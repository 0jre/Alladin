# Product specification

## Purpose and supported scope

The product mandate covers the Coinbase product universe. Public catalog and
instrument-book discovery are now generic; execution remains the legacy SOL-USDC
spot path. See [actual capabilities and migration requirements](coinbase-universe.md).
The table below describes that legacy execution path, not the overall mandate.

Alladin makes observation, portfolio control, and paper accounting available to an
external AI session through bounded commands. The session can inspect a durable
account across interactions, coordinate analyses, submit a plan, and verify the
backend's actual execution events.

| Dimension | Implemented scope |
|---|---|
| Live instrument | Coinbase `SOL-USDC` spot |
| Asset identity | Native SOL mint `So11111111111111111111111111111111111111112`; `chain=solana` |
| Live source | Coinbase Advanced Trade public market endpoints |
| Execution | Local spot paper ledger |
| Actions | LONG, HOLD, CLOSE |
| Interfaces | Authenticated HTTP, MCP over stdio, CLI |
| Runtime | Python 3.11+, standard library |
| State | One persistent SQLite account per database |
| Background processing | One supervised paper worker per database |
| Research baseline | Explicit deterministic `rules` mode |

Legacy models retain additional mint/instrument fields for historical research.
They do not enable other live products, perpetuals, wallet execution, or blockchain
collection. Alladin does not host a reasoning model, launch AI subagents, or turn
a prompt collection into a trained trading policy.

## Responsibility boundary

| External session | Backend |
|---|---|
| Establish the user's mandate and permitted account | Enforce execution mode and persisted account compatibility |
| Read evidence, instructions, schemas, and missing domains | Collect observations and build the evidence registry |
| Coordinate market, quality, flow, challenge, and manager work | Validate contracts, references, vetoes, and directional agreement |
| Decide whether observations support a thesis | Recheck current account risk, economics, exposure, and sizing |
| Submit the exact plan with an idempotency key | Apply at most one authorized mutation and persist its response |
| Report actual events and uncertainty | Expose status, performance, and audit verification |
| Keep polling active while exposed | Apply observed protective exits and circuit breakers |

The session cannot choose quantity, notional, leverage, or a different venue in a
manager plan. The backend cannot authenticate independence between report authors,
establish predictive edge, or prove that a simulated midpoint was executable.

## Account and decision lifecycle

A new database initializes an account from configuration. Warmup loads closed
history without trading. A decision task freezes the evidence reviewed by the
session. A valid submission can open a spot position, close one, or preserve cash.

Observations continue independently during reasoning. Task reuse does not renew
its deadline. Material account changes invalidate prior authority; a new candle
alone does not. Execution uses current observations and risk, never a retrospective
fill against the frozen quote.

Cash, fees, losses, and closed trades survive restarts. A new database is a different
account, not a way to erase the existing account's losses. A configuration/mode
fingerprint prevents silently changing the mandate of persisted state.

## Meaning of autonomy

An authorized external session can run a perceive–reason–submit–verify loop without
requiring approval for every paper action within its mandate. Alladin remains a
bounded backend. `serve --paper-worker` and `demo-live` do not supply an intelligent
consumer, and running a service does not keep a chat assistant continuously active.

`rules` mode is a reference strategy, not a silent fallback for external reasoning.
Mode cannot be changed on an existing account without violating compatibility.

## Evidence and economic limits

The source covers centralized-market prices, depth, trades, and completed candles.
It does not cover macro news, on-chain holders, token authorities, DEX routes, MEV,
or calibrated win probabilities. Missing data stays missing. Indicators derived
from the same price history are correlated evidence.

Acceptance means specified controls passed, not positive expected return. Paper
costs are configured assumptions, not actual fees, queue position, partial fills,
or market impact. Protection depends on active polling and fresh data; a gap can
produce a loss beyond the configured stop.

## Outputs

Outputs include account state, versioned prompts and schemas, frozen tasks,
execution events with provenance, explicit outcomes, an event hash chain, and
observed statistics. Research exports also provide JSON, JSONL, and CSV files.
They support inspection and reproducibility, not independent attestation of data
authenticity or future returns.
