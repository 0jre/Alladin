# Alladin — pesquisa autônoma com a Coinbase como única fonte

Servidor de pesquisa com decisões autônomas e execução simulada. Sem frontend e sem comandos de shell. As interfaces são JSON HTTP, CLI e um cliente Python. Mercado e execução externa passam só pela Coinbase: corretora Advanced Trade e swaps em Ethereum, Base e Arbitrum.

O simulador paper continua local. SOL cotado na corretora é um produto Coinbase, não uma leitura direta da rede Solana. O padrão é paper. `shadow` bloqueia a entrada se a cotação cair. `live` só existe com `live_arm`, allowlist e teto. O servidor não é um programa on-chain.

## Executar agora

Python 3.11+, biblioteca padrão; não precisa instalar dependências para rodar diretamente da pasta.

```bash
python3 -m unittest discover -s tests -v
python3 -m alladin generate-demo --bars 600
python3 -m alladin --db data/nova_pesquisa.sqlite replay --feed data/demo.jsonl --output results/nova_pesquisa --finalize
```

`data/demo.jsonl` é explicitamente sintético, inclusive oracle, liquidez, autoridades e funding. Os resultados em `results/demo` são exemplos de execução, não evidência de rentabilidade. O replay finalizado fecha posições ao último preço e encerra aquela sessão. Use um banco diferente para uma nova pesquisa/configuração. Para continuar recebendo barras, omita `--finalize`. Mints além do âncora entram pelo mesmo funil no replay e no validate: o primeiro snapshot de cada mint é classificado com `admit` e armado com `watch` antes do ingest; um mint inelegível aborta a leitura.

## Subir o servidor

```bash
# Crie este token no próprio servidor; não compartilhe publicamente.
export LAB_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python3 -m alladin --db data/backend.sqlite serve --port 8080
```

Escuta em `127.0.0.1:8080`. Para acesso remoto, configure um proxy TLS autenticado e limites de requisição. Esta implementação usa HTTP da biblioteca padrão e não foi validada para produção pública. GETs de saúde/status continuam disponíveis durante chamadas LLM; só um comando é executado por vez. Um comando concorrente recebe `503 command_busy`, devendo repetir a mesma chave de idempotência. Cada instância deve usar seu próprio banco; não execute vários workers para uma mesma sessão.

`POST /v1/commands` exige `Authorization: Bearer <LAB_API_TOKEN>`, `Content-Type: application/json` e `Idempotency-Key`. O corpo é sempre:

```json
{"command":"analyze","args":{}}
```

Exemplo via cliente CLI, sem montar comandos de shell pelo agente:

```bash
python3 -m alladin call --request docs/request_analyze.json --key analysis-0001
```

O comando analyze precisa de barras já ingeridas. Um teste de conectores read-only é:

```bash
python3 -m alladin call --request docs/request_collect.json --key products-0001
```

Cada nova coleta usa uma chave nova; uma repetição com a mesma chave retorna a resposta anterior, inclusive seu timestamp. A mesma chave com outro corpo é recusada. Mutações, resposta idempotente e evento são persistidos atomicamente em SQLite WAL. O WAL usa `synchronous=NORMAL`: commits continuam atômicos e consistentes; só uma queda de sistema operacional ou energia pode perder a última transação confirmada — e com ela o registro de idempotência, então a repetição com a mesma chave reexecuta limpa. Repetir a última barra com o mesmo conteúdo e outra chave também não executa de novo. Barras fora de ordem, lacunas ou revisão de uma barra processada são recusadas.

## Modo de agentes de IA

```bash
# Defina os valores no ambiente de execução por secret manager ou shell local.
export OPENAI_API_KEY="<sua chave da API, não uma chave de carteira>"
export OPENAI_MODEL="<modelo que suporte Responses API e Structured Outputs>"
python3 -m alladin --agents llm --max-llm-calls 200 --db data/ia.sqlite serve
```

O servidor possui quatro papéis:

