# Coinbase no Alladin

Coinbase é a única fonte externa de mercado e de execução. RPC da Solana, Jupiter e indexadores de pool foram removidos. O livro interno continua simulando em paper; os preços, as cotações e as ordens reais saem da Advanced Trade e da Trade API.

Pesquisa em 13/10/2026 na documentação da Coinbase Developer Platform. O produto que a Coinbase chama de base para agentes é o **AgentKit**, em `docs.cdp.coinbase.com/agent-kit`. Ele não substitui o motor do Alladin. Ele mostra o contrato certo: carteira separada do modelo, ações com esquema, e rede explícita.

## O que a Coinbase oferece

| Superfície | Para que serve | Redes |
|---|---|---|
| AgentKit | Ações nomeadas e carteira CDP, sem a seed no prompt | EVM e Solana |
| Trade API | Cotação e swap on-chain entre tokens | Ethereum, Base, Arbitrum, e também Optimism e Polygon na API |
| Advanced Trade | Livro da corretora: produtos, candles, preview e ordem | Pares da conta Coinbase, em USD |
| JWT de 2 minutos | Cada pedido autenticado leva um Bearer novo | CDP em `api.cdp.coinbase.com`; corretora em `api.coinbase.com` |

A Trade API, em beta, declara mainnet para Ethereum, Base e Arbitrum. Testnet de swap não é suportada. O swap usa Permit2: o token de origem precisa de aprovação ao contrato Permit2, e a CDP assina o permit da troca. Conta smart na Base pode usar o paymaster da Coinbase. Nas outras redes o paymaster é uma URL própria.

A Advanced Trade lista produtos `SPOT` e `FUTURE`, candles públicos e criação de ordem com `client_order_id`. Equities existem na mesma API, com sessão e tamanho inteiro, e ficam fora da ordem automática desta versão.

Chave Ed25519 é o padrão CDP. O SDK de Advanced Trade ainda pede ECDSA. Chamada direta aceita os dois. O Alladin não assina JWT aqui: o processo recebe `COINBASE_JWT`, já pronto e curto, e não vê a secret.

## Como entra no Alladin

Solana continua o padrão. Ethereum, Base e Arbitrum passam a ser redes de configuração. O caixa de uma sessão EVM nasce no USDC daquela rede.

O agente pede produto, candle, cotação de swap ou preview. Nenhum desses envia ordem. `coinbase_order` só existe com `execution=live` e `live_arm`. Pedido com campo de segredo é recusado. Resposta sem `order_id` fica `unknown` e o cliente não tenta de novo.

## Ordem de construção

1. Catálogo das três redes e USDC de cada uma. Feito.
2. Leitura pública de produtos e candles da Advanced Trade. Feito.
3. Cotação da Trade API em Ethereum, Base e Arbitrum, sem execução. Feito.
4. Preview e ordem spot armada, com JWT externo. Feito.
5. Gerar o JWT Ed25519 no processo, com a secret só no signer, ainda não. Depende de biblioteca de assinatura.
6. Aprovação Permit2, simulação e envio do swap pela carteira CDP. Ainda não. A cotação já guarda o formato.
7. Futuros e equities da Advanced Trade. Ainda não. O catálogo já consegue listar `FUTURE`; a ordem automática continua só `SPOT`.
8. Optimism e Polygon usam a mesma Trade API e entram quando o livro dessas redes for explícito.

Fontes: [AgentKit](https://docs.cdp.coinbase.com/agent-kit/welcome), [arquitetura do AgentKit](https://docs.cdp.coinbase.com/agent-kit/core-concepts/architecture-explained), [Trade API](https://docs.cdp.coinbase.com/trade-api/welcome), [swaps](https://docs.cdp.coinbase.com/wallets/using-wallets/swaps), [Advanced Trade](https://docs.cdp.coinbase.com/coinbase-business/advanced-trade-apis/rest-api), [autenticação](https://docs.cdp.coinbase.com/get-started/authentication/overview).
