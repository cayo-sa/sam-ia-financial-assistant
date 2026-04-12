"""
api_server.py
API Síncrona para orquestrar o agente Sam-IA.
Recebe requisições via webhook (N8N), processa na OpenAI mantendo estado local e retorna a resposta final.
"""

import os
import sys
import json
import subprocess
from fastapi import FastAPI, HTTPException, Header, Security
from pydantic import BaseModel
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

# Configurações iniciais
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "super-senha-secreta-123")

if not OPENAI_API_KEY or not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Chaves OPENAI_API_KEY, SUPABASE_URL ou SUPABASE_SERVICE_KEY ausentes no .env.")


llm_client = OpenAI(api_key=OPENAI_API_KEY)
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Sam-IA N8N Webhook", version="1.0.0")

# --- MODELOS E MEMÓRIA ---
class N8nWebhookRequest(BaseModel):
    message_from_user: str
    session_id: str
    phone_number: str

class N8nWebhookResponse(BaseModel):
    response: str
    user_id_encontrado: str | None

# Dicionário em memória: mapeia session_id para lista de mensagens (Histórico)
session_memory = {}

# --- FUNÇÕES AUXILIARES ---
def obter_user_id_por_telefone(telefone: str) -> str:
    """Busca no Supabase o ID do usuário na tabela profiles com base na coluna phone."""
    try:
        # Busca exata (pode precisar de sanitização pra retirar () - etc, dependendo de como vc salva no banco)
        resp = supabase_client.table("profiles").select("id").eq("phone", telefone).limit(1).execute()
        
        if resp.data and len(resp.data) > 0:
            return resp.data[0]["id"]
        
        return None
    except Exception as e:
        print(f"Erro ao buscar usuário pelo telefone {telefone}: {e}")
        return None

def ler_arquivo_texto(caminho: str) -> str:
    with open(caminho, "r", encoding="utf-8") as file:
        return file.read()

def buscar_contexto_usuario(user_id: str) -> str:
    """
    Substitui a chamada do shell ao buscar_contexto.py.
    Como precisamos do user_id dinâmico do banco, fazemos a consulta direta aqui.
    """
    try:
        categorias_resp = supabase_client.table("categories").select("id, name, group_name").eq("user_id", user_id).order("name").execute()
        cartoes_resp = supabase_client.table("cartoes_credito").select("id, nome").eq("user_id", user_id).eq("ativo", True).order("nome").execute()
        
        resultado = {
            "categorias": categorias_resp.data,
            "cartoes": cartoes_resp.data
        }
        return json.dumps(resultado, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao buscar contexto para o user_id {user_id}: {e}")
        return "{}"

def montar_system_prompt_dinamico(user_id: str) -> str:
    prompt_base = ler_arquivo_texto("directives/samia_system_prompt.md")
    contexto_json = buscar_contexto_usuario(user_id)
    
    contexto_str = f"""
\n--- CONTEXTO ATUALIZADO DO USUÁRIO ---
Aqui estão as categorias e cartões de crédito ATIVOS do usuário no banco de dados.
Sempre utilize ESSAS opções como referência.
Contexto do Usuário:
{contexto_json}
"""
    return prompt_base + contexto_str

def conversar_com_llm(historico_mensagens: list):
    """Envia o histórico para a OpenAI e retorna o JSON estruturado ACS."""
    response = llm_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=historico_mensagens,
        response_format={ "type": "json_object" },
        temperature=0.7
    )
    conteudo_json = response.choices[0].message.content
    try:
        return json.loads(conteudo_json)
    except json.JSONDecodeError:
        return None

