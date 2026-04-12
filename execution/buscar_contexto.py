"""
buscar_contexto.py
Ferramenta auxiliar para o agente Sam-IA.
Retorna as categorias e cartões ativos do usuário para evitar que a IA invente nomes.

Uso:
    python execution/buscar_contexto.py

Saída (stdout): JSON com keys "categorias" e "cartoes"
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


def buscar_contexto():
    if not all([SUPABASE_URL, SUPABASE_KEY, USER_ID]):
        print(json.dumps({"error": "Variáveis de ambiente não configuradas. Verifique o .env"}))
        sys.exit(1)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Busca categorias do usuário
    categorias_resp = (
        client.table("categories")
        .select("id, name, group_name")
        .eq("user_id", USER_ID)
        .order("name")
        .execute()
    )

    # Busca cartões ativos do usuário
    cartoes_resp = (
        client.table("cartoes_credito")
        .select("id, nome, limite, dia_vencimento")
        .eq("user_id", USER_ID)
        .eq("ativo", True)
        .order("nome")
        .execute()
    )

    resultado = {
        "categorias": categorias_resp.data,
        "cartoes": cartoes_resp.data,
    }

    print(json.dumps(resultado, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    buscar_contexto()
