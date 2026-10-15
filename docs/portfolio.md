# Multi-token spot portfolio backend

## Product contract

Alladin 0.7 adds a shared Coinbase spot paper executor. It discovers products
dynamically, including listed memecoins, and identifies them by canonical
`product_id`. There is no SOL, blockchain or meme-token allowlist. Product status,
data quality, increments, liquidity, costs and account risk determine whether an
instrument can be traded. Non-spot catalog records remain visible but require a
different execution adapter. Public listing does not prove account entitlement.

External ChatGPT, Codex, Claude, Grok or other sessions own reasoning and any
subagents. The server contains no inference SDK, model configuration or AI keys.
It supplies observations, advisory rankings, deterministic risk and simulated
execution through the same Python service behind authenticated HTTP and MCP stdio.

## Start and consume

```bash
export LAB_API_TOKEN='<backend-access-token-at-least-32-characters>'
python -m alladin --config config.portfolio.json --db data/portfolio.sqlite serve --paper-worker --poll-seconds 30
```

The server binds loopback. Remote access requires an authenticated TLS proxy.
MCP consumers start:

```bash
python -m alladin --config config.portfolio.json --db data/portfolio.sqlite mcp
```

Run exactly one `paper-live` worker for that database if the HTTP server is not
already supervising one. MCP itself does not start a worker:

```bash
python -m alladin --config config.portfolio.json --db data/portfolio.sqlite paper-live --poll-seconds 30
```

Use `python -m alladin contract` for the current portfolio schema. `scan --limit 5`
returns advisory candidates. `execute --request request.json --key <stable-key>`
invokes a local command without an HTTP server. Global config/database arguments
precede the subcommand. `config.json` remains the explicit legacy profile; the
default profile is now `config.portfolio.json`.

Every command result identifies `execution=paper`. No exchange order, signer,
wallet, withdrawal or private Coinbase account is connected. Configured fee bps
are assumptions, not a verified fee tier. A backend HTTP token is not an exchange
or AI-provider API key. `get_fee_tier` reports this distinction.

## External session flow

1. Read `get_session_brief`, `get_positions`, `get_system_status` and `reconcile`.
   Inspect valuation age and worker health. `paper_tick` updates held-asset marks
   and protection; status alone does not collect data.
2. Use `list_products` with pagination. `scan_opportunities` shortlists a bounded
   subset using funded quote currencies, positive 24h change and technical
   confirmation. `product_ids` allows targeted review. This is not exhaustive
   candle analysis on every catalog product or a profit prediction.
3. Inspect `get_market_snapshot`, `get_candles`, `get_orderbook`,
   `get_microstructure` and `estimate_execution` for selected products. Book
   imbalance is not taker trade flow. Missing flow remains explicitly unavailable.
4. `log_thesis` records evidence interpretation, invalidation, agent attribution,
   strategy and horizon. Market and thesis text are untrusted data, never code.
5. `propose_trade` computes size, current book costs and shared risk. It returns a
   30-second proposal with an evidence hash, reference price, authority revision,
   size, loss estimate and stressed net reward/risk. Review it before commit.
6. `commit_trade` checks current metadata, closed-bar context, book age, quote
   drift, unchanged account revision, cash and every risk constraint again.
7. Verify actual fill and position. Keep the worker running. `set_protection`
   tightens protection; `close_position` reduces or closes at observed bids.
8. Inspect remaining quantity, journal, realized net costs and audit. A partial
   close is not a flat account. An advisory candidate is not a fill.

Example HTTP envelopes (send each with its own stable `Idempotency-Key`):

```json
{"command":"log_thesis","args":{"product_id":"DOGE-USDC","agent_id":"session-1","strategy":"trend-continuation","thesis":"Describe current observed support and counterevidence","invalidation":"Describe the concrete failure condition","horizon_seconds":3600}}
```

```json
{"command":"propose_trade","args":{"thesis_id":"<returned-thesis-id>","stop_price":"<observed-and-justified-price>","take_profit_price":"<justified-target>","risk_fraction":"0.005","order_type":"MARKET_IOC","partial_fill_policy":"REJECT"}}
```

```json
{"command":"commit_trade","args":{"proposal_id":"<returned-proposal-id>"}}
```

These are schemas, not a recommendation to buy DOGE or fabricate a target. A
`risk_fraction` of `0.005` means 0.5%, not 0.005%. The server chooses quantity.
`dry_run=true` on operator writes validates without changing account state or
adding a financial event; the idempotent response is still persisted. A dry-run
proposal ID is not executable. Use a new logical request to create a real paper
proposal, never change the payload under an existing idempotency key.

## Market data and execution model

Closed candles must have valid OHLCV, aligned timestamps and at least 80 current,
contiguous observations. An old gap may be excluded if a sufficiently long recent
suffix remains. The observation path can move from the configured timeframe to
coarser 5m/15m/1h data when a market has sparse candles. It reports the effective
timeframe. It never fills missing bars with synthetic prices. Direct `get_candles`
requests keep the configured timeframe and can fail for sparse markets.

