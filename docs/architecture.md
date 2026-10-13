# Arquitetura do Alladin

Alladin é um backend Python de análise e paper trading para Solana mainnet. O servidor expõe comandos JSON por HTTP autenticado e MCP stdio. Não tem interface gráfica, não se conecta à Phantom/OKX, não carrega assinante e não envia transações.

## Caminho de mercado paper

1. `DexScreener` localiza e marca a pool SOL/USDC mais líquida observada para o mint configurado.
2. `GeckoTerminal` fornece candles fechados da pool; candles abertos, lacunas e atrasos são recusados.
3. `SolanaRPC` verifica mainnet e os dados SPL do mint por métodos de leitura.
4. O motor calcula features e estratégias, o conselho escolhe LONG/HOLD/CLOSE e o risco determina se há aprovação e tamanho.
5. `PaperBroker` atualiza a carteira local e o SQLite registra resposta idempotente e evento auditável.

O aquecimento não opera. Se o processo perder barras sem uma posição aberta, o histórico é reaquececido com as barras mais recentes, sem fills retroativos. Com posição ou ordem pendente, um gap interrompe o fluxo para reconciliação. Um HTTP 429 ou erro de fonte deixa o estado da carteira intacto; `paper-live` tenta novamente com backoff.

## Camadas

| Módulo | Responsabilidade |
|---|---|
| `providers.py` | Coleta de mercado Solana e RPC somente leitura |
| `features.py`, `strategies.py` | Indicadores e propostas de estratégia |
| `agents.py` | Conselho rules ou LLM com JSON Schema |
| `risk.py` | Gates, dimensionamento e circuit breakers |
| `broker.py` | Carteira paper, fills simulados e stops |
| `engine.py` | Estado causal, comandos e idempotência |
| `storage.py` | SQLite WAL e cadeia de eventos hash |
| `server.py`, `mcp_server.py` | Interfaces backend para agentes |

## Execução e limites

`Config` aceita apenas `chain=solana`, `execution=paper` e `allowed_markets=["spot"]`. A lógica de decisão e risco é compartilhada pelo ciclo paper. O fill de `paper_tick` usa a marca atual da pool mais fee/slippage definidos em configuração; não é uma cotação de rota nem replica impacto/execução de swap.

As chamadas externas são feitas antes da transação de escrita. A mutação, a resposta idempotente e o evento entram juntos na transação SQLite. O feed público pode sofrer cache, throttling e falhas; gaps nunca são sintetizados. O RPC público não é um endpoint de produção. Consulte o README para comandos e operação.
