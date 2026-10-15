# Operations and recovery

> Default backend: [multi-token portfolio](portfolio.md). The detailed legacy
> procedures below apply to explicit legacy accounts unless stated otherwise.

## Supported operating model

Use persistent local storage and one supervised worker per database. The shipped
worker uses POSIX `fcntl` locking and runs on Linux/compatible Unix. HTTP is a
standard-library loopback service, not a public production gateway. An external
reasoning consumer is a separate operational component.

| Process | Responsibility |
|---|---|
| `serve --paper-worker` | HTTP plus one observation/protection worker |
| `serve` | API only; no worker readiness or automatic polling |
| `paper-live` | Worker only; no HTTP and no intelligent consumer |
| `mcp` | Stdio tools/prompts only; no background worker |
| External session | Task review, report/plan creation, submission, outcome verification |

The worker polls after each completed cycle. It backs off on provider failures
and retains the logical key until a successful cycle. It does not fabricate data,
reset an account, or silently substitute rules for external reasoning.

## Health is layered

| Signal | What it establishes | What it does not establish |
|---|---|---|
| `/health` | HTTP process responds | Source availability, worker, signal, or execution |
| `/ready` | Attached worker/feed/session passes readiness conditions | Predictive edge or guaranteed current executable liquidity |
| `/v1/health` | Worker cycles/failures/backoff, halt, last bar, decision error | Independent verification of market history |
| `doctor` / `/v1/diagnostics` | Read-only source check and baseline economic feasibility | Permission or a recommendation to enter |
| `/v1/status` | Durable account and active task | A fresh quote merely because the endpoint responded |
| `/v1/audit/verify` | Consistency of stored event seals | Authenticity against an administrator rewriting the whole database |

`doctor.ready` combines source checks with necessary-condition feasibility of the
configured baseline targets. External strategies can differ, but still need final
risk approval. Inspect `sources_ready`, `profile_feasibility`, and individual checks
separately instead of interpreting a single Boolean as a trading signal.

## Network behavior

Public Coinbase requests are bounded to 20 seconds each; market commands share a
45-second total collection deadline. Retry and body read time count toward that
budget. A `demo-live` window additionally limits collection to its remaining time.
Responses arriving after the deadline cannot mutate the account. Read-only I/O
threads are capacity-bounded and never perform ledger commits.

Transient errors use bounded backoff. `Retry-After` is respected within limits;
excessive delay becomes a controlled failure, not an unbounded sleep. Persistent
upstream unavailability becomes HTTP 503. The provider may return throttling or
errors; the product cannot guarantee that an upstream API never emits 429.

Failure diagnostics include `source`, `stage`, and `code` when available:

| Stage/code | Interpretation | Operational response |
|---|---|---|
| `proxy_tunnel` | Failure before Coinbase TLS/API response | Check permitted outbound proxy/host access |
| `connection`, `dns_failure` | Network or name resolution | Inspect environment networking |
| `tls_handshake` | TLS establishment | Inspect trust/proxy compatibility; do not disable verification |
| `response_headers`, `response_body` | Waiting for/reading source data | Retry within bounded budgets; inspect provider availability |
| `deadline_exceeded` | Total permitted collection time exhausted | Preserve state; repeat the logical request only while authority remains valid |
| stale/invalid data | Observation cannot support execution | Obtain a new valid context; do not restamp timestamps |

Keep secrets out of logs. Access headers, private keys, raw credentials, and private
financial session reports do not belong in repository commits.

## Start and supervise

The [quickstart](getting-started.md) runs from a source checkout. For a Linux service,
review [deploy/alladin.service](../deploy/alladin.service): it expects a dedicated
`alladin` user/group, code at `/opt/alladin`, a config there, environment variables
in `/etc/alladin/alladin.env`, and writable state under `/var/lib/alladin`.

Provision paths/ownership and the backend token before installing the unit. The
unit is a template, not an installer. Its read-only filesystem restrictions require
the database to remain in the allowed state directory. Use `Restart=on-failure`,
alerts for worker failures, and a shutdown timeout longer than the collection budget.

The [Dockerfile](../Dockerfile) also binds the service to container loopback. On
Linux, host networking with a separately managed local TLS proxy is one supported
deployment arrangement. Merely publishing a port does not change a process bound
only to container loopback. Persist `/app/data`, supply `LAB_API_TOKEN` securely,
and do not bake secrets or account databases into the image.

There is no deployed hosting service or automatic connector installation in the
repository. Supervising the backend does not keep a chat session reasoning forever.

## Account continuity and backups

Retain the exact effective configuration, agent mode, database, and independent
audit heads. Reopen the same account after restart; do not reset cash or losses.
Keep database access restricted to trusted operators.

Use SQLite's online backup API or stop all writers before a consistent filesystem
backup. Copying only the main file while WAL writers are active is not a safe
backup procedure. Example with an existing initialized account:

```python
import sqlite3

with sqlite3.connect("data/paper.sqlite") as source:
    with sqlite3.connect("data/paper.backup.sqlite") as destination:
        source.backup(destination)
```

Protect backups like the live account. Test restore into an isolated location,
using the matching configuration/mode, and verify the audit before operating it.
Never run the restored copy and call it continuous history without documenting the fork.

## Recovery runbook

1. Inspect status, current exposure, last committed response, health, and audit.
2. If a client timed out, repeat the identical request/key before assuming failure.
3. If source data is unavailable, restore permitted connectivity; do not manufacture
   observations or weaken risk controls. Keep unresolved exposure visible.
4. For `command_busy`, wait/back off and repeat the same logical key.
5. For expired or materially changed authority, prepare fresh evidence and reason again.
6. For `reprepare_required`, the old task is invalidated; do not relabel old reports
   with a new hash.
7. For a gap while flat, allow rewarm without retrospective fills. For a gap with
   exposure, verified-mark recovery closes and latches a halt.
8. A halted account needs explicit operator review. There is no general resume or
   loss-reset command; do not edit SQLite to bypass a safety latch.

## End a live-data session

Stop opening new exposure, request CLOSE for any held position, verify its actual
event or a previously completed protective exit, inspect that positions are empty,
and verify the audit. Then stop the worker/server. If a fresh book cannot be
obtained, report the remaining position and keep recovery/protection supervised.

`halt` is a persistent safety latch, not proof that a sale already occurred.
`finalize` is research settlement at the stored mark, not a fresh Coinbase exit.
SIGTERM/interrupt stops polling and can leave positions open; CLI output reports
that condition for `paper-live`.

## Operational acceptance

Software verification should include contract failures, causal timing, concurrent
worker/submission, task reuse, changed-account invalidation, fresh-price limits,
current-risk vetoes, transient failure/retry, duplicate prevention, OPEN/CLOSE/HOLD,
and audit consistency. The repository suite covers these using deterministic
fixtures. A deliberate live-data `execution_validation` roundtrip can additionally
check the environment, but remains separate from strategy-performance evidence.

After an upgrade that changes evidence rendering, do not resubmit tasks from the
previous runtime as new analysis. Allow old authority to expire and prepare/review
fresh evidence; preserve the account and audit rather than editing task hashes.
