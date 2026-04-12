"""
resumo_financeiro.py
Script de execução determinístico para o agente Sam-IA.
Retorna um resumo financeiro do período: total de receitas, despesas, saldo
e breakdown de despesas por categoria.

Uso:
    python execution/resumo_financeiro.py
    python execution/resumo_financeiro.py '{"periodo_dias": 30}'

Saída (stdout): JSON com o resumo financeiro
    Sucesso: {"success": true, "periodo_dias": N, "total_receitas": X, "total_despesas": Y,
              "saldo": Z, "despesas_por_categoria": [...]}
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


def resumo_financeiro(filtros: dict = None) -> dict:
    if not all([SUPABASE_URL, SUPABASE_KEY, USER_ID]):
        return {"success": False, "error": "Variáveis de ambiente não configuradas. Verifique o .env"}

    if filtros is None:
        filtros = {}

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    periodo_dias = int(filtros.get("periodo_dias", 30))
    data_inicio = (date.today() - timedelta(days=periodo_dias)).isoformat()
    data_fim = date.today().isoformat()

    resp = (
        client.table("transactions")
        .select("amount, type, category")
        .eq("user_id", USER_ID)
        .gte("date", data_inicio)
        .lte("date", data_fim)
        .neq("status", "cancelado")
        .execute()
    )

    total_receitas = 0.0
    total_despesas = 0.0
    despesas_por_categoria: dict[str, float] = {}

    for t in resp.data:
        valor = float(t.get("amount", 0))
        if t.get("type") == "income":
            total_receitas += valor
        else:
            total_despesas += valor
            cat = t.get("category") or "Sem categoria"
            despesas_por_categoria[cat] = despesas_por_categoria.get(cat, 0.0) + valor

    # Ordena categorias por valor decrescente
    categorias_ordenadas = sorted(
        [{"category": k, "total": round(v, 2)} for k, v in despesas_por_categoria.items()],
        key=lambda x: x["total"],
        reverse=True,
    )

    return {
        "success": True,
        "periodo_dias": periodo_dias,
        "total_receitas": round(total_receitas, 2),
        "total_despesas": round(total_despesas, 2),
        "saldo": round(total_receitas - total_despesas, 2),
        "despesas_por_categoria": categorias_ordenadas,
    }


if __name__ == "__main__":
    filtros = {}
    if len(sys.argv) >= 2:
        try:
            filtros = json.loads(sys.argv[1])
        except json.JSONDecodeError as e:
            print(json.dumps({"success": False, "error": f"JSON inválido: {str(e)}"}))
            sys.exit(1)

    resultado = resumo_financeiro(filtros)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
