"""
chat_samia.py
Orquestrador central do Agente Sam-IA.
Faz a ponte entre a interface do usuário (terminal), o LLM (OpenAI) e a camada de execução determinística.
"""

import os
import json
import subprocess
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Verifica integridade das chaves
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY or OPENAI_API_KEY == "sua_chave_openai_aqui":
    print("ERRO: Configure sua OPENAI_API_KEY no arquivo .env antes de rodar o orquestrador.")
    exit(1)

client = OpenAI(api_key=OPENAI_API_KEY)

def ler_arquivo_texto(caminho):
    try:
        with open(caminho, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        print(f"ERRO: Arquivo {caminho} não encontrado.")
        exit(1)

def montar_system_prompt():
    """Junta as regras da Sam-IA com o contexto dinâmico do banco (categorias e cartões)."""
    # 1. Lê o prompt master
    prompt_base = ler_arquivo_texto("directives/samia_system_prompt.md")

    # 2. Executa o buscar_contexto.py para obter dados do usuário 
    # Usamos o Python do próprio ambiente atual
    try:
        resultado = subprocess.run(
            ["py", "-3.13", "execution/buscar_contexto.py"],
            capture_output=True,
            text=True,
            check=True
        )
        contexto_json = resultado.stdout.strip()
    except subprocess.CalledProcessError as e:
        print("ERRO ao buscar contexto financeiro:")
        print(e.stderr)
        exit(1)
    
    contexto_str = f"""
\n--- CONTEXTO ATUALIZADO DO USUÁRIO ---
Aqui estão as categorias e cartões de crédito ATIVOS do usuário no banco de dados.
Sempre utilize ESSAS opções como referência.
Contexto do Usuário:
{contexto_json}
"""
    return prompt_base + contexto_str

def conversar_com_llm(historico_mensagens):
    """Envia o histórico para a OpenAI e retorna o JSON estruturado ACS."""
    response = client.chat.completions.create(
        model="gpt-4o-mini", # Pode alterar para gpt-4o se desejar respostas mais inteligentes
        messages=historico_mensagens,
        response_format={ "type": "json_object" },
        temperature=0.7
    )
    
    conteudo_json = response.choices[0].message.content
    try:
        return json.loads(conteudo_json)
    except json.JSONDecodeError:
        print("ERRO CRÍTICO: O LLM não retornou um JSON válido.")
        print("Retorno Bruto:", conteudo_json)
        return None

def executar_tarefa(acao, payload):
    """Encaminha o payload recebido do LLM para o script python adequado."""
    if acao == "DISPATCH_TASK" and payload:
        print("\n⏳ [Sistema] Registrando dados no Supabase...")
        try:
            # Transforma o payload (dict) em string pra passar como argumento de CLI
            payload_str = json.dumps(payload, ensure_ascii=False)
            
            # Chama o registrar_despesa.py
            resultado = subprocess.run(
                ["py", "-3.13", "execution/registrar_despesa.py", payload_str],
                capture_output=True,
                text=True,
            )
            
            # Retorna o stdout do script (que deve ser o JSON de sucesso/erro)
            return resultado.stdout.strip()
        except Exception as e:
            return json.dumps({"success": False, "error": f"Falha na execução: {str(e)}"})
    
    return json.dumps({"success": False, "error": f"Ação desconhecida ou payload vazio: {acao}"})

def chat():
    print("Iniciando Sistema Sam-IA...\n")
    system_prompt = montar_system_prompt()
    
    # Histórico começa apenas com as diretivas de comportamento limitadas ao contexto
    mensagens = [
        {"role": "system", "content": system_prompt}
    ]
    
    print("Sam-IA: Olá! Como posso te ajudar a organizar essas finanças hoje? (Digite 'sair' para encerrar)\n")
    
    while True:
        try:
            input_user = input("Você: ")
            if input_user.lower() in ['sair', 'exit', 'quit']:
                break
                
            mensagens.append({"role": "user", "content": input_user})
            
            # Geração do LLM
            print("⏳ Sam-IA está pensando...")
            acs_data = conversar_com_llm(mensagens)
            if not acs_data:
                continue

            # Extração dos campos obrigatórios da chave ACS
            bot_msg = acs_data.get("message_for_user", "")
            next_action = acs_data.get("next_action", "CONTINUE_CONVERSATION")
            payload = acs_data.get("payload", None)
            
            print(f"\nSam-IA: {bot_msg}\n")
            
            # Adiciona a resposta falada da assistente ao histórico para memória de curto prazo
            # Passamos o JSON cru gerado pelo assistant no histórico, pois ele usa a API de object response
            mensagens.append({"role": "assistant", "content": json.dumps(acs_data, ensure_ascii=False)})

            # Trata ações de execução determinística
            if next_action == "DISPATCH_TASK":
                resultado_script = executar_tarefa(next_action, payload)
                print(f"🔧 [Output do Sistema]: {resultado_script}\n")
                
                # Injetamos o resultado como uma mensagem "system" invisível pro user, informando o LLM
                mensagens.append({
                    "role": "system", 
                    "content": f"O script the execução retornou isso (task_result): {resultado_script}. Informe o resultado final ao usuário."
                })
                
                # Pedimos pro LLM gerar a resposta final com base no resultado e confirmar com a persona
                print("⏳ Sam-IA está confirmando com o sistema...")
                confirmacao_acs = conversar_com_llm(mensagens)
                if confirmacao_acs:
                    final_msg = confirmacao_acs.get("message_for_user", "")
                    print(f"\nSam-IA: {final_msg}\n")
                    mensagens.append({"role": "assistant", "content": json.dumps(confirmacao_acs, ensure_ascii=False)})

        except KeyboardInterrupt:
            print("\nSaindo...")
            break

if __name__ == "__main__":
    chat()
