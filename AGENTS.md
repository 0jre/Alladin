# Alladin — notas de desenvolvimento

Backend de pesquisa paper, só biblioteca padrão (Python 3.11+). Não adicionar dependências.

## Verificação

- Testes: `python -m unittest discover -s tests` (raiz do repo)
- Simulação A–Z: `python tests/sim_az.py` com `alladin` importável — PowerShell: `$env:PYTHONPATH='.'`; bash: `PYTHONPATH=.`
- Replay demo: `python -m alladin --db data/x.sqlite replay --feed data/demo.jsonl --output results/x --finalize`
- Auditoria: `GET /v1/audit/verify` (HTTP) ou `store.verify_audit()`

## Invariantes

- Um comando por transação SQLite (`BEGIN IMMEDIATE`), resposta idempotente persistida junto com o evento.
- WAL com `synchronous=NORMAL`: atômico e consistente em crash de processo; perda do último commit só em queda de SO/energia — tolerada pelo modelo de repetição idempotente.
- Decisão na barra N executa na abertura de N+1 revalidando o snapshot anterior. Nunca fabricar preço de um mint sem barra.
- Ordem externa só na Coinbase, só com `live_arm`. Fontes de visão (Binance, OKX, CoinGecko, CMC, DexScreener, GMGN) são leitura.
- Mints não-âncora entram pelo funil `admit` → `watch`; replay/validate fazem isso automaticamente no primeiro snapshot de cada mint.
- `status()` precifica cada posição pelo mark do próprio mint (`state['series'][mint]['last_price']`).