1. **Mercado:** regime, tendência, contexto de prazo maior, reversão e volatilidade.
2. **On-chain:** evidências de mint SPL, autoridades, liquidez, concentração e lacunas.
3. **Contestação:** procura sinais contrários, custos, funding adverso e problemas nos dados.
4. **Gestor:** retorna uma proposta estruturada de LONG, SHORT, HOLD ou CLOSE.

As chamadas usam Responses API com JSON Schema, `store=false` e limite de saída. Relatórios são validados localmente, inclusive referências a chaves de evidência. O gestor pode selecionar candidatos quantitativos e ajustar stop/take/horizonte dentro do contrato, ou se abster. Ele não escolhe o notional, não altera limites, não recebe uma chave de carteira e não executa código. Os agentes recebem dados já coletados pelo backend; não têm acesso irrestrito a ferramentas externas. Justificativas são resumos auditáveis, não raciocínio interno privado.

Falhas, recusas, contratos inválidos, evidências inexistentes e esgotamento do orçamento produzem HOLD com erro registrado. Não há fallback silencioso para regras. `--max-llm-calls` limita chamadas **por processo**, não dólares, e reinicia ao reiniciar o processo. Um ciclo completo pode consumir quatro chamadas. Configure também um limite financeiro no provedor. As chamadas reais ao modelo não foram executadas neste ambiente; os contratos e falhas foram testados com respostas controladas.

O modo padrão `--agents rules` é uma referência quantitativa reproduzível, **não IA**. O status e todos os relatórios identificam o modo. O servidor não se mantém ativo ao fechar seu processo; para operação contínua é necessário um supervisor de serviço.

## MCP

O chat fala com o Alladin por MCP, no stdio. Cursor, Claude e os modos com computador sandbox descobrem as ferramentas sozinhos. A ordem continua na Coinbase. O HTTP em `127.0.0.1` fica para o sandbox e para clientes que já usam idempotência.

```bash
python -m alladin mcp
```

No Cursor, o arquivo `.cursor/mcp.json` deste projeto sobe esse comando. Se uma ferramenta devolver `action_request`, o chat mostra o link Connect account.

## Endpoints e comandos para agentes externos

| Interface | Resultado |
|---|---|
| `GET /health` | Saúde do processo, sem dados de carteira |
| `GET /v1/status` | Saldo fictício, posições, proposta pendente, bloqueios |
| `GET /v1/contract` | Contrato de comandos |
| `GET /v1/audit?limit=100` | Eventos de análise, decisão e execução |
| `coinbase_products` | Produtos públicos da Advanced Trade |
| `coinbase_candles` | Candles públicos da corretora |
| `coinbase_quote` | Cotação de swap na Trade API; não executa |
| `coinbase_preview` / `coinbase_order` | Preview, e ordem spot só com `live_arm` |
| `coinbase_connect` | Pedido de ação com o link Connect account; não devolve token |
| `market_radar` / `market_prices` | Ranking, classificação, sinais, rastreador, alpha e copy observado |
| `desks` / `platforms` | Mesas de análise e contrato para ChatGPT, Claude, Work e sandbox |
| `ingest` | Barra fechada + snapshot → conselho → risco → ação pendente |
| `analyze` | Análise dos dados armazenados, sem agendar operação |
| `evaluate` com `proposal` | Validação de risco, sem executar |
| `halt` | Bloqueio persistente; fecha na próxima barra válida |
| `finalize` | Encerra pesquisa e liquida ficticiamente ao último preço |

`docs/agent_tools.json` fornece descritores de ferramentas para registrar em um agente. `docs/tools_adapter.py` contém os wrappers Python que chamam o backend. Não existem endpoints para `exec`, shell, alteração de config, assinatura ou envio de transações. Nenhuma URL de endpoint é escolhida pelo modelo.

## Lógica quantitativa e controle de risco

