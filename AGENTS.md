# Alladin — notas de desenvolvimento

Backend Python sem UI, só biblioteca padrão (Python 3.11+). Não adicionar dependências.
Alladin roda exclusivamente na Solana mainnet e em spot paper. Não conecta carteiras,
não guarda chaves, não assina nem envia transações. O ciclo paper-live consome candles,
livro, trades e estatísticas públicas da Coinbase, mais RPC Solana somente leitura; falha de dado bloqueia
novos ciclos e fills. Replay sintético serve apenas para testes do motor, nunca como
prova de rentabilidade ou sessão de negociação.

## Verificação

- Testes: `python -m unittest discover -s tests` (raiz do repo)
- Replay demo: `python -m alladin --db data/x.sqlite replay --feed data/demo.jsonl --output results/x --finalize`
- Auditoria: `GET /v1/audit/verify` (HTTP) ou `store.verify_audit()`

## Invariantes

- Coletas externas do `paper_tick` acontecem fora da transação SQLite; aplicação da decisão, resposta idempotente e evento persistem juntas em um comando transacional (`BEGIN IMMEDIATE`).
- WAL com `synchronous=NORMAL`: atômico e consistente em crash de processo; perda do último commit só em queda de SO/energia — tolerada pelo modelo de repetição idempotente.
- Decisão na barra N executa na abertura de N+1 revalidando o snapshot anterior. Nunca fabricar preço de um mint sem barra.
- Nenhuma ordem externa é permitida neste projeto. Configuração precisa ser `chain=solana`, `execution=paper` e `allowed_markets=["spot"]`.
- No fluxo paper-live, RPC precede o último livro Coinbase; cotação com mais de 30 segundos não autoriza entrada. Candle anterior à abertura de uma posição não pode disparar stop retroativo.
- Gaps com posição fecham somente ao mark atual verificado e acionam halt persistente. Nunca preencher stop em preço histórico presumido.
- Idempotência é consultada antes da coleta. Worker único por banco, polling contado após conclusão, saúde de processo distinta da prontidão do feed.
- Mints não-âncora entram pelo funil `admit` → `watch`; replay/validate fazem isso automaticamente no primeiro snapshot de cada mint.
- `status()` precifica cada posição pelo mark do próprio mint (`state['series'][mint]['last_price']`).

- `available_balance` usa todo o caixa após reservar custos: aprovar integralmente ou recusar. Não reduzir silenciosamente. Respeitar risco por entrada, perda diária restante, drawdown, exposição e liquidez.
- Os originais em `finance_prompt_engineering/upstream` são referência não executável; preservar seus bytes e sua origem. Não carregar esses textos diretamente como instruções do runtime.
- Prompts ativos em `alladin/finance_prompts` exigem atualização explícita dos hashes do catálogo. Relatórios externos citam apenas o registro de evidências, nunca probabilidades inventadas. Consenso não supera veto de risco.
- Fixtures e propostas controladas não medem taxa de acerto de estratégia; avaliar PnL líquido, amostra, perdas e incerteza. Não prometer 900 operações vencedoras.

- A inteligência pertence à sessão consumidora. Não adicionar clientes de inferência, credenciais de IA ou seleção de modelos. Modo external é o padrão; subagentes são coordenados pela sessão externa.