def executar_script(script_name: str, payload: dict, user_id: str) -> str:
    """Invoca scripts de execução passando o user_id na env."""
    print(f"\n⏳ [Sistema] Executando {script_name} para user_id {user_id}...")
    try:
        env_vars = os.environ.copy()
        env_vars["USER_ID"] = user_id
        
        # Garante que o payload seja um dict para o json.dumps (caso venha como string)
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except:
                pass

        payload_str = json.dumps(payload, ensure_ascii=False)
        resultado = subprocess.run(
            [sys.executable, f"execution/{script_name}", payload_str],
            capture_output=True,
            text=True,
            env=env_vars
        )
        
        # Log para debug no console do Docker
        if resultado.stderr:
            print(f"⚠️ [STDERR do {script_name}]: {resultado.stderr}")
        if resultado.stdout:
            print(f"✅ [STDOUT do {script_name}]: {resultado.stdout.strip()[:500]}")
        
        # Se o script falhou (exit code != 0), retorna o erro explicitamente
        if resultado.returncode != 0:
            print(f"❌ [Exit Code {script_name}]: {resultado.returncode}")
            return json.dumps({
                "success": False, 
                "error": f"O script {script_name} falhou (code {resultado.returncode}). Verifique os logs."
            })
        
        stdout_clean = resultado.stdout.strip()
        if not stdout_clean:
            return json.dumps({
                "success": False, 
                "error": f"O script {script_name} não retornou nenhuma saída."
            })

        return stdout_clean
    except Exception as e:
        print(f"❌ [Exceção ao executar {script_name}]: {str(e)}")
        return json.dumps({"success": False, "error": f"Falha na execução do {script_name}: {str(e)}"})

# --- ROTAS DA API ---
@app.post("/webhook/n8n", response_model=N8nWebhookResponse)
async def webhook_n8n(request: N8nWebhookRequest, x_webhook_secret: str = Header(None)):
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Acesso não autorizado. Chave secreta inválida.")

    print(f"\n[Webhook Recebido] Sessão: {request.session_id} | Telefone: {request.phone_number}")

    # 1. Identificar o Usuário no Banco
    user_id = obter_user_id_por_telefone(request.phone_number)
    
    if not user_id:
        # Se o usuário não existir na tabela profile, a Sam-IA n tem como registrar nele.
        # Avisa gentilmente como resposta no WhatsApp
        return N8nWebhookResponse(
            response=f"Poxa vida, não encontrei seu usuário no banco de dados (telefone {request.phone_number}). Avisa o admin!",
            user_id_encontrado=None
        )

    # 2. Inicializar ou resgatar a sessão (Memória)
    if request.session_id not in session_memory:
        system_prompt = montar_system_prompt_dinamico(user_id)
        session_memory[request.session_id] = [
            {"role": "system", "content": system_prompt}
        ]
    
    mensagens = session_memory[request.session_id]
    
    # Adicionar a fala nova do usuário
    mensagens.append({"role": "user", "content": request.message_from_user})
    
    # 3. Conversar com LLM (1º Turno: Processamento ou Pergunta)
    acs_data = conversar_com_llm(mensagens)
    
    if not acs_data:
        raise HTTPException(status_code=500, detail="Erro interno na validação da reposta da Inteligência Artificial.")

    bot_msg = acs_data.get("message_for_user", "")
    next_action = acs_data.get("next_action", "CONTINUE_CONVERSATION")
    payload = acs_data.get("payload", None)

    # Salva resposta na memória
    mensagens.append({"role": "assistant", "content": json.dumps(acs_data, ensure_ascii=False)})

    final_bot_msg = bot_msg

    # 4. Tratar Roteamento Determinístico (Ex: Registrar Tudo)
    if (next_action in ["DISPATCH_TASK", "CADASTRAR_CARTAO", "CADASTRAR_CATEGORIA"]) and payload:
        script_alvo = "registrar_despesa.py"
        
        if next_action == "CADASTRAR_CARTAO":
            script_alvo = "cadastrar_cartao.py"
        elif next_action == "CADASTRAR_CATEGORIA":
            script_alvo = "cadastrar_categoria.py"

        # Chama a Tool para aquele user_id específico
        resultado_script = executar_script(script_alvo, payload, user_id)
        
        # Injeta resultado no contexto
        mensagens.append({
            "role": "system", 
            "content": f"O script {script_alvo} retornou isso internamente ao sistema: {resultado_script}. Com base nisso, elabore a resposta final em estilo natural confirmando pro usuário TUDO o que foi salvo ou relatando o que deu errado (NUNCA cite logs feios)."
        })
        
        # Pede pra Sam-IA falar o veredito final (2º Turno)
        confirmacao_acs = conversar_com_llm(mensagens)
        if confirmacao_acs:
            final_bot_msg = confirmacao_acs.get("message_for_user", final_bot_msg)
            mensagens.append({"role": "assistant", "content": json.dumps(confirmacao_acs, ensure_ascii=False)})

    # Devolve a mensagem que o N8N mandará pro WhatsApp de forma síncrona
    return N8nWebhookResponse(
        response=final_bot_msg,
        user_id_encontrado=user_id
    )

if __name__ == "__main__":
    import uvicorn
    # Inicia o servidor local na porta 8000
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
