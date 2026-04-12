"""
buscar_transacao.py
Script de execução determinístico para o agente Sam-IA.
Busca transações pelo nome (título) usando busca parcial case-insensitive.
Usado como pré-requisito antes de editar ou deletar uma transação.

Uso:
    python execution/buscar_transacao.py '{"termo_busca": "Netflix", "limite": 5}'
    python execution/buscar_transacao.py '{"termo_busca": "Apartamento", "mes_vigente": true}'
    python execution/buscar_transacao.py '{"termo_busca": "Apartamento", "mes_vigente": false}'

Parâmetros:
    - termo_busca (obrigatório): texto para busca parcial no título
    - limite (opcional): máximo de resultados, padrão 5
    - mes_vigente (opcional, padrão true): se true, restringe ao mês atual
      (evita confundir transações recorrentes com o mesmo nome de meses anteriores)

Saída (stdout): JSON com lista de transações encontradas
    Sucesso: {"success": true, "total": N, "mes_vigente": bool, "transacoes": [...]}
    Erro:    {"success": false, "error": "mensagem clara do erro"}
"""

import os
import json
import sys
from datetime import date
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
USER_ID = os.getenv("USER_ID")


def buscar_transacao(payload: dict) -> dict:
    if not all([SUPABASE_URL, SUPABASE_KEY, USER_ID]):
        return {"success": False, "error": "Variáveis de ambiente não configuradas. Verifique o .env"}

    termo = payload.get("termo_busca", "").strip()
    if not termo:
        return {"success": False, "error": "Campo 'termo_busca' é obrigatório."}

    limite = int(payload.get("limite", 5))
    mes_vigente = payload.get("mes_vigente", True)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    query = (
        client.table("transactions")
        .select("id, title, amount, type, category, payment_method, date, status, recurrence_type")
        .eq("user_id", USER_ID)
        .neq("status", "cancelado")
        .ilike("title", f"%{termo}%")
        .order("date", desc=True)
        .limit(limite)
    )

    if mes_vigente:
        hoje = date.today()
        primeiro_dia = hoje.replace(day=1).isoformat()
        query = query.gte("date", primeiro_dia).lte("date", hoje.isoformat())

    resp = query.execute()

    return {
        "success": True,
        "total": len(resp.data),
        "mes_vigente": mes_vigente,
        "transacoes": resp.data,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Passe o payload JSON como argumento."}))
        sys.exit(1)

    try:
        payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"JSON inválido: {str(e)}"}))
        sys.exit(1)

    resultado = buscar_transacao(payload)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
