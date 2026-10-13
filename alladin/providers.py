"""Read-only Coinbase market data plus read-only Solana account checks.

Paper mode never builds, signs, or submits a wallet transaction.
"""
import os
import time
from urllib.parse import quote, urlencode

from .models import Candle, Snapshot, SOL, TOKEN_PROGRAM, MAINNET_GENESIS, pubkey
from .transport import HTTP, DataError


class SolanaRPC:
    ALLOWED = {"getGenesisHash", "getAccountInfo", "getTokenSupply", "getTokenLargestAccounts"}

    def __init__(self, http=None, url=None):
        self.http = http or HTTP(timeout=8, retries=0)
        self.url = url or os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

    def call(self, method, params=None):
        if method not in self.ALLOWED:
            raise DataError("Método RPC não permitido")
        data = self.http.json(self.url, {"jsonrpc": "2.0", "id": 1, "method": method,
                                        "params": params or []})
        if not isinstance(data, dict) or data.get("error") or "result" not in data:
            raise DataError(f"RPC {method} falhou; detalhes omitidos")
        return data["result"]

    def inspect(self, mint=SOL):
        pubkey(mint)
        if self.call("getGenesisHash") != MAINNET_GENESIS:
            raise DataError("RPC não pertence à Solana mainnet")
        account = self.call("getAccountInfo", [mint, {"encoding": "jsonParsed", "commitment": "finalized"}])
        value = account.get("value")
        if not isinstance(value, dict) or value.get("owner") != TOKEN_PROGRAM:
            raise DataError("Somente mint SPL clássico é suportado; Token-2022 recusado")
        parsed = value.get("data", {}).get("parsed", {})
        info = parsed.get("info", {})
        if parsed.get("type") != "mint" or info.get("isInitialized") is not True:
            raise DataError("Conta não é um mint inicializado")
        if "mintAuthority" not in info or "freezeAuthority" not in info:
            raise DataError("Autoridades não informadas")
        supply = self.call("getTokenSupply", [mint, {"commitment": "finalized"}])
        largest = self.call("getTokenLargestAccounts", [mint, {"commitment": "finalized"}])
        total = int(supply["value"]["amount"])
        share = None if mint == SOL or total == 0 else min(
            1, sum(int(row["amount"]) for row in largest["value"][:10]) / total)
        return dict(mint=mint, token_program=value["owner"],
                    mint_authority=info["mintAuthority"], freeze_authority=info["freezeAuthority"],
                    top10_account_share=share, account_checked=True, cluster_verified=True,
                    slot=account["context"]["slot"],
                    warnings=["RPC público e contas SPL; não classifica contas de pool/custódia."])


