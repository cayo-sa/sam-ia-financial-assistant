import os, httpx, json
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("BATCH_API_TOKEN", "")
url = "https://lttvaejsljompzmhupqk.supabase.co/functions/v1/batch-transactions"

payload = {
    "function": "per_installment_value",
    "user_id": os.getenv("USER_ID"),
    "title": "Despesa Teste Parcelada",
    "amount": 150.0,
    "parcelas": 3,
    "date": "2026-04-11",
    "parcela_atual": 1,
    "type": "expense",
    "status": "pendente",
    "category": "Saude",
    "cartao_nome": None
}

print("TOKEN COMECA COM:", token[:15] if token else "VAZIO")
resp = httpx.post(url, json=payload, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=30)
print("STATUS:", resp.status_code)
print("RESPOSTA:", resp.text[:500])
