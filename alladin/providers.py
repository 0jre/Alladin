"""Read-only Solana market collectors used by paper mode.

No wallet signer, transaction builder, or transaction submission lives here.
"""
import os
import time
from urllib.parse import urlencode, quote

from .models import Candle, Snapshot, SOL, USDC, TOKEN_PROGRAM, MAINNET_GENESIS, pubkey
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


class DexScreener:
    """Read-only pool locator/current statistics, restricted to SOL/USDC on Solana."""
    def __init__(self, http=None):
        self.http = http or HTTP(timeout=8, retries=0)

    def market(self, mint=SOL):
        pubkey(mint)
        pairs = self.http.json(f"https://api.dexscreener.com/token-pairs/v1/solana/{mint}")
        if not isinstance(pairs, list):
            raise DataError("Resposta de pools inválida")
        valid = [p for p in pairs if isinstance(p, dict) and p.get("chainId") == "solana"
                 and p.get("baseToken", {}).get("address") == mint
                 and p.get("quoteToken", {}).get("address") == USDC
                 and p.get("pairAddress") and p.get("priceNative")
                 and (p.get("liquidity") or {}).get("usd")]
        if not valid:
            raise DataError("Nenhuma pool SOL/USDC válida encontrada na Solana")
        row = max(valid, key=lambda p: float(p["liquidity"]["usd"]))
        price = float(row["priceNative"])
        liquidity = float(row["liquidity"]["usd"])
        volume = float((row.get("volume") or {}).get("h24", 0))
        if min(price, liquidity) <= 0 or volume < 0:
            raise DataError("Dados da pool inválidos")
        trades = (row.get("txns") or {}).get("h1", {})
        buys, sells = int(trades.get("buys", 0)), int(trades.get("sells", 0))
        return dict(mint=mint, pool=row["pairAddress"], dex=row.get("dexId"),
                    price=price, liquidity_usd=liquidity, volume_24h_usd=volume,
                    buy_sell_imbalance=(buys-sells)/(buys+sells) if buys+sells else 0.0,
                    source="dexscreener_solana_pool_usdc")


class GeckoTerminal:
    """On-chain DEX pool OHLCV. Public API is beta and may be rate limited."""
    BASE = "https://api.geckoterminal.com/api/v2"

    def __init__(self, http=None):
        self.http = http or HTTP(timeout=8, retries=0)

    def candles(self, pool, count=120, aggregate=1, now=None):
        if not isinstance(pool, str) or not 20 <= len(pool) <= 64:
            raise ValueError("Endereço de pool inválido")
        if type(count) is not int or not 80 <= count <= 1000:
            raise ValueError("count precisa estar entre 80 e 1000")
        if type(aggregate) is not int or aggregate not in {1, 5, 15}:
            raise ValueError("aggregate precisa ser 1, 5 ou 15 minutos")
        query = urlencode({"aggregate": aggregate, "limit": count, "currency": "token", "token": "base"})
        url = f"{self.BASE}/networks/solana/pools/{quote(pool, safe='')}/ohlcv/minute?{query}"
        data = self.http.json(url, headers={"Accept": "application/json;version=20230203"})
        try:
            attrs = data["data"]["attributes"]
            raw = attrs["ohlcv_list"]
        except (TypeError, KeyError):
            raise DataError("Resposta OHLCV GeckoTerminal inválida") from None
        if not isinstance(raw, list):
            raise DataError("Lista OHLCV GeckoTerminal inválida")
        step = aggregate * 60
        cutoff = int(time.time() if now is None else now)
        rows = []
        for item in raw:
            if not isinstance(item, list) or len(item) != 6:
                raise DataError("Registro OHLCV GeckoTerminal inválido")
            try:
                ts = int(item[0])
                if ts + step > cutoff:
                    continue  # never consume the still-open candle
                rows.append(Candle(ts, float(item[1]), float(item[2]), float(item[3]),
                                   float(item[4]), float(item[5]), mint=SOL))
            except (ValueError, TypeError, OverflowError):
                raise DataError("Valores OHLCV GeckoTerminal inválidos") from None
        rows.sort(key=lambda candle: candle.timestamp)
        if not rows:
            raise DataError("GeckoTerminal ainda não retornou candles fechados")
        if len(rows) > count:
            rows = rows[-count:]
        if any(b.timestamp != a.timestamp + step for a, b in zip(rows, rows[1:])):
            raise DataError("OHLCV contém lacunas; recusa replay com barras ausentes")
        return rows


def collect(mint=SOL, rpc=None, dex=None, market=None):
    r = (rpc or SolanaRPC()).inspect(mint)
    market = market or (dex or DexScreener()).market(mint)
    observed_at = int(time.time())
    return Snapshot(timestamp=observed_at, mint=mint, price=market["price"],
                    liquidity_usd=market["liquidity_usd"], volume_24h_usd=market["volume_24h_usd"],
                    buy_sell_imbalance=market["buy_sell_imbalance"],
                    mint_authority=r["mint_authority"], freeze_authority=r["freeze_authority"],
                    top10_account_share=r["top10_account_share"], token_program=r["token_program"],
                    account_checked=True, cluster_verified=True, source=market["source"], slot=r["slot"],
                    warnings=tuple(r["warnings"] + [
                        "OHLCV histórico vem de GeckoTerminal; liquidez/volume são observações atuais.",
                        "Paper fills estimam taxa/slippage; não são execução de rota Jupiter."]))
