# Protocolo de Segurança: Testes Locais com Webhooks

Este documento estabelece as diretrizes de segurança aplicáveis ao ambiente de desenvolvimento e testes da **Sam-IA** (ou outras APIs do ecossistema) que exigem exposição temporária à internet para receber requisições de sistemas terceiros em nuvem, como o N8N.

## 🎯 Por que esse protocolo é necessário?
Testar integrações locais (recebidas pela nuvem) geralmente expõe a máquina do desenvolvedor (via Ngrok ou portas liberadas no roteador). Este protocolo cria um "**Túnel Seguro a Vácuo**", eliminando instalações adicionais, interceptações de rede e varreduras não autorizadas ao seu computador.

---

## 🔒 Pilares de Segurança
1. **Zero-Install Port Forwarding:** Utiliza o túnel SSH do próprio Windows (via `localhost.run`). Nenhum software externo é executado.
2. **Isolamento de Rede (Afunilamento de Porta):** A rede externa interage apenas com a porta `8000`. Não existem permissões para o tráfego chegar ao resto do seu computador.
3. **Bloqueio Endpoint (API Key Front-End):** Qualquer URL de teste está sujeita a varreduras de robôs. Por isso, a nossa API em FastAPI obriga rigidamente que **todas** as requisições tenham um Token Header validado. Caso contrário, elas morrem instantaneamente no status HTTP 401.

---

## 🚀 Passo a Passo Obrigatório de Testes

### Passo 1: Preparar a Aplicação com a Armadura
Sua `.env` **deve** possuir a variável de segredo, sem isso o servidor de testes não deve ser roteado localmente:
```env
WEBHOOK_SECRET=senha-super-segura-aqui
```

### Passo 2: Subir a API no Modo Local (Host Interno)
Certifique-se de que a API ouvirá apenas à interface do próprio computador (IPv4 interno). Em uma aba do terminal, execute a aplicação e preste atenção à porta.
```powershell
py -3.13 -m uvicorn orchestration.api_server:app --reload
```
*(Confirme se a porta 8000 está rodando na interface 127.0.0.1 e inicializou com sucesso).*

### Passo 3: Abrir a Escotilha (Túnel SSH Limpo)
Em **outra aba do seu terminal**, abra a escotilha temporária utilizando o IPv4 e incluindo o parâmetro Anti-Queda (`ServerAliveInterval`) para impedir que o túnel expire por inatividade (timeout), resolvendo o famoso erro do N8N *"The connection to the server was closed unexpectedly"*.
```powershell
ssh -o ServerAliveInterval=30 -R 80:127.0.0.1:8000 nokey@localhost.run
```
- Você receberá um host seguro, ex: `https://abcd-1234.lhr.life`
- *Nota: Caso o SSH do Windows pergunte se o host é confiável, escreva `yes`.*

### Passo 4: Chamada a partir da Nuvem (N8N)
Aponte o serviço em nuvem para o `https` gerado acima e anexe o diretório da rota (ex: `/webhook/n8n`).
A requisição HTTP da nuvem **DEVE** possuir o seguinte cabaçalho:
- Header Name: `x-webhook-secret`
- Header Value: `[A SENHA CONFIGURADA NO SEU .ENV]`

*(Dica N8N: Em algumas redes gratuitas de túneis providos pela Let's Encrypt o N8N bloqueia a chamada. Ative "Ignore SSL Issues" unicamente ao testar túneis provisórios).*

---

## ⛔ Encerrando o Ambiente
Quando seu ciclo de experimentação for concluído, finalize a exposição:
1. Vá até o terminal do SSH e aperte **`Ctrl + C`**. 
2. A URL deixará de existir no servidor deles imediatamente, desvinculando sua máquina da internet.

Repita a arquitetura acima sempre que uma nova suíte de testes de webhook precisar ser conduzida.
