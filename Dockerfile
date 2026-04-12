FROM python:3.13-slim

WORKDIR /app

# Instalar dependências gerais (se houver alguma que exija compilação, ex: build-essential)
# RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Copiar arquivos de dependências
COPY requirements.txt .

# Instalar as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código da aplicação
COPY . .

# Expor a porta que a API do FastAPI vai utilizar
EXPOSE 8000

# Executar a aplicação pelo Uvicorn atrelada a host 0.0.0.0 (Obrigatório em Docker)
CMD ["python", "-m", "uvicorn", "orchestration.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
