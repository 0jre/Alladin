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
            raise ValueError("Somente o produto Coinbase SOL-USDC é permitido")

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
            raise DataError("Coinbase feed habilitado somente para o mint nativo SOL")
        if type(count) is not int or not 1 <= count <= 348:
            raise ValueError("count precisa estar entre 1 e 348")
        if aggregate not in self.GRANULARITIES:
            raise ValueError("aggregate precisa ser 1, 5, 15 ou 60 minutos")
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
            raise DataError("Resposta Coinbase candles inválida")
        rows = []
        try:
            for item in raw:
                ts = int(item["start"])
                if ts % step:
                    raise ValueError('Candle desalinhado')
                if ts + step > cutoff:
                    continue
                close = float(item["close"])
                base_volume = float(item["volume"])
                rows.append(Candle(ts, float(item["open"]), float(item["high"]),
                                   float(item["low"]), close, base_volume * close, mint=SOL))
        except (KeyError, TypeError, ValueError, OverflowError, IndexError):
            raise DataError("Registro Coinbase candle inválido") from None
        rows.sort(key=lambda candle: candle.timestamp)
        if len(rows) > count:
            rows = rows[-count:]
        if not rows:
            raise DataError("Coinbase ainda não retornou candles fechados")
        if any(b.timestamp != a.timestamp + step for a, b in zip(rows, rows[1:])):
            raise DataError("Coinbase candles contêm lacunas; replay recusado")
        if rows[-1].timestamp+step==end:
            self._candles_cache=(cache_key,tuple(rows))
        return rows

    def market(self, mint=SOL, candles=None, timeframe_seconds=900):
        if pubkey(mint) != SOL:
            raise DataError("Coinbase market data habilitado somente para o mint nativo SOL")
        # Slow statistics first. The executable paper reference is fetched last.
        volume_quote = self._volume(candles,timeframe_seconds)
        trade_data = self._get(f"products/{quote(self.product_id, safe='')}/ticker", {"limit": 100})
        mark = self.quote(mint)

        trades = trade_data.get("trades") if isinstance(trade_data, dict) else None
        if not isinstance(trades, list) or not trades:
            raise DataError("Trades Coinbase ausentes ou inválidos")
        buy_notional = sell_notional = 0.0
        try:
            for trade in trades:
                notional = float(trade["price"]) * float(trade["size"])
                if not math.isfinite(notional) or notional <= 0:
                    raise ValueError('Trade não finito ou não positivo')
                # Coinbase reports maker side. Reverse it to estimate taker aggression.
                if trade["side"] == "SELL":
                    buy_notional += notional
                elif trade["side"] == "BUY":
                    sell_notional += notional
                else:
                    raise ValueError
        except (KeyError, TypeError, ValueError, OverflowError):
            raise DataError("Trade Coinbase inválido") from None
        imbalance = ((buy_notional - sell_notional) / (buy_notional + sell_notional)
                     if buy_notional + sell_notional else 0.0)
        if not all(math.isfinite(v) for v in (buy_notional,sell_notional)):
            raise DataError('Estatísticas Coinbase não finitas')
        return {**mark,'volume_24h_usd':volume_quote,'buy_sell_imbalance':imbalance,'scope':'full'}

    def quote(self,mint=SOL):
        """Current book-only mark for exits; missing flow/volume cannot authorize entry."""
        if pubkey(mint)!=SOL:
            raise DataError('Coinbase quote aceita somente SOL-USDC')
        book = self._get("product_book", {"product_id": self.product_id, "limit": 50})
        try:
            pricebook = book["pricebook"]
            if pricebook['product_id'] != self.product_id:
                raise ValueError('Produto errado')
            observed_at = utc_timestamp(pricebook['time'])
            if not -5 <= time.time()-observed_at <= 30:
                raise ValueError('Livro stale ou futuro')
            bids, asks = pricebook["bids"], pricebook["asks"]
            best_bid, best_ask = float(bids[0]["price"]), float(asks[0]["price"])
        except (KeyError, TypeError, ValueError, IndexError):
            raise DataError("Livro Coinbase inválido ou vazio") from None
        if not all(math.isfinite(v) for v in (best_bid,best_ask)) or min(best_bid, best_ask) <= 0 or best_bid > best_ask:
            raise DataError("Melhor bid/ask Coinbase inválido")
        mid = (best_bid + best_ask) / 2
        bid_depth = self._depth(bids, mid, lower=True)
        ask_depth = self._depth(asks, mid, lower=False)
        if min(bid_depth, ask_depth) <= 0:
            raise DataError("Profundidade Coinbase insuficiente")

        if not all(math.isfinite(v) for v in (bid_depth,ask_depth)):
            raise DataError('Estatísticas Coinbase não finitas')
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
            raise DataError('Candles Coinbase insuficientes para medir 24 horas completas')
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
                raise DataError("Nível do livro Coinbase inválido") from None
            if not math.isfinite(price) or not math.isfinite(size) or price <= 0 or size < 0:
                raise DataError("Nível do livro Coinbase inválido")
            if (price >= mid * .99) if lower else (price <= mid * 1.01):
                depth += price * size
        return depth


def collect(mint=SOL, market=None):
    """Coinbase-only observation. Never assert on-chain verification."""
    if pubkey(mint)!=SOL:
        raise DataError('Coinbase feed aceita somente SOL-USDC')
    if callable(market):
        market=market()
    if not isinstance(market,dict) or not market:
        raise DataError('Dados atuais da Coinbase são obrigatórios')
    if market.get('product_id')!='SOL-USDC' or market.get('source')!='coinbase_advanced_sol_spot':
        raise DataError('Produto/origem Coinbase inválidos')
    observed_at=market.get('observed_at')
    if type(observed_at) is not int or not -5<=time.time()-observed_at<=30:
        raise DataError('Cotação Coinbase expirada; ciclo bloqueado')
    return Snapshot(timestamp=observed_at,mint=mint,price=market['price'],
                    product_id=market['product_id'],source=market['source'],
                    liquidity_usd=market['liquidity_usd'],volume_24h_usd=market['volume_24h_usd'],
                    buy_sell_imbalance=market['buy_sell_imbalance'],
                    warnings=('Dados exclusivos da Coinbase; nenhuma verificação on-chain foi realizada.',
                              'Fills paper usam midpoint mais custos; nenhuma ordem é enviada.')+
                              (('Cotação somente livro; volume 24h e fluxo não coletados nesta observação.',)
                               if market.get('scope')=='mark_only' else ()))
