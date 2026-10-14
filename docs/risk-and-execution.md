# Risk and paper execution

## Authority

The risk engine is deterministic and final. External agreement, a strong score,
or an account-growth objective cannot bypass it. The session supplies stop, take,
horizon, thesis, and references; the backend selects the instrument and computes size.

The live product is long-only spot paper. SHORT can express report opposition but
cannot open a spot short. CLOSE reduces existing exposure. HOLD preserves it and
does not perform an execution mark; protection still needs polling.

## Entry gates

Entry requires the configured instrument/product/source, valid fresh observations,
sufficient depth and volume, a ready non-shock feature vector, historical tail risk
within the configured limit, no persistent halt or active cooldown, an enabled
market, no duplicate position, and a sufficient descriptive confidence score.

Economics must also pass net reward/risk after modeled costs. Sizing then enforces
cash, exposure, participation, open risk, and the account's available loss budgets.
The live path rechecks these against the current account and current closed risk
features after the external analysis is complete.

## Cost and sizing model

Let `C` be cash, `E` equity, `F` fixed cost per side, and
`b = (fee_bps + slippage_bps) / 10000` the variable cost fraction per side.
For spot full-balance sizing:

```text
affordable_notional = max(0, C - F) / (1 + b)
entry_cost = affordable_notional * b + F
estimated_stop_loss = notional * (stop_fraction + 2*b) + 2*F
roundtrip_cost_fraction = 2*b + 2*F/notional
net_reward_risk = (take_fraction - roundtrip_cost_fraction)
                  / (stop_fraction + roundtrip_cost_fraction)
```

`available_balance` approves the **whole affordable notional or rejects it**. It
does not silently shrink an order. This sizes deployment of cash, not permission
to lose the whole account.

The permitted notional must fit all exposure caps and
`liquidity_usd * max_pool_participation`. Its estimated stop loss must fit the
minimum of:

- `E * risk_per_trade`;
- remaining aggregate open-risk budget;
- remaining daily loss allowance relative to recorded day-start equity;
- remaining drawdown allowance relative to the recorded peak.

In `risk_budget` mode, the backend instead computes the affordable risk-limited
notional and applies the same exposure/liquidity/cash caps. Both modes reject
notional below 10 USDC and recheck net economics including fixed costs.

These formulas estimate costs/loss, not executable liquidity or maximum possible
loss. Gaps, delayed polling, and real markets can exceed assumptions.

## Why a plausible signal may still be rejected

The repository profile uses 10 fee basis points, 5 slippage basis points, and
0.02 USDC fixed cost per side. Even before fixed cost, roundtrip modeled cost is
0.30%. A 1% stop with a 2.2% gross target can fall short of the required 1.5 net
reward/risk ratio after costs. Small nominal gains can therefore be net losses.

This is an economic refusal, not evidence of a broken API. Do not increase a target
without market support, lower configured fees, reset consumed losses, or weaken
limits merely to obtain a fill. Advisory strategy economics and `doctor` help
explain necessary conditions; neither establishes positive expectancy.

## Paper accounting

The execution reference is a Coinbase midpoint. Variable fee and slippage are
charged as modeled monetary costs, plus fixed cost. The price is not moved a
second time to represent the same slippage. A spot OPEN debits notional plus entry
cost and creates SOL quantity. CLOSE credits current quantity value minus exit
cost. Net trade PnL includes both sides' costs and any applicable historical funding
fields; current configured spot execution has no funding process.

The backend produces local OPEN/CLOSE events, not orders acknowledged by Coinbase.
It does not model order queues, partial fills, real venue fee tiers, route execution,
or adverse order impact. No real funds are moved.

## Exits and protection

- Current marks can trigger observed stop, take, or time exits. They settle at the
  observed current mark, not a better retrospective threshold.
- Closed-bar processing has explicit conservative event ordering for research;
  bars containing pre-entry prices cannot retroactively close a later position.
- Trailing protection uses the best observed close and configured ATR multiple;
  it can tighten the stop without invalidating a pending analytical task.
- A losing CLOSE starts the configured bar-based cooldown.
- A feed gap with exposure closes at a verified current mark and latches a halt.
- Drawdown, daily loss, or nonpositive equity can latch a circuit breaker.

Daily accounting uses UTC calendar days. A latched halt is not automatically
cleared by midnight or process restart. `halt` does not instantly obtain a fresh
exit quote, and stopping a worker leaves positions unmonitored. For a live-data
exit, submit CLOSE and verify the result. `finalize` is stored-mark research settlement.

## Controlled checks and reporting

`execution_check` requires explicit `purpose=execution_validation`, a stable
`check_id`, and a matching close. OPEN needs a flat compatible external paper
account and a LONG/spot `execution_validation` proposal with horizon at most four
bars; normal risk still applies. It is not an automatic fallback when a strategy
abstains.

An externally submitted `strategy=execution_validation` is also an explicit check.
Validation trades remain in account cash, costs, losses, cooldown, and audit, but
are separated from strategy statistics and strategy memory. Always disclose this
purpose; a successful software roundtrip is not evidence of profitable autonomy.