- Features causais: EMAs, inclinação, RSI por médias simples, ATR por médias simples, ADX com suavização Wilder, MACD, bandas de Bollinger, VWAP aproximado, eficiência direcional, momentum e volume relativo.
- Contexto de prazo maior: grupos completos de quatro barras, ancorados ao horário UTC. Barras parciais são excluídas.
- Estratégias: tendência com confluência, breakout com volume e reversão à média em lateralização. Choques geram abstenção.
- VaR/CVaR históricos de uma barra: estatísticas descritivas de retornos passados; não são estimativas confiáveis de cauda futura.
- Risco por operação e risco aberto agregado; exposição bruta/líquida combinada de spot e perp. Não trata posições no mesmo SOL como diversificação.
- Dimensionamento limitado por saldo, distância ao stop, custos, participação estimada na liquidez e limites da carteira.
- Relação ganho/risco estimada líquida de custos; funding adverso pode bloquear perp. Confiança do agente é um score não calibrado, nunca uma probabilidade usada em Kelly.
- Bloqueio por drawdown, perda diária UTC, cooldown após perdas, preço distante da referência, oracle inválido e dados incompletos.
- Spot não vende a descoberto. Perp só entra com oracle e funding explícitos, market verificado e margem suficiente.

Todos os parâmetros em `config.json` são hipóteses para pesquisa, não parâmetros recomendados para dinheiro real. Alterar configuração de sessão existente é recusado; use outro banco.

## Dados

A execução externa é a Coinbase. `coinbase_products` e `coinbase_candles` leem a Advanced Trade sem chave. `coinbase_quote` pede a cotação de swap em Ethereum, Base ou Arbitrum e não executa. `coinbase_order` só envia ordem spot com `live_arm` e `COINBASE_JWT`, ou com a sessão OAuth gravada no processo.

`market_radar` e `market_prices` leem Binance, OKX, CoinGecko, CoinMarketCap, DexScreener e GMGN. Eles montam ranking, tabela de classificação, sinais, rastreador, alpha e candidatos de copy trading. Essa leitura não envia ordem. CoinMarketCap usa `CMC_API_KEY` no processo. CoinGecko aceita `COINGECKO_API_KEY` opcional.

`coinbase_connect` devolve um `action_request` com o link Connect account em `https://login.coinbase.com/oauth2/auth`. O chat mostra o link. O token fica no processo local e não volta no JSON. Defina `COINBASE_OAUTH_CLIENT_ID`, `COINBASE_OAUTH_REDIRECT_URI` e, para a troca do code, `COINBASE_OAUTH_CLIENT_SECRET`. O redirect local esperado pelo servidor é `/oauth/coinbase/callback`.

