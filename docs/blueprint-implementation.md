# Blueprint implementation map

The user-supplied October 14, 2026 blueprint informed the portfolio implementation.
Its live-trading and institutional infrastructure sections are a broader
specification, not features obtained by adding tool names. This release completes
the multi-token **spot paper** path. It does not claim the entire go-live checklist.

| Blueprint area | Current implementation |
|---|---|
| Agent proposes, backend controls risk | Structured thesis, expiring proposal, server sizing, current-risk commit |
| Explicit mode | `execution=paper` in command results; no private exchange credentials |
| Product normalization | Canonical product ID, metadata, currencies, base increments, quantity/notional limits and status |
| Market and evidence | Coinbase public REST books/closed candles, causal indicators, sparse-data rejection/coarser timeframe disclosure |
| Opportunity selection | Dynamic catalog, diverse base assets, bounded scanner, trend/volume/volatility/cost evidence; no predicted win probability |
| Execution | L2 snapshot walk, taker fees, IOC/limit IOC, slippage/collar, partial depth and cancellation of remainder |
| Proposal lifecycle | PROPOSED → COMMITTED, CANCELLED or EXPIRED; material account revision and quote drift checks |
| Duplicate/timeout safety | Request idempotency plus proposal-level duplicate prevention; no external order submission/UNKNOWN state is simulated |
| Shared risk | Cash, daily loss/drawdown, stop/open risk, gross/concentration, attribution and conservative correlation limits |
| Kill switch | Latching entry halt with proposal cancellation; closures allowed; no agent resume |
| Portfolio accounting | Shared multi-currency cash, positions, cost basis, balanced per-currency postings and net realized PnL |
| Reconciliation | Internal cash/quantity projections against postings; new entries blocked on drift |
| Persistence | Atomic SQLite state/events/responses; retained evidence and hash seals; legacy archive/migration |
| Agent ergonomics | Strict MCP tool schemas, session brief, resources, reviewed session/checklist/review/risk prompts |
| Verification | Multiple assets/quotes, small-price tokens, concurrency, idempotency, stale/gapped data, drift, partial fills, halt, migration and HTTP/MCP tests |
| Protected exits | Current observed worker exits; not native exchange orders |

## Explicit production gaps

- **Live exchange adapter:** no authenticated trading, order preview, signed JWT,
  KMS/HSM, actual fills, native brackets or authenticated account reconciliation.
- **Other instrument accounting:** futures/perpetual collateral and funding,
  option exercise/settlement and equity corporate actions require separate adapters.
- **MCP deployment:** stdio is implemented. Streamable HTTP MCP, OAuth 2.1, mTLS,
  independently authenticated agent scopes and subscriptions are not implemented.
  HTTP uses a shared backend bearer token behind an operator-managed TLS proxy.
- **Market streaming:** bounded REST observations, not sequenced WebSocket L2
  reconstruction. Resting orders, maker queue position, TWAP, iceberg and exchange
  latency are not simulated. Do not infer performance equivalence with live fills.
- **Infrastructure:** SQLite, not Postgres/Timescale/Redis/Kafka; local hash seals,
  not an administrator-proof immutable event store; no production pager routing.
- **Autonomy promotion:** no automatic L0–L3 promotion or operator resume command.
  Attribution labels are not authenticated risk domains. External sessions own
  coordination and must disclose actual independent review.

## Source of truth

`SpotService`, `SpotPolicy`, `SpotMarket`, `spot_tools.specifications()` and the
focused tests define implemented behavior. Legacy `Service` retains its previous
account protocol. Use [portfolio.md](portfolio.md) for operational details and
migration; never route a catalog record to an incompatible accounting model.
