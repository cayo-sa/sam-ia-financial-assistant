# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Sam-IA** is a financial assistant agent that integrates with WhatsApp via N8N webhooks. It uses OpenAI's GPT-4o-mini to parse natural language expense descriptions and writes structured financial data to a Supabase backend.

## Running the Application

**Local development (terminal chat interface):**
```bash
py -3.13 -m python orchestration/chat_samia.py
```

**API server for webhook integration:**
```bash
py -3.13 -m uvicorn orchestration.api_server:app --reload
```
The server binds to `127.0.0.1:8000` by default. For N8N webhook testing, open a second terminal and run the SSH tunnel:
```bash
ssh -o ServerAliveInterval=30 -R 80:127.0.0.1:8000 nokey@localhost.run
```

**Docker (production):**
```bash
docker-compose up
```
Requires a `.env` file with all environment variables (see below).

## Required Environment Variables (`.env`)

```
OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
USER_ID=                  # Supabase profile UUID for local/dev user
WEBHOOK_SECRET=           # Required to authenticate N8N requests via x-webhook-secret header
BATCH_API_TOKEN=          # Bearer token for the Supabase batch-transactions edge function
BATCH_API_URL=            # Defaults to the hardcoded Supabase edge function URL
```

## Architecture

The project uses a **two-layer orchestration** pattern:

### Layer 1 — Orchestrators (`orchestration/`)
- **`chat_samia.py`**: Terminal REPL for local testing. Calls `execution/buscar_contexto.py` via subprocess to build the system prompt, then loops through conversation turns.
- **`api_server.py`**: FastAPI server exposing `POST /webhook/n8n`. Validates `x-webhook-secret` header, resolves the caller's `phone_number` to a Supabase `user_id`, manages per-session conversation history in an in-memory dict (`session_memory`), and performs two-turn LLM calls (first to parse intent, second to confirm after execution).

### Layer 2 — Execution Scripts (`execution/`)
Deterministic scripts invoked via `subprocess.run()` with a JSON payload as a CLI argument. Each prints a JSON result to stdout.

| Script | `next_action` trigger | Supabase table |
|---|---|---|
| `registrar_despesa.py` | `DISPATCH_TASK` | `transactions` |
| `cadastrar_cartao.py` | `CADASTRAR_CARTAO` | `cartoes_credito` |
| `cadastrar_categoria.py` | `CADASTRAR_CATEGORIA` | `categories` |
| `buscar_contexto.py` | startup only | `categories`, `cartoes_credito` |

Parcelada (installment) expenses in `registrar_despesa.py` are handled via an external Supabase Edge Function (`batch-transactions`) rather than direct DB insert.

### LLM Contract — Agent Control Structure (ACS)
Every LLM response must be a JSON object with exactly these four fields:
- `message_for_user` — plain text reply (no markdown, no role prefixes)
- `next_phase` — conversation phase label (set to `null` in most rules)
- `next_action` — `CONTINUE_CONVERSATION` | `DISPATCH_TASK` | `CADASTRAR_CARTAO` | `CADASTRAR_CATEGORIA`
- `payload` — structured data object or `null`

The system prompt is assembled at session start by concatenating `directives/samia_system_prompt.md` with a live JSON snapshot of the user's categories and active credit cards.

### Supabase Tables Referenced
- `profiles` — user lookup by `phone`
- `transactions` — expense records
- `cartoes_credito` — credit cards (`user_id`, `nome`, `ativo`, `limite`, `dia_vencimento`, `dia_fechamento`)
- `categories` — expense categories (`user_id`, `name`, `group_name`, `group_id`)
- `category_groups` — group definitions (`user_id`, `name`)

## Testing Utilities

```bash
# Test the Supabase batch-transactions edge function directly
py -3.13 test_request.py

# Test Supabase connection
py -3.13 execution/testar_conexao.py

# Manually run an execution script
py -3.13 execution/registrar_despesa.py '{"despesas": [...]}'
py -3.13 execution/cadastrar_cartao.py '{"nome_cartao": "Nubank", "limite": 5000, "dia_vencimento": 10, "dia_fechamento": 3}'
py -3.13 execution/cadastrar_categoria.py '{"nome_categoria": "Academia", "nome_grupo": "Qualidade de Vida"}'
```

## Security

All requests to `/webhook/n8n` must include the `x-webhook-secret` header matching `WEBHOOK_SECRET`. Requests without a valid secret return HTTP 401 immediately. Never expose the API without this secret configured.
