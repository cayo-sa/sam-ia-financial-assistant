"""
cadastrar_cartao.py
Cadastra um novo cartão de crédito para o usuário no banco de dados.
"""

import os
import json
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
USER_ID = os.getenv("USER_ID")

def cadastrar_cartao(payload: dict | str) -> dict:
    if not all([SUPABASE_URL, SUPABASE_KEY, USER_ID]):
        return {"success": False, "error": "Configurações de banco ausentes."}

    # Se o payload vier como string, converte para dict
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return {"success": False, "error": f"Payload inválido: {payload}"}

    nome = payload.get("nome_cartao")
    limite = payload.get("limite")
    venc = payload.get("dia_vencimento")
    fechamento = payload.get("dia_fechamento")

    if not nome or limite is None or venc is None or fechamento is None:
        return {"success": False, "error": "Parâmetros incompletos no payload (nome_cartao, limite, dia_vencimento, dia_fechamento)."}

    # Tentativa de cast para numbers caso a LLM mande em string
    try:
        limite = float(limite)
        venc = int(venc)
        fechamento = int(fechamento)
    except Exception:
        return {"success": False, "error": "limite, dia_vencimento ou dia_fechamento possuem formatos inválidos."}

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    registro = {
        "user_id": USER_ID,
        "nome": nome,
        "limite": limite,
        "dia_vencimento": venc,
        "dia_fechamento": fechamento,
        "ativo": True
    }

    try:
        resp = client.table("cartoes_credito").insert(registro).execute()
        
        if resp.data and len(resp.data) > 0:
            return {"success": True, "message": f"Cartão {nome} inserido com sucesso para o usuário.", "cartao_id": resp.data[0]["id"]}
        else:
            return {"success": False, "error": "Falha silenciosa no banco ao inserir o cartão."}
            
    except Exception as e:
        return {"success": False, "error": f"Erro interno do Supabase: {str(e)}"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Payload JSON ausente."}))
        sys.exit(1)

    try:
        payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"JSON inválido: {str(e)}"}))
        sys.exit(1)

    resultado = cadastrar_cartao(payload)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
