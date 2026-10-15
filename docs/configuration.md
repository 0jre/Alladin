# Configuration reference

> Default backend: [multi-token portfolio](portfolio.md). The detailed legacy
> procedures below apply to explicit legacy accounts unless stated otherwise.

`Config.load(path)` reads JSON; unknown/malformed fields fail validation. Always
select the intended file explicitly. The values below distinguish the repository
profile from unchanged legacy class defaults used when a field is omitted.

| Field | Repository `config.json` | Class default / meaning |
|---|---|---|
| `chain` | `solana` | Required asset metadata; not an RPC connection |
| `execution` | `paper` | Only supported execution mode |
| `mint` | Inherited | Native SOL mint |
| `allowed_markets` | `["spot"]` | Only permitted enabled market set |
| `timeframe_seconds` | 900 | Live collection supports 60, 300, 900 |
| `initial_usdc` | 250 | Class default 10,000; initializes new accounts only |
| `sizing_mode` | `available_balance` | Class default `risk_budget` |
| `risk_per_trade` | 0.02 | Class default 0.003; fraction of equity |
| `max_open_risk` | 0.02 | Class default 0.01 |
| `max_position_fraction` | 1.0 | Class default 0.15 |
| `max_gross_fraction` | 1.0 | Class default 0.30 |
| `max_net_fraction` | 1.0 | Class default 0.20 |
| `max_daily_loss` | 0.02 | Fraction of UTC day-start equity |
| `max_drawdown` | 0.06 | Fraction below recorded peak |
| `min_reward_risk` | 1.5 | Class default 1.8; net of modeled costs |

Additional inherited controls:

| Field | Default | Meaning |
|---|---|---|
| `warmup_bars` | 80 | Must be at least 80; feature readiness |
| `fee_bps`, `slippage_bps` | 10, 5 | Variable monetary cost assumptions per side |
| `fixed_cost_usdc` | 0.02 | Fixed modeled cost per side |
| `min_confidence` | 0.65 | Descriptive score threshold, not win probability |
| `min_liquidity_usd` | 1,000,000 | Minimum observed centralized depth measure |
| `min_volume_24h_usd` | 1,000,000 | Minimum completed-candle quote-volume estimate |
| `max_pool_participation` | 0.0005 | Notional cap against observed liquidity |
| `max_entry_gap_fraction` | 0.01 | Entry execution price deviation from reviewed snapshot |
| `max_historical_cvar` | 0.04 | Empirical bar tail-loss gate |
| `cooldown_bars` | 4 | Cooldown after a net losing close |
| `trailing_atr_multiple` | 2.5 | Trailing-stop distance in ATR units |
| `max_snapshot_age_seconds` | 1800 | Legacy/replay limit; live execution additionally caps age at 30 seconds |
| `max_watched` | 32 | Historical research universe bound |

Other model fields preserve historical token/perpetual research compatibility.
They do not enable on-chain data or leveraged live execution. Changing
`allowed_markets` to enable perpetuals is rejected.

## Persisted compatibility

The database stores a configuration fingerprint and agent mode. Reopening with a
different effective configuration/mode fails rather than silently changing the
account. Class defaults are deliberately preserved for old fingerprints; do not
assume the shipped profile applies to a programmatic `Config()`.

Do not alter `initial_usdc`, delete a database, or create a replacement account and
present it as continuous history. A new configuration/database is appropriate for
a genuinely separate experiment, identified as such.

## Narrow audited policy revision

`revise-policy` allows **only** a change to `min_reward_risk`. The previous
configuration must match the persisted account exactly. It preserves portfolio,
losses, cooldown, and history, records the before/after fingerprints and policy
change, and cancels pending decisions. It is an administrative operation, not an
automatic response to an unwanted risk rejection.

```bash
python3 -m alladin --config revised-config.json --db data/paper.sqlite revise-policy --from-config previous-config.json
```

Keep the previous configuration and record the rationale outside private runtime
secrets. Other mandate changes need an explicitly reviewed continuity/migration
plan; there is no general automatic migration command.

## Process configuration

`LAB_API_TOKEN` is the only required HTTP access secret; no inference or Coinbase
account credentials are configured. CLI selects config/database/agent mode.
`serve --paper-worker` and `paper-live` accept polling intervals of 10–300 seconds.
Task expiry and live quote limits are enforced by code, not overrides in a manager plan.
