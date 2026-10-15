# Nautilus execution core

Alladin pins NautilusTrader **1.231.0**, upstream commit
`27a8e54e7ac3c57d6cbf8891f0283dfbaee97317`. The complete source is materialized locally from a committed lock and bootstrap
script, preserving its LGPL-3.0 license, copyright notices and integrity manifest.
Run `python scripts/vendor_nautilus.py` after cloning Alladin to reproduce it.
The materialized copy contains no nested `.git`. Original upstream files are not
modified. Runtime uses the matching compiled release through `alladin[engine]`.

## Authority and process boundary

External agent sessions reason and supervise. Alladin owns the shared durable
capital ledger, product eligibility, proposal lifecycle, aggregate risk, evidence
and idempotency. Nautilus v2 supplies the native risk/execution engine, cash
account checks, order lifecycle, L2 matching and fill events.

For each approved paper action, a separate native process is seeded from the
current account cash and inventory snapshot, receives the observed Coinbase L2
book and executes the exact approved IOC intent. Its fills, prices and commission
are validated before ledger mutation. A native crash, rejection, timeout, version
mismatch or fill divergence cannot fall back silently to another executor.

The native process never performs model inference, contacts an exchange, reads
trading credentials or places real orders. Native matching is an isolated paper
transaction, not a persistent live Nautilus node. Alladin remains the durable
source of truth across transactions; the native cache is reconstructed from it.
The native risk engine is not bypassed. Account mutation and stored response are
atomic; interrupted paper computations have no external order to reconcile.

The `reference` execution setting is an explicit deterministic test/reference
backend. The shipped portfolio profile selects `nautilus`. Every order records
its actual engine and version, and native orders retain native fill identifiers.

## Install and run locally

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install '.[engine]'
export LAB_API_TOKEN='<backend-token-at-least-32-characters>'
docker compose up --build -d
```

The Compose file uses host networking because the HTTP server binds loopback;
this profile targets Linux and Docker Desktop installations with host networking
enabled. A remote endpoint still needs an operator-managed authenticated TLS
proxy. The named volume preserves account state; do not delete it to erase losses.
Docker is not available in the development workspace, so a local Compose startup
must be verified on the target Docker installation. Python/native integration
tests are independent of that deployment check.

## Hybrid strategies and external supervision

The current external-session protocol exposes market features, advisory scanning,
theses and deterministic propose/commit controls. A consuming session or its
quantitative workers can implement trend, reversion or breakout strategies under
the same risk authority. The backend does not create six independent agents,
run LLM APIs, train XGBoost/LightGBM models, or claim statistical model accuracy.
Versioned quantitative workers and persistent live-node streaming are further
integration work; importing Nautilus does not create those services.

Coinbase's pinned upstream adapter is Rust/v2. Legacy Python `TradingNode`
examples must not be mistaken for a supported Coinbase integration. This release
uses public Coinbase REST observations and native local matching. Live Coinbase
adapter wiring, native exchange protection and private reconciliation remain
disabled. No real-money readiness or profitable strategies are claimed.
