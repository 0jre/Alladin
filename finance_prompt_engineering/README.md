# Finance prompt engineering for Alladin

## Provenance and execution boundary

`upstream/` preserves the imported
[awesome-claude-finance-prompts](https://github.com/devfinprojects/awesome-claude-finance-prompts)
snapshot. Its nested `.git` was removed after recording commit/tree/file hashes in
[UPSTREAM.json](UPSTREAM.json). Original bytes remain unchanged. The recorded
snapshot contained no license declaration; preservation does not imply a license grant.

The backend never loads upstream chapter text directly as runtime instruction.
The reviewed Alladin-specific library is `alladin/finance_prompts`, packaged with
the Python service and checked by `prompts.py` for allowed paths, size, version,
and exact catalog hashes. Current bundle: **2.2.0**. The
[adaptation map](ADAPTATIONS.md) describes the conceptual scope.

## Active roles

| Role | Purpose |
|---|---|
| `market` | Closed-bar regime, directional support, counterevidence, and invalidation |
| `quality` | Coinbase identity, timestamps, continuity, completeness, and missing data |
| `flow` | Centralized depth/trades, cost drag, concentration, and execution limits |
| `challenger` | Pre-mortem, contradictions, unsupported assumptions, and stressed economics |
| `manager` | Structured plan with evidence, protection, horizon, and final-risk submission |

The consuming session coordinates the perspectives; the backend does not launch
agents or authenticate independence. It validates references, contracts, vetoes,
agreement, and deterministic risk. Candidates are advisory: lack of an internal
candidate does not prohibit a supported external hypothesis.

## Evidence rather than invented knowledge

`finance.py` builds closed features, snapshot, portfolio, configuration, candidate
economics, 2× cost stress, memory, and missing domains into a hashed envelope.
Every available reference has a source and availability time. Missing macro news,
on-chain facts, DEX liquidity, MEV, and calibrated probability remain missing.

Prompts organize provided evidence; they do not train a model, create observations,
or establish profitable edge. Conclusions are concise and evidence-based, with
invalidation and uncertainty; no private chain-of-thought is requested.

## Interfaces and governance

HTTP `/v1/prompts`, `/v1/prompts/{role}`, task instructions, MCP `prompts/list`, and
`prompts/get` expose only the allowlisted reviewed roles. These interfaces do not
read arbitrary files. Updates require deliberate prompt/catalog version and hash
review, tests, and a controlled deployment.

The [external-session protocol](../docs/external-sessions.md) governs reports and
plans. The [research guide](../docs/research.md) explains observed statistics and
why operational checks or a high hit rate cannot prove future returns. No embedded
model, inference endpoint, API key, or on-chain verification is configured here.
