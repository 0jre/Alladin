# External session protocol

> Default backend: [multi-token portfolio](portfolio.md). The detailed legacy
> procedures below apply to explicit legacy accounts unless stated otherwise.

## Identity and authority

The protocol is `external-session-v2`, task binding version `2`. Alladin prepares
evidence and checks submissions; the consuming session supplies reasoning. No
inference provider, model, or AI key is configured in the service.

An active worker or consumer-owned `paper_tick` loop must keep position protection
running. `demo-live` exports observations/tasks but does not author or submit plans.

## Prepare and inspect

Call `prepare_decision` after warmup. A successful task includes:

| Field | Meaning |
|---|---|
| `id` | Exact task identity for submission |
| `protocol`, `binding_version` | Compatibility surfaces |
| `context_sha256` | Material account authority at preparation |
| `evidence_sha256` | Exact frozen analytical evidence |
| `created_at`, `expires_at`, `status` | Original deadline and consumption state |
| `evidence` | Features, snapshot, portfolio, candidates, economics, configuration, missing domains, registry |
| `instructions` | Reviewed role-specific prompt text |
| `report_schema`, `decision_schema` | Actual required JSON contracts |
| `stages` | Market/quality/flow, then challenger, then manager |

The task expires after `min(300, 2 × timeframe_seconds)` seconds: 120 seconds for
one-minute candles, 300 seconds for five- or fifteen-minute candles. It is not
renewed by reuse. Parallel preparation and normal market updates return the same
valid task instead of replacing an analysis already in progress.

Material account changes invalidate authority. New candles, marks, peak updates,
and trailing-stop movement alone do not. Submission evaluates the frozen evidence
and independently rechecks execution against the current account and market.

## Evidence discipline

Use only exact identifiers present in `evidence.evidence_registry`. Each registered
value includes its source and availability time. Null/unavailable fields do not
become observations. Reference examples such as `features.rsi` and `snapshot.price`
are valid only if present in that particular task.

Candidates and their economics are advisory. An empty or risk-rejected candidate
list does not prevent external analysis. A different named strategy is permitted,
but must be supported by observed evidence and pass all final controls. Do not
invent a target, probability, news event, or data source to obtain approval.

`entry_conditions` and `counterevidence_keys` contain registry references, not code
or a predicate language. Natural-language thesis/invalidation is assessed by the
consumer; the backend cannot prove its predictive validity.

## Specialist reports

The `reports` object has exactly `market`, `quality`, `flow`, and `challenger`.
The manager is the separate `decision` object. Every report requires:

| Field | Contract |
|---|---|
| `stance` | LONG, SHORT, HOLD, or CLOSE; SHORT is opposition, not enabled short execution |
| `score` | Finite number in [0, 1]; descriptive, not a win probability |
| `summary`, `invalidation` | Nonempty strings, at most 2,000 characters |
| `evidence_keys` | Exact unique references; at most 20, each at most 200 characters; required for non-HOLD |
| `concerns`, `missing_data` | String lists; at most 20 entries of at most 500 characters |
| `risk_flags` | Same list limits; values from the allowed flags below |
| `blocking` | Boolean veto flag |
| `score_is_probability` | Must be `false` |

Allowed risk flags: `data_quality`, `costs`, `liquidity`, `concentration`,
`model_uncertainty`, `contradictory_evidence`, `unsupported_assumptions`.

Coordinate the first three perspectives without disclosing peer answers when the
session has independent agents. Give their reports to the challenger, then the
review to the manager. If one coordinator performs all perspectives, disclose
that fact; four JSON objects do not prove independent authorship. The backend
checks structure and agreement, not identity or statistical independence.

## Manager plan

The `decision` object requires exactly:

| Field | Contract |
|---|---|
| `action`, `market` | LONG/HOLD/CLOSE and `spot` |
| `confidence` | Descriptive finite score in [0, 1] |
| `stop_fraction` | 0.005–0.10 |
| `take_fraction` | 0.005–0.30 |
| `horizon_bars` | Integer 1–96 |
| `thesis`, `strategy` | Strings up to 2,000 and 100 characters respectively; use meaningful values |
| `evidence_keys` | Exact references; nonempty for LONG/CLOSE |
| `invalidation` | Nonempty string up to 2,000 characters |
| `entry_conditions` | Exact references; nonempty for LONG |
| `exit_conditions` | List of allowed exit labels, at most 10 |
| `counterevidence_keys` | Exact references, possibly empty |

Reference lists follow the report reference bounds. Exit labels are
`configured_stop`, `configured_take`, `time_exit`, `signal_reversal`, and `feed_failure`.
A LONG needs `configured_stop`, at least one `features.*` and one `snapshot.*`
evidence reference, at least two LONG supporters among market/quality/flow with
scores at or above `min_confidence`, no blocking report, no contrary SHORT/CLOSE
assessment, and deterministic risk approval. CLOSE requires an existing spot
position; entry consensus/veto logic does not prohibit reducing that exposure.

Never add `qty`, `notional`, `leverage`, or `mint` to the manager plan. The backend
selects the configured instrument and computes size.

## Submit

Send exactly these arguments with a stable logical idempotency key:

```json
{
  "task_id": "REPLACE_WITH_RETURNED_TASK_ID",
  "evidence_sha256": "REPLACE_WITH_RETURNED_EVIDENCE_HASH",
  "session_id": "truthful-consumer-session-identity",
  "reports": {},
  "decision": {}
}
```

The empty objects above are intentionally incomplete. Use returned schemas and
actual assessments. A full non-trading payload skeleton is provided in
[.agents/examples/decision-template.json](../.agents/examples/decision-template.json).
It is not a trading recommendation or fabricated review.

For live-data LONG, the backend fetches current closed risk features and a fresh
full Coinbase snapshot. The original quote is never rejuvenated. It checks entry
drift, current account limits, and costs again. CLOSE needs a current book only;
an adverse price move cannot be rejected solely by an entry deviation guard.
HOLD performs no market I/O and applies no protective mark itself; the worker
remains responsible for protection.

In replay, approved actions schedule next-bar execution. The two input modes
cannot be mixed in the same account.

## Outcomes and recovery

| Observation | Required consumer action |
|---|---|
| `submitted/opened` | Verify OPEN event and actual position/size |
| `submitted/closed` | Verify CLOSE event and remaining exposure |
| `submitted/abstained` | Report HOLD; inspect council gates/errors rather than claiming a trade |
| `submitted/risk_rejected` | Read actual approval reasons; do not relax controls to force execution |
| `submitted/scheduled` | Replay action is pending, not yet filled |
| `reprepare_required` | Task was invalidated by drift; prepare, reason again, submit a new plan/key |
| Transient 503 or client timeout | Retry identical command/payload/key while authority is valid; first inspect unknown outcomes |
| Expired/materially invalid task | Prepare new evidence; never copy old reports under a new hash without review |
| Already consumed task | Retrieve the committed response with its original key; inspect state/audit |

Invalid contracts can be consumed as HOLD with an audit error; a 200 response is
not proof of intended action. Successful execution events include provenance:
declared session, protocol, prompt bundle, evidence hash, and source. Audit fields
separate analytical time from current risk and execution observations.

## Operational validation

`execution_check` is a separate explicit OPEN/CLOSE diagnostic. Alternatively an
external submission may use `strategy=execution_validation` with its test purpose
clearly declared. These checks still pass ordinary risk/cost controls. They are
marked/separated from strategy statistics, while costs, PnL, cooldown, daily loss,
and drawdown continue to affect the account. Do not substitute them for alpha
trades without disclosing their diagnostic purpose.