class CoinbaseMarket:
    """Coinbase Advanced Trade public spot data, restricted to Solana's native SOL mint."""
    BASE = "https://api.coinbase.com/api/v3/brokerage/market"
    PRODUCT_IDS = {"SOL-USDC"}
    GRANULARITIES = {60: "ONE_MINUTE", 300: "FIVE_MINUTE", 900: "FIFTEEN_MINUTE"}

    def __init__(self, http=None, product_id=None):
        self.http = http or HTTP(timeout=8, retries=0)
        self.product_id = product_id or "SOL-USDC"
        if self.product_id not in self.PRODUCT_IDS:
            raise ValueError("Somente o produto Coinbase SOL-USDC é permitido")

    def _get(self, path, params=None):
        url = f"{self.BASE}/{path}"
        if params:
            url += "?" + urlencode(params)
        return self.http.json(url, headers={"Cache-Control": "no-cache"})

    def candles(self, mint=SOL, count=120, aggregate=900, now=None):
        if pubkey(mint) != SOL:
            raise DataError("Coinbase feed habilitado somente para o mint nativo SOL")
        if type(count) is not int or not 80 <= count <= 348:
            raise ValueError("count precisa estar entre 80 e 348")
        if aggregate not in self.GRANULARITIES:
            raise ValueError("aggregate precisa ser 1, 5 ou 15 minutos")
        step = aggregate
        cutoff = int(time.time() if now is None else now)
        end = cutoff // step * step
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
        return rows

    def market(self, mint=SOL, candles=None, timeframe_seconds=900):
        if pubkey(mint) != SOL:
            raise DataError("Coinbase market data habilitado somente para o mint nativo SOL")
        product = self._get(f"products/{quote(self.product_id, safe='')}")
        if not isinstance(product, dict) or product.get("product_id") != self.product_id:
            raise DataError("Produto Coinbase inválido")
        if product.get("base_currency_id") != "SOL" or product.get("quote_currency_id") != "USDC":
            raise DataError("Produto Coinbase não representa SOL contra USDC")
        if product.get("is_disabled") is True or product.get("trading_disabled") is True:
            raise DataError("Produto Coinbase desabilitado")

        book = self._get("product_book", {"product_id": self.product_id, "limit": 50})
        try:
            pricebook = book["pricebook"]
            bids, asks = pricebook["bids"], pricebook["asks"]
            best_bid, best_ask = float(bids[0]["price"]), float(asks[0]["price"])
        except (KeyError, TypeError, ValueError, IndexError):
            raise DataError("Livro Coinbase inválido ou vazio") from None
        if min(best_bid, best_ask) <= 0 or best_bid > best_ask:
            raise DataError("Melhor bid/ask Coinbase inválido")
        mid = (best_bid + best_ask) / 2
        bid_depth = self._depth(bids, mid, lower=True)
        ask_depth = self._depth(asks, mid, lower=False)
        if min(bid_depth, ask_depth) <= 0:
            raise DataError("Profundidade Coinbase insuficiente")

        trade_data = self._get(f"products/{quote(self.product_id, safe='')}/ticker", {"limit": 100})
        trades = trade_data.get("trades") if isinstance(trade_data, dict) else None
        if not isinstance(trades, list) or not trades:
            raise DataError("Trades Coinbase ausentes ou inválidos")
        buy_notional = sell_notional = 0.0
        try:
            for trade in trades:
                notional = float(trade["price"]) * float(trade["size"])
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
        try:
            volume_base = float(product["volume_24h"])
            product_price = float(product.get("price", mid))
        except (KeyError, TypeError, ValueError, OverflowError):
            raise DataError("Volume/preço Coinbase inválido") from None
        if min(volume_base, product_price) < 0 or product_price == 0:
            raise DataError("Volume/preço Coinbase inválido")
        # Coinbase volume_24h is base-asset volume; convert to quote notional.
        volume_quote = volume_base * product_price
        if (candles and timeframe_seconds <= 900
                and len(candles) >= 86400 // timeframe_seconds):
            # Prefer exact quote notional only when the supplied bars cover a full day.
            day_ago = int(time.time()) - 86400
            if candles[0].timestamp <= day_ago:
                volume_quote = sum(bar.volume for bar in candles if bar.timestamp >= day_ago)
        return dict(mint=mint, product_id=self.product_id, price=mid,
                    bid=best_bid, ask=best_ask,
                    liquidity_usd=bid_depth + ask_depth, volume_24h_usd=volume_quote,
                    buy_sell_imbalance=imbalance, source="coinbase_advanced_sol_spot")

    @staticmethod
    def _depth(levels, mid, lower):
        depth = 0.0
        for level in levels:
            try:
                price, size = float(level["price"]), float(level["size"])
            except (KeyError, TypeError, ValueError, OverflowError):
                raise DataError("Nível do livro Coinbase inválido") from None
            if price <= 0 or size < 0:
                raise DataError("Nível do livro Coinbase inválido")
            if (price >= mid * .99) if lower else (price <= mid * 1.01):
                depth += price * size
        return depth


def collect(mint=SOL, rpc=None, market=None):
    r = (rpc or SolanaRPC()).inspect(mint)
    if not market:
        raise DataError("Dados atuais da Coinbase são obrigatórios")
    observed_at = int(time.time())
    return Snapshot(timestamp=observed_at, mint=mint, price=market["price"],
                    liquidity_usd=market["liquidity_usd"], volume_24h_usd=market["volume_24h_usd"],
                    buy_sell_imbalance=market["buy_sell_imbalance"],
                    mint_authority=r["mint_authority"], freeze_authority=r["freeze_authority"],
                    top10_account_share=r["top10_account_share"], token_program=r["token_program"],
                    account_checked=True, cluster_verified=True, source=market["source"], slot=r["slot"],
                    warnings=tuple(r["warnings"] + [
                        "Mercado, preço, livro e trades vêm da Coinbase; segurança do mint vem de RPC Solana.",
                        "Paper fills usam o midpoint Coinbase mais custos configurados; não são ordens ou cotação executável."]))
