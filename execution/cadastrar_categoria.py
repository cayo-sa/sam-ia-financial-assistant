"""
cadastrar_categoria.py
Ajusta e insere uma nova categoria para o usuário na tabela categories.
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

def cadastrar_categoria(payload: dict | str) -> dict:
    if not all([SUPABASE_URL, SUPABASE_KEY, USER_ID]):
        return {"success": False, "error": "Configurações de banco ausentes."}

    # Se o payload vier como string, converte para dict
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            return {"success": False, "error": f"Payload inválido: {payload}"}

    nome_cat = payload.get("nome_categoria")
    nome_grupo = payload.get("nome_grupo")

    if not nome_cat or not nome_grupo:
        return {"success": False, "error": "nome_categoria e nome_grupo são parâmetros obrigatórios."}

    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. Obter o group_id pesquisando em category_groups
    # Tenta descobrir o ID do grupo pelo nome retirando emojis com regex
    import re
    buscar_nome_limpo = re.sub(r'[^\w\s]', '', nome_grupo).strip()

    # Tenta achar o group_id
    try:
        resp_grupo = (
            client.table("category_groups")
            .select("id")
            .eq("user_id", USER_ID)
            .ilike("name", f"%{buscar_nome_limpo}%")
            .limit(1)
            .execute()
        )
        
        group_id = None
        if resp_grupo.data and len(resp_grupo.data) > 0:
            group_id = resp_grupo.data[0]["id"]
            
    except Exception as e:
        return {"success": False, "error": f"Fazendo a varredura do grupo de dados: {str(e)}"}

    # 2. Inserir a Categoria
    registro = {
        "user_id": USER_ID,
        "name": nome_cat,
        "group_name": nome_grupo
    }
    
    if group_id:
        registro["group_id"] = group_id
        
    try:
        resp = client.table("categories").insert(registro).execute()
        
        if resp.data and len(resp.data) > 0:
            return {"success": True, "message": f"Categoria '{nome_cat}' associada ao grupo '{nome_grupo}' com sucesso."}
        else:
            return {"success": False, "error": "Falha silenciosa no banco ao inserir a categoria."}
            
    except Exception as e:
        return {"success": False, "error": f"Erro interno do Supabase na tabela categories: {str(e)}"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "Payload JSON ausente."}))
        sys.exit(1)

    try:
        payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"JSON inválido: {str(e)}"}))
        sys.exit(1)

    resultado = cadastrar_categoria(payload)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
