# Alladin

**A headless research and paper-trading backend operated by external AI agents.**

Alladin targets **the Coinbase product universe**, across tokens and product types.
`catalog`, `instrument` and `instrument_book` discover public products and their
metadata without a SOL allowlist. **Execution migration is incomplete:** the
existing paper executor supports SOL-USDC spot only. See the exact
[capability matrix and migration requirements](docs/coinbase-universe.md).

The existing execution path turns public Coinbase SOL-USDC spot observations into structured market
evidence, accepts decisions from an external agent session, checks them against
deterministic execution and risk rules, and records simulated trades in an audited
SQLite ledger. It is a Python service with HTTP, MCP over stdio, and CLI interfaces.

The consuming ChatGPT, Codex, Claude, Grok, or other compatible session supplies the
reasoning and coordinates any subagents. Alladin supplies the data, contracts,
portfolio state, controls, and paper execution. It contains **no inference client,
model selection, or AI-provider API keys**.

## What the product does

| Capability | Implemented behavior |
|---|---|
| Instrument discovery | Full public Coinbase catalog across returned types, canonical product IDs, metadata, explicit capability blocks and product-specific research books |
| Market evidence | Coinbase closed candles, current order book, recent trades, and estimated quote volume over completed 24-hour candles |
| Quantitative context | Causal indicators, regime classification, and advisory trend, breakout, and mean-reversion candidates |
| Agent coordination | Versioned prompts, an evidence registry, frozen decision tasks, four specialist assessments, and a structured manager plan |
| Risk and sizing | Freshness, product identity, liquidity, costs, score, exposure, stop-loss budget, daily loss, drawdown, and cooldown checks |
| Paper execution | LONG, CLOSE, and HOLD; current midpoint with modeled costs; stops, time exits, and trailing protection while polling is active |
| Persistence | Durable account state, idempotent commands, atomic ledger/event writes, and a verifiable event hash chain |
| Research | Explicit rules baseline, causal JSONL replay, chronological validation blocks, cost stress, exports, and observed performance statistics |

The worker keeps data and existing positions updated. **It does not create AI
agents or submit intelligent decisions.** Without an external consumer,
`--agents external` collects observations and waits. `demo-live` is a bounded
observation runner, not an autonomous trading strategy.

## Decision and execution flow

1. **Observe:** `paper_tick` warms up or advances the feed and manages existing positions.
2. **Prepare:** `prepare_decision` returns evidence, exact reference identifiers,
   schemas, reviewed role prompts, and an expiring task.
3. **Reason externally:** the session assesses market, quality, and flow; challenges
   the thesis; then produces a manager plan. Quantitative candidates are advisory,
   so an external strategy can be proposed without an internal signal.
4. **Submit:** `submit_decision` validates reports, references, consensus, task
   authority, and the actual plan. Agreement cannot override a risk veto.
5. **Verify:** approved live-data paper actions produce execution events and an
   explicit outcome; status, performance, and audit expose the result.

Tasks preserve the evidence originally reviewed. Ordinary ticks do not replace a
valid task; material account changes invalidate its authority. Entry risk is checked
again using current account state, closed indicators, and a quote no more than
30 seconds old. HOLD requires no execution quote. CLOSE uses a current book without
waiting for unrelated candle, trade, or volume collection.

## Run locally

Requires **Python 3.11+**; the runtime has no third-party Python dependencies.
The persistent worker uses POSIX file locking, so use Linux or compatible Unix.
From the repository root:

```bash
python3 -m unittest discover -s tests -q
export LAB_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python3 -m alladin --config config.json --db data/paper.sqlite serve --paper-worker --poll-seconds 30
```

HTTP binds to `127.0.0.1:8080`. `LAB_API_TOKEN` authenticates the backend; it is not
a Coinbase or AI-provider key. Public Coinbase data requires no exchange account
key. Use the same token in the consuming client process.

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS -H "Authorization: Bearer $LAB_API_TOKEN" http://127.0.0.1:8080/v1/status
```

For MCP, run `python3 -m alladin --config config.json --db data/paper.sqlite mcp`.
MCP does not start a worker automatically; call `paper_tick` or coordinate with
one worker using the same database. Read [getting started](docs/getting-started.md)
before operating a persistent account.

## Product boundaries

- Live data comes exclusively from Coinbase SOL-USDC. `chain=solana` and the native
  SOL mint identify the asset; **there is no Solana RPC or on-chain collection**.
- Execution is **spot paper only**: no real order submission, wallet connection,
  signer, Phantom/OKX integration, short selling, or leveraged trading.
- A paper fill is a local midpoint simulation with configured costs, not a Coinbase
  fill confirmation or an executable DEX route.
- The repository profile starts a **new** account with 250 USDC, 15-minute candles,
  full affordable-balance sizing, a 2% estimated loss budget per entry, a 2% daily
  loss limit, a 6% drawdown limit, and a 1.5 minimum modeled net reward/risk ratio.
  Existing accounts preserve their state and configuration fingerprint.
- Validated software, sophisticated prompts, or a high observed win rate do not
  establish predictive edge. HOLD and risk rejection are legitimate outcomes;
  profit and upstream network availability are not guaranteed.

## Documentation

Start with the [documentation index](docs/README.md).

| Topic | Reference |
|---|---|
| Capabilities and responsibility boundaries | [Product](docs/product.md) |
| Installation and first account | [Getting started](docs/getting-started.md) |
| Components, persistence, and concurrency | [Architecture](docs/architecture.md) |
| HTTP, MCP, CLI, and result contracts | [API reference](docs/api.md) |
| Tasks, reports, plans, and retries | [External session protocol](docs/external-sessions.md) |
| Coinbase sources, indicators, and timing | [Market data](docs/feed.md) |
| Sizing, costs, exits, and circuit breakers | [Risk and execution](docs/risk-and-execution.md) |
| Workers, deployment, recovery, and backups | [Operations](docs/operations.md) |
| Replay, validation, and performance | [Research and evaluation](docs/research.md) |
| Parameters and persisted compatibility | [Configuration](docs/configuration.md) |
| Consuming or maintaining agents | [.agents](.agents/README.md) and [AGENTS.md](AGENTS.md) |

Reviewed runtime prompts live in `alladin/finance_prompts`. Separately preserved
source material is described in [finance_prompt_engineering](finance_prompt_engineering/README.md);
it is not loaded as executable runtime instruction.
