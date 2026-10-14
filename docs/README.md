# Alladin documentation

These guides describe the implemented Python backend for external-agent research
and Coinbase SOL-USDC spot paper execution. They are not a development diary,
an unimplemented roadmap, or a profitability claim.

| Task | Read |
|---|---|
| Understand the product | [Product](product.md) |
| Start a service and paper account | [Getting started](getting-started.md) |
| Connect an external session | [API](api.md), [protocol](external-sessions.md), [consumer instructions](../.agents/CONSUMER.md) |
| Understand observations and timing | [Market data](feed.md) |
| Explain approved or rejected trades | [Risk and execution](risk-and-execution.md), [configuration](configuration.md) |
| Deploy, monitor, back up, or recover | [Operations](operations.md) |
| Change the implementation | [Architecture](architecture.md), [AGENTS.md](../AGENTS.md), [maintainer instructions](../.agents/MAINTAINER.md) |
| Evaluate outcomes | [Research](research.md) |
| Review prompt provenance | [Finance prompts](../finance_prompt_engineering/README.md), [adaptations](../finance_prompt_engineering/ADAPTATIONS.md), [references](upstream-research.md) |

## Contract sources

- `GET /v1/contract` and `python -m alladin contract`: endpoint/command inventory.
- `prepare_decision`: actual evidence, report schema, plan schema, and role instructions.
- MCP `tools/list`, `prompts/list`, and `prompts/get`: implemented discovery.
- `config.json` and `alladin/models.py`: repository profile and class defaults.

Use returned schemas, not prose, to construct executable payloads.
`external-session-v2`, task `binding_version=2`, prompt bundle `2.1.0`, and package
version `0.6.0` identify different compatibility surfaces.

## Evidence and language policy

Maintained product documentation, agent instructions, examples, and new public
runtime text are English. Original third-party material remains byte-for-byte
unchanged. Historical JSON verification artifacts in this directory are retained
evidence, not current specifications: their recorded messages and outcomes are not
rewritten or translated retroactively, and may describe earlier behavior.

Do not publish private session databases or operational reports as documentation.
Historical results do not prove present network availability or profitable alpha.
