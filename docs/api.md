# API reference

Read-only `catalog`, `instrument` and `instrument_book` commands share the command
transport described below. They cover the public Coinbase universe independently
of legacy mint-based execution. See [schemas and capability limits](coinbase-universe.md).

## HTTP transport

Start `serve` with a `LAB_API_TOKEN` of at least 32 characters. The standard-library
server binds to `127.0.0.1`; remote access needs a separately configured authenticated
TLS proxy. All `/v1/*` routes require `Authorization: Bearer <token>`.
`/health` and `/ready` are public process/readiness probes.

| Route | Returns |
|---|---|
| `GET /health` | Process identity and execution mode |
| `GET /ready` | `{"ready":true}` with 200, or false with 503 |
| `GET /v1/health` | Attached worker health, mode, halt state, last bar, decision error |
| `GET /v1/status` | Cash/equity, positions, costs, pending activity, last decision, active task, universe, blocks |
| `GET /v1/contract` | Implemented endpoint/command inventory |
| `GET /v1/diagnostics` | Read-only source checks and baseline profile feasibility |
| `GET /v1/performance` | Observed strategy statistics and separate validation counts |
| `GET /v1/prompts` | Prompt version, hashes, roles, source commit |
| `GET /v1/prompts/{role}?regime=range` | Reviewed role instructions; regime is optional |
| `GET /v1/audit?limit=100` | Recent events; HTTP limit is bounded to 1–1,000 |
| `GET /v1/audit/verify` | Hash-chain validity, event count, current head |
| `POST /v1/commands` | Wrapped command result |

### Command envelope

```http
POST /v1/commands
Authorization: Bearer <backend-token>
Content-Type: application/json
Idempotency-Key: session-01-prepare-01

{"command":"prepare_decision","args":{}}
```

The body contains **exactly** `command` and `args`. `args` is an object. Body length
must be 1–200,000 bytes; transfer encoding is rejected. An idempotency key is a
nonempty string of at most 128 characters. It identifies one logical command and
payload, not an HTTP attempt.

A successful HTTP response is `{"result": <command-result>}`. The result is itself
an object. `BackendClient.command()` unwraps it. HTTP 200 does not mean a trade
occurred: inspect `result`, `outcome`, approval reasons, and `events`.

### Core commands

| Command | Arguments | Effect |
|---|---|---|
| `paper_tick` | `{}` | Read Coinbase, warm/advance history, update protection; no external reasoning |
| `prepare_decision` | `{}` | Return/reuse a frozen task or report precheck abstention |
| `submit_decision` | `task_id`, `evidence_sha256`, `reports`, `decision`, `session_id` | Validate the external plan; paper mutation only if permitted |
| `analyze` | `{}` | Analyze stored context; does not schedule an order |
| `evaluate` | `proposal` | Risk evaluation only; does not execute |
| `execution_check` | `action`, `check_id`, `purpose`, optional OPEN `proposal` | Explicit operational OPEN/CLOSE test, not strategy performance |
| `halt` | `{}` | Latch a halt; protection/flattening needs subsequent valid processing |
| `finalize` | `{}` | Settle research positions at stored marks and latch finalization |
| `ingest` | `candle`, `snapshot` | Controlled replay feed; separate temporal semantics |
| `universe` | `{}` | Inspect historical mint funnel |
| `admit` | `snapshot` | Classify a research snapshot |
| `watch` | `mint`, optional `arm` | Watch/arm an eligible research mint |
| `unwatch` | `mint` | Remove a watched research mint and its pending action |

The universe tools do not enable additional live Coinbase products. Live collection
remains restricted to native SOL and `SOL-USDC`.

### Results and failures

`paper_tick` can return `warmed_up`, `resynchronized`, `waiting_for_closed_bar`, or
`processed`; inspect associated events and halt state. Warmup/resynchronization
does not manufacture trades for elapsed time.

