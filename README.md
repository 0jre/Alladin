# Alladin

Backend Python de pesquisa e paper trading **exclusivamente na Solana mainnet**, em spot. Não há UI, conexão com Phantom/OKX, chave de carteira, assinatura ou envio de transações. Os agentes chamam comandos HTTP/MCP; o backend coleta evidências, calcula sinais, valida risco e registra decisões/fills simulados.

## O que significa paper-live

`paper-live` usa candles fechados, livro, trades recentes e volume de 24 horas do mercado spot SOL-USDC da Coinbase Advanced Trade. O RPC Solana é usado apenas para confirmar mainnet e dados do mint. O primeiro comando só aquece os indicadores; os próximos processam cada barra fechada uma vez. Barras faltantes, feed atrasado, snapshot stale ou erro de provedor interrompem o ciclo sem preencher retroativamente. A negociação acompanha o ativo SOL da Solana, enquanto os preços refletem o mercado centralizado da Coinbase.

O motor quantitativo ou o conselho LLM usa os mesmos sinais, filtros e limites de risco configurados para o fluxo paper do Alladin. O saldo inicial padrão é **20 USDC**. As entradas e saídas são registradas localmente contra o midpoint atual da Coinbase, somando as taxas/slippage configuradas. Isso não é uma ordem Coinbase, uma cotação executável nem garantia de que um fill real teria esse preço. Não use os resultados como evidência de rentabilidade.

Os endpoints públicos da Coinbase podem cachear ou limitar respostas; snapshots usam `Cache-Control: no-cache`. O RPC público tem limites e não é recomendado pela Solana para produção. Para serviço contínuo, configure provedores estáveis, supervisão, alertas e validação econômica independente.

## Iniciar uma sessão paper

Requer Python 3.11+ e nenhuma dependência de terceiros:

```bash
python3 -m unittest discover -s tests -v
python3 -m alladin --config config.json --db data/paper-250.sqlite paper-tick
python3 -m alladin --config config.json --db data/paper-250.sqlite serve --paper-worker --poll-seconds 30
```

O padrão agora é 250 USDC. O primeiro `paper-tick` tende a retornar `warmed_up`. `serve --paper-worker` mantém a API e a coleta no mesmo processo; `paper-live` inicia só o worker. Para uma conta paper nova, use outro arquivo SQLite. O comando `generate-demo` e `replay` usam dados sintéticos e servem somente para testar o motor, nunca como replay de mercado real.

O perfil padrão `sizing_mode=available_balance` usa todo o saldo disponível, descontando o custo da entrada. A perda estimada até o stop, incluindo custos de ida e volta, precisa caber em 2% por operação, no orçamento diário restante de 2% e no drawdown de 6%. Uma entrada que não cabe nesses limites é recusada integralmente. Após a venda, o próximo tamanho usa o saldo atualizado. O perfil anterior continua disponível com `sizing_mode=risk_budget`.

Esta mudança de perfil exige um banco novo; não reconfigure silenciosamente uma sessão existente. Para continuar uma carteira anterior, transfira o saldo e os limites diários já consumidos com um evento de auditoria que referencie a sessão de origem.

Leia o [guia de operação](docs/operations.md) para persistência, readiness, supervisão Linux, container, gaps e retomada. `GET /health` confirma processo ativo; `GET /ready` verifica prontidão de coleta e worker. O template systemd está em `deploy/alladin.service`.

## Escolher o motor de decisão

O padrão `--agents rules` é uma referência quantitativa reproduzível, não IA. Para habilitar o conselho LLM:

```bash
export OPENAI_API_KEY="<chave da API>"
export OPENAI_MODEL="<modelo compatível com Responses API e Structured Outputs>"
python3 -m alladin --agents llm --max-llm-calls 200 --db data/llm-paper.sqlite paper-live
```

Os agentes podem propor LONG, HOLD ou CLOSE e justificar a proposta com evidências coletadas pelo backend. Não escolhem notional, não alteram limites, não recebem segredos e não executam código. Se um agente ou provedor falha, o ciclo não deve produzir uma nova entrada. Configure limite financeiro no provedor de modelos; o orçamento de chamadas por processo não é limite em dólares.

## Interface para agentes

Servidor HTTP autenticado, vinculado a `127.0.0.1`:

```bash
export LAB_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python3 -m alladin --db data/backend.sqlite serve --port 8080
```

O cliente envia `Authorization: Bearer <LAB_API_TOKEN>`, `Content-Type: application/json` e `Idempotency-Key` em `POST /v1/commands`. Endpoints disponíveis:

| Endpoint/comando | Uso |
|---|---|
| `GET /health` | Saúde do processo, sem dados da carteira paper |
| `GET /v1/status` | Saldo, posições, última decisão e bloqueios paper |
| `GET /v1/contract` | Contrato de endpoints e comandos |
| `GET /v1/audit?limit=100` | Eventos de decisão e execução simulada |
| `GET /v1/audit/verify` | Verifica o encadeamento de hashes dos eventos |
| `paper_tick` | Coleta read-only de mercado Solana e processa um ciclo paper futuro |
| `ingest` | Injeta barra fechada + snapshot Solana validados; útil para feeds próprios/testes |
| `analyze`, `evaluate` | Análise e validação de risco, sem enviar ordens |
| `halt`, `finalize` | Para novas entradas ou fecha a sessão paper |

Exemplo de corpo: `{"command":"paper_tick","args":{}}`. A chave de idempotência deve ser nova por ciclo lógico; repetir a mesma chave e mesmo conteúdo devolve a resposta persistida. Uma chave reutilizada com conteúdo diferente é recusada.

MCP stdio está disponível com `python3 -m alladin mcp` e oferece os mesmos comandos paper/status/auditoria. Não há comandos para carteira, order routing, shell ou configuração dinâmica.

## Modelo quantitativo e limites

O motor calcula indicadores causais (EMAs, RSI, ATR, ADX, MACD, Bollinger, VWAP aproximado, eficiência direcional, momentum e volume relativo), compara estratégias de tendência/breakout/reversão e passa propostas pelo risco determinístico. O risco considera stops, custos estimados, liquidez, volume, exposição, perdas diárias, drawdown e qualidade/frescor do snapshot. Spot não vende a descoberto.

Em `paper-live`, a decisão usa candle já fechado e evidência atual do livro/trades Coinbase; o fill paper usa o midpoint atual mais custos configurados. O caminho `ingest` preserva a semântica histórica do replay: decisão na barra N e entrada elegível na abertura de N+1 com revalidação. Os dois fluxos não devem ser misturados na mesma sessão.

O midpoint de uma exchange não garante execução em uma DEX Solana. O simulador não mede impacto real de ordem, profundidade roteável, MEV, falhas de RPC, prioridade, congestionamento, taxa de rede ou diferenças entre o livro Coinbase e uma rota on-chain. Perp e live execution estão desativados. Testes com fixtures verificam o software, não rentabilidade nem resposta ao mercado real.

## Verificação

```bash
python3 -m unittest discover -s tests -v
python3 -m alladin contract
```

O servidor usa SQLite WAL e uma cadeia de hash para auditoria. O HTTP da biblioteca padrão deve permanecer atrás de uma camada TLS/autenticação/limite de tráfego para acesso remoto. Os eventos ainda exigem backups e retenção operacional.
