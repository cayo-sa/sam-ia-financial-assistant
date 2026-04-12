"""
desativar_cartao.py
Script de execução determinístico para o agente Sam-IA.
Desativa um cartão de crédito pelo nome (ativo = false).

Uso:
    python execution/desativar_cartao.py '{"nome_cartao": "Nubank"}'

Saída (stdout): JSON com resultado
    Sucesso: {"success": true, "message": "Cartão X desativado.", "cartao_id": "uuid"}
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


def desativar_cartao(payload: dict) -> dict:
    if not all([SUPABASE_URL, SUPABASE_KEY, USER_ID]):
        return {"success": False, "error": "Variáveis de ambiente não configuradas. Verifique o .env"}

    nome_cartao = payload.get("nome_cartao", "").strip()
    if not nome_cartao:
        return {"success": False, "error": "Campo 'nome_cartao' é obrigatório."}

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # Localiza o cartão pelo nome (case-insensitive)
    busca = (
        client.table("cartoes_credito")
        .select("id, nome")
        .eq("user_id", USER_ID)
        .eq("ativo", True)
        .ilike("nome", nome_cartao)
        .limit(1)
        .execute()
    )

    if not busca.data:
        return {"success": False, "error": f"Cartão '{nome_cartao}' não encontrado ou já está inativo."}

    cartao_id = busca.data[0]["id"]
    nome_real = busca.data[0]["nome"]

    resp = (
        client.table("cartoes_credito")
        .update({"ativo": False})
        .eq("id", cartao_id)
        .eq("user_id", USER_ID)
        .execute()
    )

    if not resp.data:
        return {"success": False, "error": "Não foi possível desativar o cartão."}

    return {
        "success": True,
        "message": f"Cartão {nome_real} desativado.",
        "cartao_id": cartao_id,
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

    resultado = desativar_cartao(payload)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
