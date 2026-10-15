# Alladin

**A headless Coinbase multi-token paper trading backend for external AI agents.**

Alladin lets a ChatGPT, Codex, Claude, Grok or other agent session discover Coinbase
products, compare opportunities, record a thesis, propose a trade and commit a
simulated order. The backend owns sizing, shared cash, risk checks, execution
accounting and audit. The session owns reasoning and any subagents. There is no
UI, embedded model, inference API key, wallet signer or real-order path.

The default execution core is **NautilusTrader 1.231.0**, isolated behind the
Alladin capital/risk gateway. [Engine setup and boundaries](docs/nautilus.md).

## What it does

| Capability | Implemented behavior |
|---|---|
| Product universe | Dynamic public Coinbase catalog; spot execution across eligible tokens, including listed memecoins; no SOL-only allowlist |
| Opportunity discovery | Bounded shortlist by funded quote, 24h activity and trend, momentum, volume, volatility, spread and cost checks |
| Market evidence | Product-specific metadata, current L2 book, contiguous closed candles, indicators, visible imbalance and execution estimates |
| Agent workflow | `log_thesis` → `propose_trade` → `commit_trade`; expiring evidence-bound proposals, deterministic size and current-risk revalidation |
| Shared portfolio | One cash authority across instruments, explicit currency units, per-position basis, realized PnL and fees |
| Execution | Decimal lot sizing, bid/ask book walking, `MARKET_IOC` / `LIMIT_IOC`, explicit partial-fill policy, idempotent fills |
| Risk | Stop budget, costs, daily loss, drawdown, open risk, concentration, attributed agent/strategy limits, conservative correlation and order-rate limits |
| Protection | Worker-managed observed stop, target, time and trailing exits; reduce-only halt and current-book closure |
| Integrity | Atomic SQLite ledger and responses, balanced postings, retained proposal evidence, internal reconciliation and hash-chained audit |
| Interfaces | Authenticated HTTP, MCP stdio tools/resources/prompts and CLI; Python 3.12+ with the pinned engine extra |

The scanner is advisory and examines a bounded subset, not every token's full
history on each call. It does not predict guaranteed profit or execute a ranking
automatically. External agents must justify trades and can abstain. Public
listing does not verify account/regional trading permission.

## Run

```bash
python -m pip install '.[engine]'
export LAB_API_TOKEN='<backend-token-at-least-32-characters>'
python -m alladin --config config.portfolio.json --db data/portfolio.sqlite serve --paper-worker --poll-seconds 30
```

For MCP, run `python -m alladin mcp` and keep one separate `paper-live` worker on
the same account while positions are open. Global config/database arguments come
before the subcommand. `python -m alladin contract` returns the active portfolio
command schema; `python -m alladin scan --limit 5` scans public market data.

The default profile is `config.portfolio.json`; execution is always paper. The
legacy `config.json` profile and old research tools remain available explicitly.
Existing accounts require the documented flat-account migration, never a balance
reset. USD, USDC, EUR and BTC are not assumed equivalent; a quote currency must
be funded and have actual FX evidence where needed.

## Session flow

1. Inspect account, policy, worker health and `reconcile`.
2. Discover products and inspect advisory opportunities and current evidence.
3. Log a thesis with invalidation and horizon.
4. Review the server-sized, expiring proposal and its stressed costs/risk.
5. Commit once, verify the actual fill and keep position protection active.
6. Reduce/close using current bids; verify remaining exposure and net results.

Paper fills walk visible L2 snapshots and apply configured fee assumptions. They
do not reproduce queue priority, hidden liquidity, exchange latency or actual
account fee tiers. Stops are local observed paper exits, **not exchange-native
orders**; protection requires a running worker and working data access.

## Documentation

- [Portfolio backend, commands, accounting, risk and migration](docs/portfolio.md)
- [Blueprint implementation and explicit production gaps](docs/blueprint-implementation.md)
- [Product universe and capability boundaries](docs/coinbase-universe.md)
- [Documentation index](docs/README.md)
- [Agent instructions](AGENTS.md) and [consumer guide](.agents/CONSUMER.md)
- [Reviewed finance prompts and upstream provenance](finance_prompt_engineering/README.md)

Catalog discovery also preserves non-spot records. Futures, perpetuals, options,
equities, real orders, native brackets and institutional deployment controls are
not implemented by the spot adapter. Unknown instrument types fail closed.
No win rate, account doubling or continuous uptime is promised.

## Verify

```bash
python -m unittest discover -s tests -q
python -m compileall -q alladin
git diff --check
```

Deterministic fixtures test software behavior; networked paper checks use real
Coinbase observations. Neither establishes profitable alpha. Keep private account
state, credentials, runtime reports and external audit anchors out of Git.
