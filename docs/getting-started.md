# Getting started

## Requirements

- Python 3.11+; no third-party runtime dependencies.
- Linux or compatible Unix for the worker's POSIX file lease.
- Permitted outbound HTTPS to `api.coinbase.com`; no exchange account key is needed.
- Persistent writable storage for SQLite and its sidecar files.
- An external task consumer when using `external` mode.

A source checkout runs from the repository root without installation. Optionally,
`python3 -m pip install .` installs the package and `alladin` console command; its
build system may obtain setuptools.

```bash
python3 -m alladin --help
python3 -m unittest discover -s tests -q
python3 -m alladin --config config.json doctor
```

`doctor` is read-only. Source/profile feasibility can fail; a successful check is
not an entry signal. See [operations](operations.md).

## Start HTTP and one worker

```bash
export LAB_API_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python3 -m alladin --config config.json --db data/paper.sqlite serve --paper-worker --poll-seconds 30
```

The token needs at least 32 characters. Retain it securely for the consuming client;
do not commit it or include it in a plan. A second terminal must use the **same**
token, not a freshly generated replacement. It authenticates the backend, not a
wallet, Coinbase account, or inference provider.

The server binds to loopback. Warmup is automatic. The repository's 900-second
timeframe remains 15 minutes even if polling occurs every 30 seconds.

```bash
curl -fsS http://127.0.0.1:8080/health
curl -fsS -H "Authorization: Bearer $LAB_API_TOKEN" http://127.0.0.1:8080/v1/status
curl -fsS -H "Authorization: Bearer $LAB_API_TOKEN" http://127.0.0.1:8080/v1/contract
```

`/health` checks the process. `/ready` requires an attached healthy worker and an
acceptable feed/session state. API-only `serve` may be healthy but not ready.
Neither endpoint certifies a trade opportunity.

## Operate the account

1. Inspect mode, account, active positions, halt state, and command contract.
2. Wait for warmup, or call `paper_tick` when the consumer owns polling.
3. Call `prepare_decision` with a new logical idempotency key.
4. Read the task's evidence, registry, schemas, missing domains, and role instructions.
5. Produce assessments and a plan externally; do not fabricate backend reports.
6. Submit the exact task ID/hash and inspect `outcome` and actual `events`.
7. Keep monitoring while exposed. At the end of a mandate, close with current data
   and verify state rather than assuming process shutdown closed the position.

See the [consumer guide](../.agents/CONSUMER.md) and
[protocol](external-sessions.md). A ready server with no consumer does not reason.

## Other entry points

| Need | Command |
|---|---|
| One observation/update | `python3 -m alladin --config config.json --db data/paper.sqlite paper-tick` |
| Worker without HTTP | `python3 -m alladin --config config.json --db data/paper.sqlite paper-live --poll-seconds 30` |
| API without worker | `python3 -m alladin --config config.json --db data/paper.sqlite serve` |
| MCP without worker | `python3 -m alladin --config config.json --db data/paper.sqlite mcp` |
| Stored state | `python3 -m alladin --config config.json --db data/paper.sqlite status` |
| Performance | `python3 -m alladin --config config.json --db data/paper.sqlite performance` |

Do not start two workers for one database. MCP can share an account with one
worker, but does not start it. This MCP server uses Content-Length framing;
verify the client's transport compatibility.

## Configuration and continuity

Pass the intended configuration and database explicitly. `config.json` defines
the repository profile; `Config()` class defaults differ. Persisted accounts
reject incompatible fingerprints and agent modes.

Use a separate configuration/database for a new research experiment. Do not edit
an existing balance, losses, mode, or fingerprint. `revise-policy` can revise only
`min_reward_risk` against the exact previous configuration; see
[configuration](configuration.md).

## Stop safely

Stopping a process stops polling, not necessarily exposure. Submit CLOSE, verify
the event or an already completed protective exit, inspect status, and verify the
audit. If fresh data is unavailable, report unresolved exposure instead of inventing
a settlement. `finalize` uses a stored research mark; it is not a fresh live-data exit.
Use the supervision and backup guidance in [operations](operations.md).
