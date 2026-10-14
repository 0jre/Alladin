"""Coinbase-only public market data.

Paper mode never builds, signs, or submits a wallet transaction.
"""
import math
import time
from urllib.parse import quote, urlencode

from .models import Candle, Snapshot, SOL, pubkey, utc_timestamp
from .transport import HTTP, DataError,HTTP_TOTAL_SECONDS


class CoinbaseMarket:
    """Coinbase Advanced Trade public spot data, restricted to Solana's native SOL mint."""
    BASE = "https://api.coinbase.com/api/v3/brokerage/market"
    PRODUCT_IDS = {"SOL-USDC"}
    GRANULARITIES = {60: "ONE_MINUTE", 300: "FIVE_MINUTE", 900: "FIFTEEN_MINUTE",
                     3600: "ONE_HOUR"}

    def __init__(self, http=None, product_id=None):
        self.http = http or HTTP(timeout=HTTP_TOTAL_SECONDS, retries=2)
        self.product_id = product_id or "SOL-USDC"
        self._volume_cache = None
        self._candles_cache = None
        if self.product_id not in self.PRODUCT_IDS:
            raise ValueError("Only Coinbase SOL-USDC is permitted")

    def _get(self, path, params=None):
        url = f"{self.BASE}/{path}"
        if params:
            url += "?" + urlencode(params)
        try:
            return self.http.json(url, headers={"Cache-Control": "no-cache"})
        except DataError as exc:
            kind='candles' if path.endswith('/candles') else 'ticker' if path.endswith('/ticker') else 'book' if path=='product_book' else 'statistics'
            raise exc.at_source('coinbase_'+kind) from None

    def candles(self, mint=SOL, count=120, aggregate=900, now=None):
        if pubkey(mint) != SOL:
            raise DataError("Coinbase feed supports only the native SOL mint")
        if type(count) is not int or not 1 <= count <= 348:
            raise ValueError("count must be between 1 and 348")
        if aggregate not in self.GRANULARITIES:
            raise ValueError("aggregate must be 1, 5, 15 or 60 minutes")
        step = aggregate
        cutoff = int(time.time() if now is None else now)
        end = cutoff // step * step
        cache_key=(mint,count,aggregate,end)
        if self._candles_cache is not None and self._candles_cache[0]==cache_key:
            return list(self._candles_cache[1])
        start = end - (count + 2) * step
        data = self._get(f"products/{quote(self.product_id, safe='')}/candles", {
            "start": start, "end": end, "granularity": self.GRANULARITIES[aggregate],
            "limit": count + 2,
        })
        raw = data.get("candles") if isinstance(data, dict) else None
        if not isinstance(raw, list):
            raise DataError("Invalid Coinbase candles response")
        rows = []
        try:
            for item in raw:
                ts = int(item["start"])
                if ts % step:
                    raise ValueError('Misaligned candle')
                if ts + step > cutoff:
                    continue
                close = float(item["close"])
                base_volume = float(item["volume"])
                rows.append(Candle(ts, float(item["open"]), float(item["high"]),
                                   float(item["low"]), close, base_volume * close, mint=SOL))
        except (KeyError, TypeError, ValueError, OverflowError, IndexError):
            raise DataError("Invalid Coinbase candle record") from None
        rows.sort(key=lambda candle: candle.timestamp)
        if len(rows) > count:
            rows = rows[-count:]
        if not rows:
            raise DataError("Coinbase has not returned closed candles yet")
        if any(b.timestamp != a.timestamp + step for a, b in zip(rows, rows[1:])):
            raise DataError("Coinbase candles contain gaps; replay rejected")
        if rows[-1].timestamp+step==end:
            self._candles_cache=(cache_key,tuple(rows))
        return rows

    def market(self, mint=SOL, candles=None, timeframe_seconds=900):
        if pubkey(mint) != SOL:
            raise DataError("Coinbase market data supports only the native SOL mint")
        # Slow statistics first. The executable paper reference is fetched last.
        volume_quote = self._volume(candles,timeframe_seconds)
        trade_data = self._get(f"products/{quote(self.product_id, safe='')}/ticker", {"limit": 100})
        mark = self.quote(mint)

        trades = trade_data.get("trades") if isinstance(trade_data, dict) else None
        if not isinstance(trades, list) or not trades:
            raise DataError("Coinbase trades are missing or invalid")
        buy_notional = sell_notional = 0.0
        try:
            for trade in trades:
                notional = float(trade["price"]) * float(trade["size"])
                if not math.isfinite(notional) or notional <= 0:
                    raise ValueError('Trade is nonfinite or nonpositive')
                # Coinbase reports maker side. Reverse it to estimate taker aggression.
                if trade["side"] == "SELL":
                    buy_notional += notional
                elif trade["side"] == "BUY":
                    sell_notional += notional
                else:
                    raise ValueError
        except (KeyError, TypeError, ValueError, OverflowError):
            raise DataError("Invalid Coinbase trade") from None
        imbalance = ((buy_notional - sell_notional) / (buy_notional + sell_notional)
                     if buy_notional + sell_notional else 0.0)
        if not all(math.isfinite(v) for v in (buy_notional,sell_notional)):
            raise DataError('Nonfinite Coinbase statistics')
        return {**mark,'volume_24h_usd':volume_quote,'buy_sell_imbalance':imbalance,'scope':'full'}

    def quote(self,mint=SOL):
        """Current book-only mark for exits; missing flow/volume cannot authorize entry."""
        if pubkey(mint)!=SOL:
            raise DataError('Coinbase quote supports only SOL-USDC')
        book = self._get("product_book", {"product_id": self.product_id, "limit": 50})
        try:
            pricebook = book["pricebook"]
            if pricebook['product_id'] != self.product_id:
                raise ValueError('Wrong product')
            observed_at = utc_timestamp(pricebook['time'])
            if not -5 <= time.time()-observed_at <= 30:
                raise ValueError('Book is stale or future-dated')
            bids, asks = pricebook["bids"], pricebook["asks"]
            best_bid, best_ask = float(bids[0]["price"]), float(asks[0]["price"])
        except (KeyError, TypeError, ValueError, IndexError):
            raise DataError("Coinbase book is invalid or empty") from None
        if not all(math.isfinite(v) for v in (best_bid,best_ask)) or min(best_bid, best_ask) <= 0 or best_bid > best_ask:
            raise DataError("Invalid Coinbase best bid or ask")
        mid = (best_bid + best_ask) / 2
        bid_depth = self._depth(bids, mid, lower=True)
        ask_depth = self._depth(asks, mid, lower=False)
        if min(bid_depth, ask_depth) <= 0:
            raise DataError("Insufficient Coinbase depth")

        if not all(math.isfinite(v) for v in (bid_depth,ask_depth)):
            raise DataError('Nonfinite Coinbase statistics')
        return dict(mint=mint,product_id=self.product_id,price=mid,bid=best_bid,ask=best_ask,
                    liquidity_usd=bid_depth+ask_depth,volume_24h_usd=0,buy_sell_imbalance=0,
                    observed_at=observed_at,source='coinbase_advanced_sol_spot',scope='mark_only')

    def _volume(self,candles,timeframe_seconds):
        """Estimate quote volume over a full 24h of completed candles only."""
        end = int(time.time())//timeframe_seconds*timeframe_seconds
        start = end-86400
        bars = [b for b in (candles or []) if start <= b.timestamp and b.timestamp+timeframe_seconds <= end]
        if len(bars) == 86400//timeframe_seconds:
            return sum(b.volume for b in bars)
        end = int(time.time())//3600*3600
        if self._volume_cache and self._volume_cache[0] == end:
            return self._volume_cache[1]
        bars = self.candles(SOL,count=26,aggregate=3600)
        bars = [b for b in bars if end-86400 <= b.timestamp and b.timestamp+3600 <= end]
        if len(bars) != 24:
            raise DataError('Insufficient Coinbase candles for a complete 24-hour volume estimate')
        volume = sum(b.volume for b in bars)
        self._volume_cache = (end,volume)
        return volume

    @staticmethod
    def _depth(levels, mid, lower):
        depth = 0.0
        for level in levels:
            try:
                price, size = float(level["price"]), float(level["size"])
            except (KeyError, TypeError, ValueError, OverflowError):
                raise DataError("Invalid Coinbase book level") from None
            if not math.isfinite(price) or not math.isfinite(size) or price <= 0 or size < 0:
                raise DataError("Invalid Coinbase book level")
            if (price >= mid * .99) if lower else (price <= mid * 1.01):
                depth += price * size
        return depth