`platforms` entrega o contrato de ferramenta para Cursor, ChatGPT, ChatGPT Work, Claude, Claude Work e computador sandbox. `desks` lista as mesas do Alladin. As categorias seguem a organização pública de [awesome-claude-finance-prompts](https://github.com/devfinprojects/awesome-claude-finance-prompts); o texto é do Alladin e obriga o uso destas ferramentas.

O servidor não baixa sozinho o histórico. Um feed confiável chama `ingest` com barras fechadas. Não se inventa volume de uma barra a partir de volume de 24 horas. Flags do snapshot são evidências do chamador autenticado.

## Formato do feed

Veja `docs/feed.md`. Uma linha JSONL tem `candle` e `snapshot`; os mesmos objetos servem como args de ingest. Na v0.2 o intervalo é fixo e uniforme, padrão de 15 minutos. Só são aceitas barras fechadas no horário UTC atual. Feeds precisam preservar os snapshots históricos disponíveis naquele instante; coletar dados de hoje e colocá-los em barras antigas causaria lookahead.

## Execução simulada

A decisão ocorre no fechamento da barra N e a entrada/saída por agente só ocorre na abertura de N+1, após revalidar risco usando o snapshot anterior. O snapshot de N+1 não autoriza retroativamente essa entrada. Ordens bloqueadas não são reenviadas automaticamente.

Stops, take profits e expiração são avaliados nas barras; se stop e take podem ocorrer na mesma barra, o stop tem prioridade. Gaps adversos preenchem ao preço de abertura. Trailing stop é atualizado depois do fechamento e só vale a partir da próxima barra. Custos são debitados de forma explícita; slippage é um custo hipotético em bps, não uma reconstrução de roteamento real. Taxa fixa simula custo por operação em USDC.

Perp usa uma aproximação de margem isolada com manutenção fixa e liquidação aproximada, não uma réplica de Drift/Adrena. Funding_rate é a taxa efetivamente realizada uma vez naquela barra: positivo significa long paga e short recebe. Expected_funding_hourly no snapshot é informação anterior para decisão. A perda isolada é limitada ao colateral no modelo; seguros, cross-margin, oracles reais, keeper fees, liquidações parciais e mecanismos específicos do protocolo não estão reproduzidos.

Halt não inventa execução em um preço antigo: bloqueia imediatamente novas entradas e aguarda próxima barra válida para fechar posições fictícias. Finalize é explicitamente um encerramento de pesquisa pelo último preço observado. Não existe reset automático de circuit breaker.

## Avaliar períodos e custos

```bash
python3 -m alladin validate --feed data/demo.jsonl --folds 3 --output results/validacao_nova
```

Cria blocos cronológicos com 80 barras anteriores de warmup, conta independente por bloco e custos base/2x. A primeira entrada possível é na primeira barra de avaliação. Não otimiza parâmetros nesses blocos. Este comando valida o modo rules; avaliação LLM fora da amostra ainda está pendente. Para testar vantagem é necessário histórico real com snapshots contemporâneos e amostra muito maior.

Export gera `summary.json`, `equity.csv`, `trades.csv` e `audit.jsonl`. O estado guarda até 500 barras, 200 trades recentes e 2.000 pontos de curva para limitar o contexto; o banco mantém o histórico de eventos e export o utiliza. O arquivo de eventos cresce: retenção, rotação, backups e métricas de infraestrutura ainda precisam ser configurados.

## Validação e limites desta entrega

Testes locais verificam causalidade, entrada na barra seguinte, revalidação com dados anteriores, idempotência HTTP/SQLite, restauração, gates de risco, contabilidade, funding, autenticação e falhas do modelo. O replay sintético verifica o ciclo completo sem fundos ou chaves.

O acesso direto às APIs externas retornou HTTP 403 no ambiente de construção. Os conectores foram verificados contra documentação e fixtures, **não contra dados ao vivo**. A IA usa um cliente implementado e testes controlados, **não foi validada economicamente com um modelo real**.

Para completar um sistema de produção faltam: feed OHLCV/oracle/funding verificado, validação real fora da amostra, revisão independente, integração específica dos protocolos, custódia/assinatura com permissões, reconciliação on-chain e observabilidade de operação. Esta entrega não é um trader de fundos reais pronto para ativar.

## Fontes usadas na implementação

- https://solana.com/docs/rpc/http/getaccountinfo
- https://solana.com/docs/rpc/http/gettokensupply
- https://solana.com/docs/rpc/http/gettokenlargestaccounts
- https://solana.com/docs/rpc/http/getgenesishash
- https://docs.dexscreener.com/api/reference
- https://developers.jup.ag/docs/api-reference/swap/v1/quote
- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/cookbook/examples/structured_outputs_intro

Implementação própria; não é um fork nem incorpora o código dos repositórios pesquisados anteriormente.

## Pesquisa de projetos e procedência

Veja [seleção técnica](docs/upstream-research.md). As referências não são dependências incorporadas: esta versão mantém implementação própria.

A auditoria agora encadeia eventos com SHA-256 e valida via `GET /v1/audit/verify`. Retenha o `head` fora do banco para detectar reescrita completa; hashes não são assinaturas. Bancos antigos sem selos falham na validação: use um banco novo para esta versão.
