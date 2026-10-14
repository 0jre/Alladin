# Coinbase product universe

## Product mandate and current implementation

Alladin's product mandate is the Coinbase instrument universe, across tokens and
product types. SOL-USDC is a legacy executor constraint, not the product mandate.
This change implements broad discovery and product-specific public books. It does
**not** implement broad execution. Never describe the current backend as trading
all Coinbase products: that migration is incomplete.

| Layer | Implemented behavior |
|---|---|
| Catalog | `get_all_products=true`, cursor pagination, offset compatibility, bounded complete refresh, cache and content hash |
| Identity | Canonical Coinbase `product_id`; no Solana mint requirement |
| Product types | Preserve every returned type, including unknown future types, disabled and expired instruments |
| Metadata | Preserve increments, limits, currencies, venue, session, futures, equity and other returned details |
| Order book | Request by product ID, validate identity and levels, preserve source timestamp; research only |
| Size helper | Decimal arithmetic; round down to actual lot multiples; enforce base limits |
| Execution | Existing SOL-USDC spot paper executor only; other adapters explicitly unavailable |
| Eligibility | Unknown: public listing does not establish regional/account permission |

## Commands

Use the authenticated `POST /v1/commands` route or the matching MCP tools:

```json
{"command":"catalog","args":{}}
```

```json
{"command":"instrument","args":{"product_id":"BTC-USD"}}
```

```json
{"command":"instrument_book","args":{"product_id":"ETH-EUR"}}
```

These commands are read-only and do not consume or modify an account's cash,
positions, risk history, tasks or configuration fingerprint. A fresh catalog is
cached for 60 seconds. `{"refresh":true}` requests a complete refresh. Failures
raise an error; incomplete refreshes never replace the complete cache. Read-only
requests are not persisted as idempotent ledger mutations, so repeating one can
return newer observations.

Each catalog record includes `alladin_capabilities`, separating discovery,
market-data availability, actual paper execution support and account eligibility.
Do not strip disabled instruments or silently classify unknown types as spot.
Catalog snapshots are observations, not a transactionally frozen exchange-wide
view; pagination can overlap as the upstream listing changes.

## Execution migration requirements

Multi-product execution must use a single shared cash/risk authority rather than
duplicating the same balance in a ledger per symbol. It must preserve existing
accounts and audit chains through an explicit migration. A canonical instrument
model must replace mint-based execution identity throughout proposals, evidence,
task bindings, marks, positions and aggregate exposure.

Spot requires separate currency balances, actual bid/ask liquidity, increments,
fees and explicit FX conversion. USD, USDC, EUR and BTC must not be treated as the
same unit. Futures require contract multipliers, collateral, long/short margin,
maintenance, funding when applicable, expiry and settlement. Options require
contract rights, premium units, expiry, exercise/settlement and appropriate risk;
a product group is not an executable contract. Equities require canonical IDs,
session calendars, fractional permissions, side restrictions and corporate action
handling. Venue-specific gateways must be implemented where applicable.

Until those paths and their tests exist, discovery must return an explicit
`execution_adapter_not_implemented` block. Generic book responses always return
`execution_authorized=false`; receiving a book cannot bypass execution checks.

## Primary reference

[Coinbase List Public Products](https://docs.cdp.coinbase.com/api-reference/advanced-trade-api/rest-api/public/list-public-products)
documents that omitting the type filter returns spot only, while
`get_all_products=true` includes all product types and expired futures. Available
products and access can differ by venue, account and region. The public catalog
does not establish entitlement or coverage of services outside that API.
