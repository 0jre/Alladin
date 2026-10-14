# Instructions for maintainers

## Read before editing

Read root [AGENTS.md](../AGENTS.md), [architecture](../docs/architecture.md), and the
guide for the affected contract. Inspect current source and tests; do not infer
behavior from old verification JSON or comments describing earlier versions.

The runtime is Python standard library only. Do not introduce UI, embedded
inference, RPC, signers, exchange-order adapters, or new live products as an
incidental improvement. Keep source and maintained documentation in English.

## Code map

| Area | Files | Representative verification |
|---|---|---|
| Observations/time | `providers.py`, `transport.py`, `features.py` | Coinbase, deadline, causal feed tests |
| External coordination | `external.py`, `agents.py`, `finance.py`, `engine.py` | External session, coordination, pipeline tests |
| Risk/accounting | `risk.py`, `broker.py`, `models.py` | Sizing, hardening, execution tests |
| Persistence/concurrency | `storage.py`, `engine.py`, `runtime.py` | Idempotency, concurrent tick/submit, worker tests |
| Interfaces | `server.py`, `mcp_server.py`, `client.py` | HTTP/MCP/source-contract roundtrips |
| Research | `research.py`, `validation.py`, `evaluation.py` | Causality, statistics, controlled-check separation |
| Prompt library | `prompts.py`, `finance_prompts/` | Catalog integrity and schema/evidence tests |

## Change standards

- Preserve financial and temporal invariants, not just happy-path response shapes.
- Keep read-only source I/O outside write transactions. Recheck authority at commit.
- Preserve idempotent lookup, atomic response/event/state, and audit sealing.
- Do not broaden material task binding back to the entire mutable observation state.
- Do not solve a context race by pretending old evidence is new or skipping final risk.
- Do not weaken policy merely to make a test trade fill. Fixtures must be clearly
  synthetic; live operational checks must be explicitly identified.
- Do not rewrite upstream prompt bytes, historical event text, or sealed evidence.
  Active prompt changes require catalog hash/version updates and focused tests.
- Keep contracts, CLI help, examples, and documentation consistent. Human message
  translation must preserve machine codes, identifiers, schemas, and stored history.

## Verification and delivery

Run focused tests for a behavioral change, then the required suite:

```bash
python3 -m unittest discover -s tests -q
python3 -m compileall -q alladin
git diff --check
```

Validate documentation links, command names, JSON examples, and actual schemas.
Use isolated accounts and deterministic fixtures. Do not mutate a user's account
or perform networked paper trading to verify a prose-only edit. Package changes
need build/resource verification, especially prompts and catalog integrity.

Publish only intended source/docs/tests. Exclude private account state, credentials,
runtime reports, and temporary artifacts. Describe actual checks and limitations;
do not label local tests as remote CI or operational checks as strategy returns.
