# Research and evaluation

## Separate three questions

1. Does the software preserve timing, contracts, accounting, and risk invariants?
2. Can this environment currently obtain valid market observations and complete
   paper operations through the intended interfaces?
3. Does a strategy have positive out-of-sample expectancy after realistic costs?

Unit/integration fixtures address the first. Explicit live-data execution checks
help address the second. Neither establishes the third.

## Rules baseline

`--agents rules` uses deterministic candidates and risk checks. It is explicit and
persisted; it cannot silently replace an external session. The current candidate
families are trend following, volume breakout, and mean reversion. They are
heuristics, not validated profitable policies.

In external mode these candidates and cost-stressed economics are suggestions.
An externally supported strategy can differ, but cannot bypass contracts, risk,
or the requirement to cite real evidence. A candidate score and council agreement
are not measured win probabilities.

## Synthetic fixtures

```bash
python3 -m alladin generate-demo --output data/synthetic.jsonl --bars 600
python3 -m alladin --config config.json --db data/replay.sqlite --agents rules replay --feed data/synthetic.jsonl --output results/replay --finalize
```

These commands generate synthetic data and exercise causal accounting. Use a new
database/output for a genuinely separate experiment. Synthetic snapshots and
security fields remain synthetic even if they look plausible. Never report this
as live market trading or historical strategy validation.

Replay schedules an eligible decision from bar N at N+1's opening after revalidation.
Input snapshots cannot contain information available only after the decision bar.
Live-data `paper_tick` uses different execution timing and cannot share the same
input-mode database with replay.

## Chronological validation

```bash
python3 -m alladin --config config.json --agents rules validate --feed data/synthetic.jsonl --output results/validation --folds 3
```

The implementation evaluates fixed parameters across 2–10 chronological blocks,
with prior warmup and a new account per fold. It runs normal and doubled variable/
fixed cost assumptions. It does not optimize parameters or train a model, and does
not evaluate external-agent decisions through a simulated inference client.

The feed must satisfy causal availability, mint matching, and continuity and have
warmup plus at least 40 evaluation bars per fold. Existing validation output
databases are rejected. Independent real historical data, transaction-quality
cost modeling, and genuine out-of-sample review are necessary before inferring edge.

## Performance endpoint

`performance` / `GET /v1/performance` reconstructs closed roundtrips from execution
events and reports wins, losses, breakeven, net PnL, mean outcome, profit factor,
worst trade, and a 95% Wilson interval for the observed win rate. A win is strictly
positive net PnL; breakeven is a non-win. Empty/undefined metrics are null rather
than invented certainty.

It also groups decision contexts by mode/protocol/prompt version. Mixed contexts,
unrecorded origins, open positions, and imported trades limit interpretation.
Source labels are metadata, not independent attestation of data authenticity.

Explicit execution checks and `strategy=execution_validation` roundtrips are
separated from strategy counts and memory. They still affect actual paper account
cash, costs, daily loss, drawdown, cooldown, and audit.

The legacy 900-roundtrip target is a descriptive research diagnostic, not a product
promise. It counts chronological outcomes without dropping losses. Near-perfect
sample wins do not establish the same true win probability; dependence between
trades weakens binomial intervals. Small frequent wins can also be outweighed by
rare large losses. Net expectancy and downside matter as well as win rate.

## Exports and their limits

`export --output <directory>` writes `audit.jsonl`, `summary.json`, `equity.csv`, and
`trades.csv`. This is a research export, not the canonical strategy-only accounting
view. Its trade table includes recorded CLOSE events, including operational checks;
its curve derives from cycle events and may not capture every intrabar observation.
Use `/v1/performance` for separated validation statistics and the complete audit for
execution-level reconstruction. Do not infer a precise intrabar maximum drawdown
or annualized Sharpe from a short export curve.

## Reporting standard

State data source, input mode, account/configuration, strategy/prompt context,
period, closed sample size, cost assumptions, net results, open exposure, failures,
and audit status. Separate software validation from strategy outcomes. Never
remove a losing trade, reset the account, invent a fill, or count an unexecuted plan
as success. Preserve original observations and explicitly identify historical,
synthetic, or missing evidence.
