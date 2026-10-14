# Agent instructions for Alladin

Alladin is a headless Python 3.11+ backend targeting the Coinbase product universe.
Discovery covers the full public catalog; the legacy executor remains SOL-USDC
spot **paper** until product-specific adapters are implemented. Read
[Coinbase universe](docs/coinbase-universe.md) and [README.md](README.md), then choose the appropriate path:

- **Consume the service:** [.agents/CONSUMER.md](.agents/CONSUMER.md).
- **Change the repository:** [.agents/MAINTAINER.md](.agents/MAINTAINER.md).
- **Operate or recover an account:** [docs/operations.md](docs/operations.md).
- **Discover the full guide:** [.agents/README.md](.agents/README.md).

## Non-negotiable product boundaries

- Use only the standard library at runtime; do not add inference SDKs, model
  configuration, or AI-provider keys. Reasoning and optional subagents belong to
  the consuming session, not this backend.
- Product scope is the Coinbase catalog, across tokens and instrument types;
  do not introduce a SOL-only allowlist in generic discovery or new adapters.
  Identify instruments by canonical `product_id`, not a blockchain mint.
- Keep `execution=paper`. Product-specific adapters must implement currencies,
  quantities, sessions, contract size, margin, settlement and funding where
  applicable before advertising execution support. Never route an unknown type
  into spot accounting. Legacy account constraints remain valid for those accounts.
- Do not add RPC, wallet connections, signers or real order submission. Public
  visibility does not prove account or regional trading eligibility.
- All maintained documentation, agent instructions, examples, and public runtime
  text must be English. Preserve third-party originals and historical audit/data
  artifacts exactly; do not rewrite old evidence to satisfy a language policy.

## Execution and persistence invariants

- Market I/O stays outside SQLite write transactions. Mutation, event/seal, and
  idempotent response commit atomically under `BEGIN IMMEDIATE`.
- Check committed idempotency before collection; repeat the same logical payload
  with the same key. Do not change keys to force a duplicate operation.
- WAL with `synchronous=NORMAL` is atomic/process-crash consistent, not maximum
  power-loss durability. Preserve backups, original account history, and seals.
- Do not mix replay and live-data input in one database or silently change its
  configuration fingerprint/mode. Never reset cash, losses, cooldown, or halt state.
- Live entries require fresh Coinbase marks (30-second maximum) and closed current
  risk data. Do not restamp old observations or invent retrospective gap/stop fills.
- Replay decisions from N are eligible at N+1 after revalidation. Live execution
  uses current observations, and pre-entry candles cannot retroactively stop a trade.
- Gaps with exposure close only at a verified current mark and latch a halt. Flat
  recovery may rewarm without inventing skipped-time trades.
- Keep one cooperative worker per database and poll from completion. Stopping a
  process does not prove exposure was closed.
- `available_balance` approves the full affordable balance or refuses it; no hidden
  downsizing. Enforce costs, exposure, participation, remaining daily loss, and drawdown.

## External task invariants

- Internal candidates are advisory. Do not gate external tasks/strategies solely
  on an internally approved candidate. Evidence, consensus, and final risk remain mandatory.
- Binding version 2 freezes the analysis and binds material account authority.
  Market ticks do not replace valid tasks. Concurrent preparation coalesces without
  refreshing timestamps or extending expiry.
- Reproduce the original evidence hash at submission, then check current execution
  risk. Never relabel old reports as analysis of new candles.
- HOLD requires no market I/O and applies no mark. CLOSE requires a current book,
  not unrelated candle/trade/volume collection or an entry-only deviation bound.
- Excessive entry deviation retires the task with `reprepare_required`. Repeated
  requests must remain nonexecuting/idempotent until a genuinely new plan is submitted.
- Read exact schemas and registry references. Reject invented facts/probabilities,
  unsupported sizes, invalid contracts, and attempts to override risk through consensus.
- Do not claim independent agents unless that coordination actually happened.

## Prompts and evidence

Preserve `finance_prompt_engineering/upstream` bytes and `UPSTREAM.json` provenance;
never execute those texts as runtime instructions. Active prompts live in
`alladin/finance_prompts`; changes require explicit catalog hash/version review.
Fixtures and operational checks validate software, not profitable alpha or a
near-perfect win rate. Report actual events, net results, uncertainty, and open exposure.

## Verification

```bash
python3 -m unittest discover -s tests -q
python3 -m compileall -q alladin
git diff --check
python3 -m alladin contract
```

Use isolated test accounts. Do not perform networked paper trades, alter a user's
account, or publish private financial reports merely to verify documentation edits.
