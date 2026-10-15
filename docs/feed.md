# Market data and temporal contract

> Default backend: [multi-token portfolio](portfolio.md). The detailed legacy
> procedures below apply to explicit legacy accounts unless stated otherwise.

## Live source

The only implemented live source is Coinbase Advanced Trade public market data
for `SOL-USDC` under `https://api.coinbase.com/api/v3/brokerage/market`:

| Path | Use |
|---|---|
| `products/SOL-USDC/candles` | Closed OHLCV; one-, five-, fifteen-minute bars; hourly bars for volume coverage |
| `products/SOL-USDC/ticker?limit=100` | Recent trades and approximate taker imbalance |
| `product_book?product_id=SOL-USDC&limit=50` | Current midpoint, timestamp, and visible depth |

The provider sends `Cache-Control: no-cache` but cannot guarantee upstream caching
behavior or availability. It preserves the book's observation timestamp rather
than stamping a delayed response with the local current time.

The `solana` label and native mint identify SOL. No RPC, wallet, indexer, token
authority lookup, holder analysis, or DEX routing is implemented.

## Units and interpretation

- Candle `timestamp` is UTC Unix seconds at bar opening. A bar is usable only
  after `timestamp + timeframe_seconds`.
- Provider OHLC prices are USDC per SOL. Base volume is converted to approximate
  quote volume by multiplying it by candle close.
- Snapshot `timestamp` is the original book time. Snapshot `price` is the midpoint
  `(best_bid + best_ask) / 2`, not an executable order quote.
- `liquidity_usd` sums visible notional within approximately 1% of midpoint, subject
  to the returned book's depth limit. It is centralized-book depth, not DEX liquidity.
- `volume_24h_usd` estimates quote volume over a full set of completed 24-hour
  candles, commonly from 24 hourly bars; it is not an independently exact USD metric.
- `buy_sell_imbalance` is normalized notional aggression in [-1, 1]. The adapter
  interprets reported side as maker side and reverses it to estimate taker side. A recent batch is noisy,
  not persistent alpha or evidence of organic on-chain activity.

A book-only exit mark does not collect trades or volume. It uses zero sentinels
for those fields with an explicit warning; they are **unavailable**, not observed
zero activity. It fails entry volume requirements and is not reused as a complete
entry context.

## Validation and caches

The provider rejects wrong products/mints, malformed/nonfinite values, crossed or
empty books, invalid trade records, misaligned candles, and noncontiguous history.
Open candles are excluded. The live path accepts only 60-, 300-, or 900-second
timeframes and requires at least 80 bars for feature readiness.

Closed-candle responses are cached only for their matching interval and only when
the most recent expected closed candle is present. The volume estimate is cached
within its completed hourly period. Neither cache refreshes observation timestamps.

Execution quotes must be no more than 30 seconds old; the implemented tolerance
for book clock skew is at most five seconds into the future. Current entry risk
also requires sufficiently recent closed features. Collection crossing a candle
boundary refreshes risk candles and, when necessary, the quote.

## Causal feature set

`features.py` returns readiness/count or a descriptive feature vector. It uses
closed prices only; no feature is a calibrated forecast.

| Family | Fields and computation |
|---|---|
| Trend | 12/36 EMAs over recent history, normalized gap/slope, 12-bar momentum |
| Slower context | 5/15 EMAs over completed nonoverlapping groups of four bars; not a separate news or macro feed |
| Volatility | Mean 14-bar true range and ATR fraction; standard deviation of up to 64 log returns |
| Directionality | 20-bar path efficiency and Wilder-style ADX |
| Oscillation | 14-change RSI, 20-price z-score, Bollinger width |
| MACD | 12/26 EMA difference, 9-period signal, normalized histogram |
| Volume | Latest quote volume relative to the previous 20 bars |
| Reference levels | Previous 20-bar high/low, approximate 20-bar volume-weighted typical price |
| Tail risk | Empirical 95% loss quantile and upper-tail mean over recent bar returns |

Regime is `shock` if ATR/price exceeds 5% or the latest absolute log return exceeds
4%; otherwise `trend` if efficiency exceeds 0.30, and `range` otherwise. These are
heuristics. Historical tail estimates are small-sample measures, not future-loss bounds.

## Warmup, gaps, and execution time

Warmup does not trade. The worker processes forward observations and prevents
duplicate bars. A flat account can rewarm after missing history without retroactive
fills. With exposure or pending activity, a feed gap requires a current verified
mark, closes there, and latches a halt. An older candle that includes pre-entry
prices cannot retrospectively stop a newly opened position.

External analysis and execution have distinct times. A valid task can survive a
new bar, but execution uses current risk observations; see the
[task protocol](external-sessions.md).

## Controlled replay

`ingest` and JSONL replay are separate from live collection. One JSONL line contains
exactly `candle` and `snapshot`. The candle is closed; a replay snapshot must be
available no later than that candle's close. Subsequent bars must be contiguous
for their mint. An approved decision is eligible at the next bar's opening after
revalidation; replay cannot be mixed with `paper_tick` on one database.

Example fixture shape, **not live evidence**:

```json
{
  "candle": {
    "timestamp": 1767225600, "open": 150, "high": 152, "low": 149,
    "close": 151, "volume": 100000, "chain": "solana",
    "mint": "So11111111111111111111111111111111111111112"
  },
  "snapshot": {
    "timestamp": 1767226500, "price": 151,
    "liquidity_usd": 10000000, "volume_24h_usd": 50000000,
    "product_id": "SOL-USDC", "source": "coinbase_advanced_sol_spot",
    "warnings": ["Illustrative fixture only; not a real market observation."]
  }
}
```

Labels in a fixture do not attest authenticity. Legacy snapshot fields support old
research records, not new on-chain verification claims. Synthetic replay tests
causality/accounting, not market profitability.
