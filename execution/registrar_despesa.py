"""
registrar_despesa.py
Script de execução determinístico para o agente Sam-IA.
Recebe um payload JSON de despesas e insere na tabela transactions do Supabase.

Uso:
    python execution/registrar_despesa.py '<json_payload>'

Payload esperado (array de despesas):
    {
        "despesas": [
            {
                "nome_despesa": "string",
                "valor": number,
                "categoria": "string",
                "tipo_despesa": "unica | recorrente | parcelada",
                "forma_pagamento": "pix | dinheiro | cartão de crédito",
                "nome_cartao_credito": "string | null",
                "data_pagamento": "YYYY-MM-DD | null",
                "quantidade_parcelas": "number | null",
                "numero_parcela_atual": "number | null"
            }
        ]
    }

Saída (stdout): JSON com resultado do registro
    Sucesso: {"success": true, "registradas": N, "ids": [...]}
    Erro:    {"success": false, "error": "mensagem clara do erro"}
"""

import os
import json
import sys
import uuid
from datetime import date, datetime
from dotenv import load_dotenv
from supabase import create_client
import httpx

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
USER_ID = os.getenv("USER_ID")
BATCH_API_URL = os.getenv("BATCH_API_URL", "https://lttvaejsljompzmhupqk.supabase.co/functions/v1/batch-transactions")
BATCH_API_TOKEN = os.getenv("BATCH_API_TOKEN")


def resolver_cartao_id(client, nome_cartao: str) -> str | None:
    """Busca o cartao_id pelo nome (case-insensitive). Retorna None se não encontrar."""
    resp = (
        client.table("cartoes_credito")
        .select("id, nome")
        .eq("user_id", USER_ID)
        .eq("ativo", True)
        .ilike("nome", f"%{nome_cartao}%")
        .limit(1)
        .execute()
    )
    if resp.data:
        return resp.data[0]["id"]
    return None


def registrar_despesas(payload: dict | str) -> dict:
    if not all([SUPABASE_URL, SUPABASE_KEY, USER_ID]):
        return {"success": False, "error": "Variáveis de ambiente não configuradas. Verifique o .env"}

    # Se o payload vier como string (JSON double-encoded), converte para dict
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return {"success": False, "error": f"Payload inválido (não é um JSON válido): {payload}"}

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    despesas = payload.get("despesas", [])

    if not despesas:
        return {"success": False, "error": "Nenhuma despesa encontrada no payload."}

    ids_registrados = []
    hoje = date.today().isoformat()

    for despesa in despesas:
        # --- Valida campos obrigatórios ---
        campos_obrigatorios = ["nome_despesa", "valor", "categoria", "forma_pagamento", "tipo_despesa"]
        faltando = [c for c in campos_obrigatorios if not despesa.get(c)]
        if faltando:
            return {"success": False, "error": f"Campos obrigatórios faltando: {', '.join(faltando)}"}

        nome = despesa["nome_despesa"]
        valor = float(despesa["valor"])
        categoria = despesa["categoria"]
        tipo = despesa["tipo_despesa"]  # unica | recorrente | parcelada
        forma_pagamento = despesa["forma_pagamento"]
        nome_cartao = despesa.get("nome_cartao_credito")
        data_pagamento = despesa.get("data_pagamento") or hoje
        qtd_parcelas = despesa.get("quantidade_parcelas")
        parcela_atual = despesa.get("numero_parcela_atual")

        # --- Resolve cartao_id se for crédito ---
        cartao_id = None
        if forma_pagamento == "cartão de crédito":
            if not nome_cartao:
                return {"success": False, "error": f"Nome do cartão obrigatório para despesa '{nome}' no crédito."}
            cartao_id = resolver_cartao_id(client, nome_cartao)
            if not cartao_id:
                return {"success": False, "error": f"Cartão '{nome_cartao}' não encontrado ou inativo."}
            
            # Regra de negócio: compras no crédito não preenchem a data de pagamento hoje (DB resolve)
            data_pagamento = None

        # --- Monta o registro base ---
        registro = {
            "user_id": USER_ID,
            "title": nome,
            "category": categoria,
            "amount": valor,
            "type": "expense",
            "date": hoje,
            "payment_method": forma_pagamento,
            "cartao_nome": nome_cartao,
            "cartao_id": cartao_id,
            "payment_date": data_pagamento,
            "recurrence_type": tipo,
            "status": "pendente",
            "origin": "sam-ia",
        }

        # --- Despesa parcelada: chama API batch-transactions ---
        if tipo == "parcelada" and qtd_parcelas and parcela_atual:
            if not BATCH_API_TOKEN:
                return {"success": False, "error": "BATCH_API_TOKEN não configurado no .env."}

            api_payload = {
                "function": "per_installment_value",
                "user_id": USER_ID,
                "title": nome,
                "amount": valor,
                "parcelas": int(qtd_parcelas),
                "date": data_pagamento or hoje,
                "parcela_atual": int(parcela_atual),
                "type": "expense",
                "status": "pendente",
                "category": categoria,
                "cartao_nome": nome_cartao
            }

            try:
                resp_api = httpx.post(
                    BATCH_API_URL,
                    json=api_payload,
                    headers={
                        "Authorization": f"Bearer {BATCH_API_TOKEN}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )
                resp_api.raise_for_status()
                api_result = resp_api.json()

                # A API retorna os IDs criados
                if isinstance(api_result, list):
                    ids_registrados.extend([row.get("id", "batch") for row in api_result])
                elif isinstance(api_result, dict) and api_result.get("ids"):
                    ids_registrados.extend(api_result["ids"])
                else:
                    ids_registrados.append("batch-ok")

            except httpx.HTTPStatusError as e:
                return {
                    "success": False,
                    "error": f"Erro na API batch-transactions (HTTP {e.response.status_code}): {e.response.text}"
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": f"Erro ao chamar API batch-transactions: {str(e)}"
                }

        else:
            # --- Despesa única ou recorrente ---
            resp = client.table("transactions").insert(registro).execute()
            if resp.data:
                ids_registrados.append(resp.data[0]["id"])

    return {
        "success": True,
        "registradas": len(ids_registrados),
        "ids": ids_registrados,
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

    resultado = registrar_despesas(payload)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
