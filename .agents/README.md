# Alladin agent entry point

Start with the [multi-token portfolio protocol](../docs/portfolio.md). Legacy task envelopes remain supported only for explicit legacy accounts.

This directory teaches an external agent how to **use** Alladin and a coding agent
how to **maintain** it. It is documentation, not an installed skill, model plugin,
automatic worker, or permission to trade outside the user's mandate.

1. Read the root [AGENTS.md](../AGENTS.md) for repository invariants.
2. Read [CONSUMER.md](CONSUMER.md) before operating a paper account.
3. Read [MAINTAINER.md](MAINTAINER.md) before changing code.
4. Follow the [session workflow](workflows/paper-session.md) when coordinating a run.
5. Use [examples](examples/README.md) as interface examples, never as market signals.

The full product reference starts at [docs/README.md](../docs/README.md).
Discover actual contracts through `/v1/contract`, MCP `tools/list`, and the returned
task schemas. The backend contains no inference engine: the consuming session owns
the reasoning and can coordinate subagents only when that session supports and
authorizes them. Do not claim a subagent ran merely because a role name exists.
