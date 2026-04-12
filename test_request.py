import os
import httpx
import json
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('BATCH_API_TOKEN')
url = os.getenv('BATCH_API_URL', 'https://lttvaejsljompzmhupqk.supabase.co/functions/v1/batch-transactions')

payload = {
    'function': 'per_installment_value',
    'user_id': os.getenv('USER_ID'),
    'title': 'Despesa Teste',
    'amount': 150.0,
    'parcelas': 3,
    'date': '2026-04-11',
    'parcela_atual': 1,
    'type': 'expense',
    'status': 'pendente',
    'category': 'Eletrônicos',
    'cartao_nome': 'Nubank'
}

print(f'\\n--- DADOS DA REQUISICAO ---')
print(f'URL: {url}')
print(f'Headers: Authorization: Bearer {token[:10]}...{token[-5:]}')
print(f'Payload: {json.dumps(payload)}')

try:
    resp = httpx.post(url, json=payload, headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'})
    print(f'\\n--- RESPOSTA {resp.status_code} ---')
    print(resp.text)
except Exception as e:
    print(e)
