"""
listar_transacoes.py
Script de execução determinístico para o agente Sam-IA.
Lista as transações recentes do usuário com filtros opcionais.

Uso:
    python execution/listar_transacoes.py
    python execution/listar_transacoes.py '<json_filtros>'

Filtros opcionais (JSON):
    {
        "limite": 10,
        "tipo": "expense | income",
        "categoria": "string",
        "periodo_dias": 30
    }

Saída (stdout): JSON com lista de transações
    Sucesso: {"success": true, "total": N, "transacoes": [...]}
    Erro:    {"success": false, "error": "mensagem clara do erro"}
"""

import os
import json
import sys
from datetime import date, timedelta
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
USER_ID = os.getenv("USER_ID")


def listar_transacoes(filtros: dict = None) -> dict:
    if not all([SUPABASE_URL, SUPABASE_KEY, USER_ID]):
        return {"success": False, "error": "Variáveis de ambiente não configuradas. Verifique o .env"}

    if filtros is None:
        filtros = {}

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    limite = int(filtros.get("limite", 10))
    tipo = filtros.get("tipo")
    categoria = filtros.get("categoria")
    periodo_dias = int(filtros.get("periodo_dias", 30))

    data_inicio = (date.today() - timedelta(days=periodo_dias)).isoformat()

    query = (
        client.table("transactions")
        .select("id, title, amount, type, category, payment_method, date, status, recurrence_type")
        .eq("user_id", USER_ID)
        .gte("date", data_inicio)
        .order("date", desc=True)
        .limit(limite)
    )

    if tipo:
        query = query.eq("type", tipo)
    if categoria:
        query = query.eq("category", categoria)

    resp = query.execute()

    return {
        "success": True,
        "total": len(resp.data),
        "periodo_dias": periodo_dias,
        "transacoes": resp.data
    }


if __name__ == "__main__":
    filtros = {}
    if len(sys.argv) >= 2:
        try:
            filtros = json.loads(sys.argv[1])
        except json.JSONDecodeError as e:
            print(json.dumps({"success": False, "error": f"JSON inválido: {str(e)}"}))
            sys.exit(1)

    resultado = listar_transacoes(filtros)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
