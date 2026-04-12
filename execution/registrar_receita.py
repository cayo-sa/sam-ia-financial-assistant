"""
registrar_receita.py
Script de execução determinístico para o agente Sam-IA.
Recebe um payload JSON de receitas e insere na tabela transactions do Supabase.

Uso:
    python execution/registrar_receita.py '<json_payload>'

Payload esperado:
    {
        "receitas": [
            {
                "nome_receita": "string",
                "valor": number,
                "categoria": "string",
                "forma_recebimento": "pix | dinheiro | transferência | salário",
                "data_recebimento": "YYYY-MM-DD | null",
                "tipo_receita": "unica | recorrente"
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
from datetime import date
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
USER_ID = os.getenv("USER_ID")


def registrar_receitas(payload: dict) -> dict:
    if not all([SUPABASE_URL, SUPABASE_KEY, USER_ID]):
        return {"success": False, "error": "Variáveis de ambiente não configuradas. Verifique o .env"}

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    receitas = payload.get("receitas", [])

    if not receitas:
        return {"success": False, "error": "Nenhuma receita encontrada no payload."}

    ids_registrados = []
    hoje = date.today().isoformat()

    for receita in receitas:
        # --- Valida campos obrigatórios ---
        campos_obrigatorios = ["nome_receita", "valor", "categoria", "forma_recebimento", "tipo_receita"]
        faltando = [c for c in campos_obrigatorios if not receita.get(c)]
        if faltando:
            return {"success": False, "error": f"Campos obrigatórios faltando: {', '.join(faltando)}"}

        nome = receita["nome_receita"]
        valor = float(receita["valor"])
        categoria = receita["categoria"]
        forma_recebimento = receita["forma_recebimento"]
        tipo = receita["tipo_receita"]
        data_recebimento = receita.get("data_recebimento") or hoje

        registro = {
            "user_id": USER_ID,
            "title": nome,
            "category": categoria,
            "amount": valor,
            "type": "income",
            "date": hoje,
            "payment_method": forma_recebimento,
            "payment_date": data_recebimento,
            "recurrence_type": tipo,
            "status": "confirmado",
            "origin": "sam-ia",
        }

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

    resultado = registrar_receitas(payload)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
