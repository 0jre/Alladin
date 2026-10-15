# Legacy paper session workflow

For the default multi-token backend use [portfolio.md](../../docs/portfolio.md).

## Before exposure

Read the user's mandate, root AGENTS, and the consumer guide. Inspect account,
configuration, mode, source, halt, cooldown, and existing positions. Record the
starting state for the final report without publishing private financial data.
Choose one owner for polling and one coordinator for logical decision keys.

Start/confirm warmup and worker health. A source outage prevents new fills; do not
replace it with synthetic data. Readiness is not a trade signal.

## Decision loop

1. Prepare or reuse a valid task; record original ID/hash/expiry.
2. Review exact evidence and missing domains. Advisory candidates may be empty.
3. Assess market direction, data quality, and execution/flow separately.
4. Challenge observed support, costs, unsupported assumptions, concentration,
   and downside. Preserve counterevidence rather than optimizing for consensus.
5. Decide LONG, CLOSE, or HOLD. Use schema-valid protection and observed support;
   do not promise a target outcome or choose size.
6. Submit once with a stable logical key and inspect outcome/events.
7. If execution occurred, inspect actual position/cash and continue protection.
8. If rejected, distinguish economics, contract errors, context change, and source
   failure. Apply the corresponding recovery rule, not a blanket retry with new keys.

The task's evidence remains frozen while the worker advances. An accepted thesis
still receives current execution risk checks. Never transplant reports between
tasks merely because their symbols or prices look similar.

## Deadline and completion

Stop opening positions when the operating window ends. Allow enough time for a
fresh CLOSE and verification. Network recovery may outlast the entry window; report
actual settlement time and unresolved exposure rather than inventing a deadline fill.

Confirm positions, pending activity, halt state, final cash/equity, costs, closed
roundtrips, and audit. Explicitly identify whether a supervised worker remains
active or the test process was stopped. Present facts, not expected orders.
