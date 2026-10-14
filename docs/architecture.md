# Arquitetura do Alladin

Alladin é um backend Python de análise e paper trading para Solana mainnet. O servidor expõe comandos JSON por HTTP autenticado e MCP stdio. Não tem interface gráfica, não se conecta à Phantom/OKX, não carrega assinante e não envia transações.

## Caminho de mercado paper

1. `CoinbaseMarket` coleta candles fechados do produto SOL-USDC, o livro, trades recentes e volume de 24 horas pelos endpoints públicos Coinbase Advanced Trade.
2. O provedor recusa candles abertos, lacunas, produtos que não sejam SOL e snapshots sem bid/ask ou dados de trade válidos.
3. `SolanaRPC` verifica mainnet e os dados SPL do mint por métodos de leitura.
4. O motor calcula features e estratégias, a sessão externa propõe LONG/HOLD/CLOSE e o risco determina se há aprovação e tamanho.
5. `PaperBroker` atualiza a carteira local e o SQLite registra resposta idempotente e evento auditável.

O aquecimento não opera. Se o processo perder barras sem uma posição aberta, o histórico é reaquececido com as barras mais recentes, sem fills retroativos. Com posição ou ordem pendente, um gap fecha ao mark atual verificado, registra o intervalo não observado e aciona halt persistente para revisão. Erros transitórios de fonte deixam a carteira intacta; o transporte faz retries limitados respeitando `Retry-After`, e `paper-live` agenda a próxima tentativa com backoff. O HTTP do Alladin traduz falhas persistentes de fonte em 503, nunca repassa o status upstream.

## Camadas

| Módulo | Responsabilidade |
|---|---|
| `providers.py` | Coleta de mercado Solana e RPC somente leitura |
| `features.py`, `strategies.py` | Indicadores e propostas de estratégia |
| `agents.py` | Contratos e validação de decisões externas; baseline rules |
| `risk.py` | Gates, dimensionamento e circuit breakers |
| `broker.py` | Carteira paper, fills simulados e stops |
| `engine.py` | Estado causal, comandos e idempotência |
| `storage.py` | SQLite WAL e cadeia de eventos hash |
| `server.py`, `mcp_server.py` | Interfaces backend para agentes |
| `runtime.py` | Worker único por banco, retry, shutdown e diagnóstico de saúde |

## Execução e limites

`Config` aceita apenas `chain=solana`, `execution=paper` e `allowed_markets=["spot"]`. A lógica de decisão e risco é compartilhada pelo ciclo paper. O fill de `paper_tick` usa o midpoint Coinbase mais fee/slippage definidos em configuração; não é uma cotação de rota nem replica impacto/execução de swap.

As coletas de mercado/RPC são feitas antes da transação de escrita. A análise dos
agentes acontece na sessão consumidora, sem transação SQLite aberta e sem chamada
de inferência pelo Alladin. Preparação e submissão são comandos separados e duráveis.
Resposta idempotente, mutação e evento persistem na mesma transação. O feed público
pode falhar ou limitar acesso; gaps não são sintetizados.

O servidor pode iniciar seu worker com `serve --paper-worker`. Consulte [operação](operations.md) para persistência, readiness e supervisão.

## Dimensionamento pelo saldo

O perfil `available_balance` investe o caixa disponível depois do custo de entrada. O risco aprova o saldo inteiro ou recusa a entrada; não o reduz automaticamente. O perfil padrão limita a perda estimada a 2% por operação, respeita o orçamento diário restante de 2% e drawdown de 6%. O perfil `risk_budget` anterior mantém seus fingerprints e regras de dimensionamento. Mudança de perfil exige nova sessão e transferência auditada para continuidade do saldo.


## Finance Prompt Engineering

O clone solicitado está em `finance_prompt_engineering/upstream`, sem `.git` e com
hashes em `UPSTREAM.json`. O runtime usa apenas a adaptação revisada e versionada
em `alladin/finance_prompts`, incluída no pacote Python. Veja o [mapa de adaptação](../finance_prompt_engineering/ADAPTATIONS.md).

```mermaid
flowchart TD
  A["Candles fechados e snapshot verificado"] --> B["Envelope e registro de evidências"]
  P["Bundle de prompts com hashes"] --> C["Mercado, Solana e fluxo independentes"]
  B --> C
  B --> E["Prévia determinística: risco, custos e estresse"]
  C --> D["Contestador e pré-mortem"]
  E --> D
  D --> M["Gestor com plano estruturado"]
  M --> R["Consenso, referências e risco final"]
  R --> O["Paper broker e auditoria"]
```

A sessão consumidora coordena os primeiros três relatórios sem revelar as respostas
dos pares, fornece-os ao contestador e encaminha a revisão ao gestor. O backend
valida referências, contratos, veto, desacordo e risco; não pode comprovar que os
pareceres vieram de agentes independentes. Sem candidato econômico viável não
emite tarefa de entrada.

Cada tarefa tem ID, hash do estado e das evidências, prazo de até 300 segundos e
consumo único. Estado alterado, tarefa substituída ou vencida exige nova preparação.
Em paper-live, preparação e submissão coletam observações novas fora da transação;
a submissão recusa desvio de preço acima do limite, cotação vencida e contexto que
atravessou o fechamento da próxima barra. O risco é reavaliado com o novo snapshot.
Em replay, conserva-se a execução elegível na abertura da barra seguinte.

A auditoria registra sessão declarada pelo consumidor, protocolo, bundle e evidência.
Não há SDK de inferência, modelo configurável, cliente de provedor ou orçamento de
chamadas. Prompts não fornecem notícias ou dados on-chain que não foram coletados.
`/v1/performance` mede PnL líquido e incerteza do histórico, sem prometer ganhos.

Consulte [o protocolo externo](external-sessions.md) para os payloads e a integração.
