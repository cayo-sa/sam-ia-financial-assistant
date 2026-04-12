"""
confirmar_transacao.py
Script de execução determinístico para o agente Sam-IA.
Marca uma transação como 'confirmado' (ex: despesa pendente que foi paga).

Uso:
    python execution/confirmar_transacao.py '{"transaction_id": "uuid"}'

Saída (stdout): JSON com resultado
    Sucesso: {"success": true, "message": "Transação confirmada.", "id": "uuid"}
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


def confirmar_transacao(payload: dict) -> dict:
    if not all([SUPABASE_URL, SUPABASE_KEY, USER_ID]):
        return {"success": False, "error": "Variáveis de ambiente não configuradas. Verifique o .env"}

    transaction_id = payload.get("transaction_id", "").strip()
    if not transaction_id:
        return {"success": False, "error": "Campo 'transaction_id' é obrigatório."}

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    resp = (
        client.table("transactions")
        .update({"status": "confirmado"})
        .eq("id", transaction_id)
        .eq("user_id", USER_ID)
        .execute()
    )

    if not resp.data:
        return {"success": False, "error": "Transação não encontrada ou sem permissão para confirmar."}

    return {
        "success": True,
        "message": "Transação confirmada.",
        "id": transaction_id,
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

    resultado = confirmar_transacao(payload)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
