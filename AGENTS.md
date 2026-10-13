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
- Mints não-âncora entram pelo funil `admit` → `watch`; replay/validate fazem isso automaticamente no primeiro snapshot de cada mint.
- `status()` precifica cada posição pelo mark do próprio mint (`state['series'][mint]['last_price']`).
