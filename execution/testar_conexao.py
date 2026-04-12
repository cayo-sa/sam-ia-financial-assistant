"""
testar_conexao.py
Script de diagnóstico para verificar se a conexão com o Supabase está funcionando.

Uso:
    python execution/testar_conexao.py

Saída: JSON com status da conexão e tabelas acessíveis
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


def testar_conexao():
    print(json.dumps({"status": "iniciando", "mensagem": "Testando conexão com Supabase..."}, ensure_ascii=False))

    if not all([SUPABASE_URL, SUPABASE_KEY, USER_ID]):
        faltando = [k for k, v in {"SUPABASE_URL": SUPABASE_URL, "SUPABASE_SERVICE_KEY": SUPABASE_KEY, "USER_ID": USER_ID}.items() if not v]
        print(json.dumps({
            "success": False,
            "error": f"Variáveis de ambiente faltando: {', '.join(faltando)}. Verifique o arquivo .env"
        }, ensure_ascii=False))
        sys.exit(1)

    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Testa acesso às tabelas principais
        resultados = {}

        # Testa tabela transactions
        resp_tx = client.table("transactions").select("id").eq("user_id", USER_ID).limit(1).execute()
        resultados["transactions"] = {"acessivel": True, "total_registros_amostra": len(resp_tx.data)}

        # Testa tabela categories
        resp_cat = client.table("categories").select("id, name").eq("user_id", USER_ID).limit(5).execute()
        resultados["categories"] = {
            "acessivel": True,
            "exemplos": [c["name"] for c in resp_cat.data]
        }

        # Testa tabela cartoes_credito
        resp_cart = client.table("cartoes_credito").select("id, nome").eq("user_id", USER_ID).eq("ativo", True).execute()
        resultados["cartoes_credito"] = {
            "acessivel": True,
            "cartoes_ativos": [c["nome"] for c in resp_cart.data]
        }

        print(json.dumps({
            "success": True,
            "mensagem": "CONEXAO OK!",
            "supabase_url": SUPABASE_URL,
            "user_id": USER_ID,
            "tabelas": resultados
        }, ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": f"Falha na conexão: {str(e)}"
        }, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    testar_conexao()