`prepare_decision` normally returns `awaiting_external_agents` with `task`.
`reused=true` means the same unexpired authority/evidence was returned, not refreshed.
Safety prechecks can return `abstained`; no task is fabricated to bypass them.

`submit_decision` returns `submitted` with `outcome`:

| Outcome | Interpretation |
|---|---|
| `opened` | At least one OPEN event committed |
| `closed` | At least one CLOSE event committed |
| `abstained` | Resulting proposal is HOLD; no execution quote is needed |
| `risk_rejected` | Requested directional plan did not receive current final approval |
| `scheduled` | Approved replay action is pending the next eligible bar |

An excessive entry-price deviation returns `reprepare_required` /
`context_rejected`, invalidates that task, and produces no fill. See the
[protocol](external-sessions.md) for consumer recovery.

| HTTP status | Meaning and action |
|---|---|
| 400 | Invalid request/session, stale authority, conflicting idempotency payload; inspect `detail`, correct/reprepare as appropriate |
| 401 | Missing or incorrect backend authentication |
| 404 | Unknown route/prompt |
| 413 / 415 | Invalid body size/encoding or content type |
| 503 `command_busy` | Another HTTP mutation is active; retry the same logical request/key with backoff |
| 503 `provider_unavailable` | Source/collection failure; inspect `code`, `stage`, `source`, optional `Retry-After` |
| 500 | Unexpected backend error; inspect state/audit before recovery; do not change the key to force another trade |

Machine-readable codes are the integration contract. Human-readable `detail`
messages may evolve. A timeout is an unknown client outcome until the identical
request/key is repeated or state/audit is inspected. Never assume it proves failure.

## MCP over stdio

Launch from the repository root or an installed package:

```bash
python3 -m alladin --config config.json --db data/paper.sqlite mcp
```

This implementation uses **Content-Length-framed JSON-RPC 2.0**, with stdout reserved
for frames. It accepts initialization versions `2024-11-05`, `2025-03-26`, and
`2025-06-18`, falling back to `2024-11-05`. It is not Streamable HTTP or an
unconditionally interchangeable newline-delimited adapter. Verify client framing.

Supported methods: `initialize`, `ping`, `tools/list`, `tools/call`, `prompts/list`,
and `prompts/get`. Commands use their names above. Read tools are `alladin_status`,
`alladin_diagnostics`, `alladin_performance`, `alladin_audit`, and `alladin_contract`.
Prompt names are `alladin_market`, `alladin_quality`, `alladin_flow`,
`alladin_challenger`, and `alladin_manager`.

For mutations, supply `idempotency_key` in tool arguments. If omitted the server
generates a new key, which does **not** make separate client retries idempotent.
MCP `alladin_audit` limits results to 1–500. Successful tool content contains JSON text with the unwrapped command result.
`isError=true` means failure; inspect the returned text before retrying. MCP itself
needs no backend HTTP token and does not start a paper worker.

## CLI and Python

Global flags precede the subcommand: `--config`, `--db`, and `--agents external|rules`.
CLI subcommands use hyphens (`paper-tick`); JSON commands use underscores (`paper_tick`).
Run `python -m alladin --help` for the complete inventory. `call` sends a request
file through HTTP:

```bash
python3 -m alladin call --url http://127.0.0.1:8080 --request docs/request_analyze.json --key session-01-analysis-01
```

The minimal Python client uses `LAB_API_TOKEN` or an explicit constructor token:

```python
from alladin.client import BackendClient

client = BackendClient("http://127.0.0.1:8080")
state = client.status()
task_result = client.command("prepare_decision", {}, "session-01-prepare-01")
# The consuming session now reviews task_result; this snippet does not submit a trade.
```

The client supports loopback HTTP or remote HTTPS, rejects URL credentials, and
does not automatically retry mutations. An endpoint/tool schema adapter is in
[tools_adapter.py](tools_adapter.py); it does not instantiate an inference model.
