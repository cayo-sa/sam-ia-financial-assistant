"""
listar_cartoes.py
Script de execução determinístico para o agente Sam-IA.
Lista os cartões de crédito ativos do usuário.

Uso:
    python execution/listar_cartoes.py

Saída (stdout): JSON com lista de cartões
    Sucesso: {"success": true, "total": N, "cartoes": [...]}
    Erro:    {"success": false, "error": "mensagem clara do erro"}
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


def listar_cartoes() -> dict:
    if not all([SUPABASE_URL, SUPABASE_KEY, USER_ID]):
        return {"success": False, "error": "Variáveis de ambiente não configuradas. Verifique o .env"}

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    resp = (
        client.table("cartoes_credito")
        .select("id, nome, limite, dia_vencimento, dia_fechamento")
        .eq("user_id", USER_ID)
        .eq("ativo", True)
        .order("nome")
        .execute()
    )

    return {
        "success": True,
        "total": len(resp.data),
        "cartoes": resp.data,
    }


if __name__ == "__main__":
    resultado = listar_cartoes()
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