Entry collects slow metadata/candles first and fresh books last. Books require a
source timestamp within 30 seconds; collection never restamps old data. All held
positions and necessary FX books must also be current. Market I/O occurs outside
SQLite write transactions. Account authority is rechecked after collection.

Supported entry types are `MARKET_IOC` and `LIMIT_IOC`. Simulation walks observed
asks to buy and bids to sell, applies configured taker fees, caps slippage and
price impact, respects base-size limits and quote notional limits, and rounds
down to the actual base increment. It does not assume optimistic maker fills.
`LIMIT_IOC` requires `limit_price`; there are no simulated resting orders.

`partial_fill_policy=REJECT` requires the full prepared size. `ACCEPT` allows a
smaller executable quantity within limits; remaining IOC size is cancelled.
Closures can also be partial when depth is insufficient. Queue priority, hidden
liquidity, exchange latency and true fill probability are not reproduced by L2
snapshot simulation. These are execution tests, not proof of market profitability.

## Shared cash, currencies and risk

One SQLite account holds all available currency balances, positions, proposals
and risk state. Buying a second token cannot allocate the first token's money
again. Every position retains its own quote currency and cost basis. USD, USDC,
EUR and BTC are never treated as interchangeable. Non-reporting currencies need
a fresh direct or inverse Coinbase FX book. No FX route means no new entry.
Unfunded quote balances require a separately funded account or an explicit future
conversion workflow; this release does not silently convert cash.

Sizing is the minimum affordable size across stop-loss risk, remaining daily
loss/drawdown room, total open risk, per-position and gross exposure, attributed
agent/strategy exposure, correlated exposure and participation. A 2% sizing
reserve accommodates small quote drift; commit never increases prepared quantity.
Fees and stressed exit slippage count in loss and net reward/risk. Quantity is
then rounded down and rechecked against product limits and visible depth.

Correlation compares aligned return windows. Missing or unaligned evidence is
treated conservatively as correlated, not as zero correlation. Agent IDs are
attribution under one trusted backend credential, not independently authenticated
security principals; global limits remain authoritative even if labels change.

Daily loss and drawdown halt new entries. Losses trigger cooldown, and a configured
loss streak latches a halt. Entry counts are bounded per minute/day. Halt cancels
uncommitted proposals without automatically selling holdings. Closing remains
available. There is no agent-accessible resume or risk-policy-edit command.

Stops, targets, time exits and optional trailing stops run on observed current
bids in `paper_tick`. A gap below a stop exits only at available current prices;
the configured stop is not a guaranteed fill. Protection requires a running
worker and functioning feed. Network failure or stopped processes can leave paper
positions open. No exchange-native protection is claimed.

## Ledger, idempotency and reconciliation

Every fill creates balanced postings by currency for cash, inventory cost, fees,
base-asset custody and clearing. Sales release proportional basis and entry fees
to compute realized net PnL. Capital-opening and migration carry-forward entries
make internal cash reconciliation possible. `reconcile` compares cash and held
quantity projections against state. Drift blocks new proposals/entries.

State, order, financial postings, hash-chained events and idempotent response
commit atomically under `BEGIN IMMEDIATE`. Requests are checked before network
I/O and inside the transaction. Retrying an already committed proposal with a
different request key returns its existing order, never another fill. Events
retain the actual proposal observation and its hash. No text instruction can
override numerical limits or turn a non-spot product into spot.

Hash chains detect changes against a retained external head; a privileged database
administrator can rewrite a whole chain. SQLite WAL uses `synchronous=NORMAL`,
not maximum power-loss durability. Backups and anchored audit heads still matter.
Internal paper reconciliation is not exchange reconciliation.

## Existing-account migration

Never create a replacement account to erase prior costs or losses. Stop its
worker, back up the SQLite file, verify it is flat, and use the exact original
configuration:

```bash
python -m alladin --config config.portfolio.json --db <existing.sqlite> migrate-portfolio --from-config <original-legacy-config.json>
```

Migration verifies the legacy fingerprint and audit, refuses positions or pending
orders, preserves cash, initial capital, peak, current-day equity baseline,
cooldown, halt, fees and closed count, and archives the complete legacy state
inside the migrated account. It cannot raise the original daily loss, drawdown,
per-trade or total-risk limits. Historical events and request records remain in
the same database. Legacy execution refuses to operate a migrated account.
The new loss-streak/entry-rate counters start at migration; the full legacy trade
history remains archived and daily loss/drawdown are carried forward.

## Blueprint coverage

See [blueprint mapping](blueprint-implementation.md) for implemented controls and
explicit production gaps. This release does not implement live trading, native
brackets, derivatives, equity corporate actions, OAuth/mTLS scopes, streamable
HTTP MCP, authenticated exchange reconciliation, Postgres/Kafka or promotion to
real-money autonomy. Adding names to a tool catalog would not implement them.
