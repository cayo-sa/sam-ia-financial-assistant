# Diretiva — Registro de Despesas (Sam-IA)

## Objetivo
Coletar dados de UMA ou MAIS despesas em linguagem natural e registrá-las no banco de dados via script de execução.

## Entradas
- Mensagem do usuário (linguagem natural)
- Contexto da conversa anterior

## Ferramenta de Execução
```
python execution/registrar_despesa.py '<json_payload>'
```

Antes de chamar o script, se necessário, consulte o contexto do usuário:
```
python execution/buscar_contexto.py
```
Use para validar nomes de categorias e cartões. **Nunca invente nomes que não estejam na lista retornada.**

## Campos a Extrair por Despesa

| Campo | Obrigatório | Tipo |
|---|---|---|
| `nome_despesa` | ✅ | string |
| `valor` | ✅ | number |
| `categoria` | ✅ | string (nome exato do banco) |
| `tipo_despesa` | ✅ | `unica` \| `recorrente` \| `parcelada` |
| `forma_pagamento` | ✅ | `pix` \| `dinheiro` \| `cartão de crédito` |
| `nome_cartao_credito` | ✅ se crédito | string (nome exato do banco) |
| `data_pagamento` | ❌ | YYYY-MM-DD (default: hoje) |
| `quantidade_parcelas` | ✅ se parcelada | number |
| `numero_parcela_atual` | ✅ se parcelada | number |

## Regras de Extração

### Tipo de despesa
- **única**: gasto pontual ("gastei", "comprei", "paguei")
- **recorrente**: se repete mensalmente (Netflix, aluguel, academia)
- **parcelada**: usuário menciona parcelas ("em 12x", "parcela da TV")

### Forma de pagamento
- Se o usuário disser "crédito", "cartão" → `cartão de crédito` → **pedir o nome do cartão se não informado**
- Se disser "pix", "transferência" → `pix`
- Se disser "dinheiro", "espécie", "cash" → `dinheiro`
- "débito" → perguntar se foi pix ou dinheiro (débito não é uma forma de pagamento no sistema)

### Categoria
- Use **sempre** o nome exato retornado por `buscar_contexto.py`
- Se o usuário disser uma categoria que não existe, apresente as mais próximas e pergunte

## Processo

1. Extrair todos os dados que o usuário informou
2. Se faltar campo obrigatório → pedir de forma natural, sem listar todos de uma vez
3. Quando todos os dados estiverem completos → avisar o usuário que vai registrar
4. Executar `registrar_despesa.py` com o payload
5. Aguardar o resultado real do script:
   - `{"success": true}` → confirmar com o resultado exato (nome, valor, categoria)
   - `{"success": false, "error": "..."}` → informar o erro e pedir correção ao usuário

> ⚠️ **REGRA CRÍTICA**: Nunca confirme o registro antes de o script retornar `success: true`.
> A mensagem de confirmação ao usuário SEMPRE vem depois do resultado real.

## Payload de Saída (para o script)

```json
{
  "despesas": [
    {
      "nome_despesa": "Suporte Monitor",
      "valor": 450.00,
      "categoria": "Compra Livre",
      "tipo_despesa": "unica",
      "forma_pagamento": "cartão de crédito",
      "nome_cartao_credito": "Neon",
      "data_pagamento": null,
      "quantidade_parcelas": null,
      "numero_parcela_atual": null
    }
  ]
}
```

## Edge Cases Conhecidos

- **"Débito"**: não existe no sistema. Pergunte se foi pix ou dinheiro.
- **Múltiplas despesas na mesma mensagem**: extraia todas, confirme todas de uma vez antes de executar.
- **Categoria inexistente**: não invente. Liste as opções próximas e peça confirmação.
- **Cartão inexistente**: não invente. Informe que o cartão não foi encontrado e pergunte o nome correto.
- **Despesa parcelada**: O `valor` SEMPRE se refere ao valor de CADA PARCELA individual, e NÃO ao valor total da compra. O script chama uma API externa (`batch-transactions`) que cria automaticamente todas as parcelas a partir da parcela atual até a última. Exemplo: se o usuário disser "comprei um celular de R$ 150 por mês em 12x, estou na parcela 3", o valor é `150`, quantidade_parcelas é `12`, numero_parcela_atual é `3`, e a API criará as parcelas 3 a 12 automaticamente.