def collect(mint=SOL, market=None):
    """Coinbase-only observation. Never assert on-chain verification."""
    if pubkey(mint)!=SOL:
        raise DataError('Coinbase feed supports only SOL-USDC')
    if callable(market):
        market=market()
    if not isinstance(market,dict) or not market:
        raise DataError('Current Coinbase data is required')
    if market.get('product_id')!='SOL-USDC' or market.get('source')!='coinbase_advanced_sol_spot':
        raise DataError('Invalid Coinbase product or source')
    observed_at=market.get('observed_at')
    if type(observed_at) is not int or not -5<=time.time()-observed_at<=30:
        raise DataError('Coinbase quote expired; cycle blocked')
    return Snapshot(timestamp=observed_at,mint=mint,price=market['price'],
                    product_id=market['product_id'],source=market['source'],
                    liquidity_usd=market['liquidity_usd'],volume_24h_usd=market['volume_24h_usd'],
                    buy_sell_imbalance=market['buy_sell_imbalance'],
                    warnings=('Coinbase data only; no on-chain verification was performed.',
                              'Paper fills use midpoint plus modeled costs; no order is submitted.')+
                              (('Book-only quote; 24-hour volume and trade flow were not collected for this observation.',)
                               if market.get('scope')=='mark_only' else ()))
