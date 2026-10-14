# Alladin

O módulo [Alladin Finance Prompt Engineering](finance_prompt_engineering/README.md) incorpora o repositório solicitado sem `.git`, preserva os originais e fornece uma biblioteca ativa de prompts para os agentes da sessão externa. Há cinco papéis com evidências citáveis, contestação, plano estruturado e revalidação determinística de risco.

`GET /v1/prompts`, `GET /v1/prompts/{role}` e MCP `prompts/list`/`prompts/get` disponibilizam a biblioteca revisada. `GET /v1/performance` e `python -m alladin performance` mostram estatísticas líquidas e incerteza. A meta de 898–899 acertos em 900 operações é apenas um critério de pesquisa, não uma capacidade demonstrada nem promessa de lucro.

Backend Python de pesquisa e paper trading **exclusivamente com dados da Coinbase**, no produto spot SOL-USDC. Não há UI, conexão com Phantom/OKX, chave de carteira, assinatura ou envio de transações. Os agentes chamam comandos HTTP/MCP; o backend coleta evidências, calcula sinais, valida risco e registra decisões/fills simulados.

## O que significa paper-live

`paper-live` usa candles fechados, livro, trades recentes e volume de 24 horas do mercado spot SOL-USDC da Coinbase Advanced Trade. O primeiro comando só aquece os indicadores; os próximos processam cada barra fechada uma vez. Barras faltantes, feed atrasado, snapshot stale ou erro de provedor interrompem o ciclo sem preencher retroativamente. A negociação acompanha o ativo SOL da Solana, enquanto os preços refletem o mercado centralizado da Coinbase.

O backend fornece os mesmos sinais, filtros e limites de risco configurados para o fluxo paper do Alladin. O saldo inicial padrão é **250 USDC**. As entradas e saídas são registradas localmente contra o midpoint atual da Coinbase, somando as taxas/slippage configuradas. Isso não é uma ordem Coinbase, uma cotação executável nem garantia de que um fill real teria esse preço. Não use os resultados como evidência de rentabilidade.

Os endpoints públicos da Coinbase podem cachear ou limitar respostas; snapshots usam `Cache-Control: no-cache`. Para serviço contínuo, configure provedores estáveis, supervisão, alertas e validação econômica independente.

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

## Agentes da própria sessão

O padrão é `--agents external`. Alladin não carrega modelos, não realiza inferência e
não recebe credenciais de provedores de IA. ChatGPT Work, Codex, Claude/CLI, Grok e
outros consumidores fazem a análise na própria sessão e chamam as ferramentas.

1. `paper_tick` aquece/atualiza o feed e administra stops e bloqueios existentes.
2. `prepare_decision` retorna evidências, hashes, schemas e instruções dos cinco papéis.
3. A sessão coordena mercado/Solana/fluxo sem compartilhar respostas entre eles;
   depois fornece os três pareceres ao contestador e a revisão ao gestor.
4. `submit_decision` recebe os quatro pareceres e o plano do gestor, vinculados ao
   `task_id` e `evidence_sha256`. O backend valida contratos, consenso e risco.
5. Em paper-live, coleta nova cotação, verifica desvio/frescor e registra o fill paper;
   em replay, uma proposta aprovada fica para a abertura da próxima barra.

Sem consumidor externo executando esse ciclo, o worker coleta dados e aguarda;
ele não cria agentes nem raciocina sozinho. Subagentes são criados pela sessão
consumidora conforme os recursos disponíveis nela. A independência dos pareceres
é uma obrigação do coordenador: quatro objetos JSON não provam quatro agentes.
Veja [o protocolo de integração](docs/external-sessions.md).

`--agents rules` permanece uma referência quantitativa explícita para pesquisa.
Bancos antigos preservam o modo original: use `--agents rules` para reabri-los.
Não altere o modo ou zere saldos de uma sessão existente silenciosamente.

## Interface para agentes

Servidor HTTP autenticado, vinculado a `127.0.0.1`:

```bash
export LAB_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python3 -m alladin --db data/backend.sqlite serve --port 8080
```

O token HTTP protege acesso ao backend; não é uma credencial de inferência. Via MCP stdio não há token. O cliente HTTP envia `Authorization: Bearer <LAB_API_TOKEN>`, `Content-Type: application/json` e `Idempotency-Key` em `POST /v1/commands`. Endpoints disponíveis:

| Endpoint/comando | Uso |
|---|---|
| `GET /health` | Saúde do processo, sem dados da carteira paper |
| `GET /v1/status` | Saldo, posições, última decisão e bloqueios paper |
| `GET /v1/contract` | Contrato de endpoints e comandos |
| `GET /v1/audit?limit=100` | Eventos de decisão e execução simulada |
| `GET /v1/audit/verify` | Verifica o encadeamento de hashes dos eventos |
| `paper_tick` | Coleta read-only de mercado SOL-USDC Coinbase e processa um ciclo paper futuro |
| `ingest` | Injeta barra fechada + snapshot Solana validados; útil para feeds próprios/testes |
| `prepare_decision`, `submit_decision` | Contexto para a sessão e validação da decisão externa |
| `analyze`, `evaluate` | Análise e validação de risco, sem enviar ordens |
| `halt`, `finalize` | Para novas entradas ou fecha a sessão paper |

Exemplo de corpo: `{"command":"paper_tick","args":{}}`. A chave de idempotência deve ser nova por ciclo lógico; repetir a mesma chave e mesmo conteúdo devolve a resposta persistida. Uma chave reutilizada com conteúdo diferente é recusada.

MCP stdio não exige chave ou token de IA. Está disponível com `python3 -m alladin mcp` e oferece os mesmos comandos paper/status/auditoria. Não há comandos para carteira, order routing, shell ou configuração dinâmica.

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

Para observar uma janela limitada, use `demo-live --seconds 60 --output results/demo`.
O orçamento de coleta cobre DNS, leitura e retries; os comandos de mercado têm
limite total de 45 segundos e a demonstração também respeita o tempo restante da
janela. A sessão externa continua responsável por analisar e submeter decisões.

Antes de repetir uma sessão bloqueada, rode `python -m alladin doctor` ou chame
`alladin_diagnostics` via MCP. O resultado separa disponibilidade das fontes,
fase de rede e compatibilidade econômica dos planos padrão. `proxy_tunnel`
indica falha anterior à resposta da API, que exige verificar o acesso do ambiente
aos hosts públicos. Limites de risco não são relaxados para produzir negociações.

O runtime não contém cliente RPC nem configuração `SOLANA_RPC_URL`. A fonte externa única é a Coinbase. O protocolo `external-session-v2` usa o papel `quality` no lugar de `onchain`; o bundle ativo é 2.0.0. Campos on-chain de snapshots antigos são compatibilidade de histórico e não aparecem no envelope de evidências.

O perfil demo agora declara retorno/risco líquido mínimo de **1,5**, mantendo
**2%** de perda estimada por operação e por dia e **6%** de drawdown. Os custos e
alvos não foram alterados. Essa política precisa de avaliação fora da amostra;
não demonstra rentabilidade. Carteiras existentes usam revisão explícita auditada
com `revise-policy --from-config`, preservando saldo e perdas já consumidas.

A checagem explícita `execution_check` permite validar OPEN/CLOSE paper com preços atuais, mantendo o risco. Ela é rotulada como teste controlado e não integra estatísticas de estratégia. Consulte [operação](docs/operations.md). Posições também são acompanhadas por mark entre candles quando o worker/consumidor está ativo.
