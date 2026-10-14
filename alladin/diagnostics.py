"""Read-only source checks. No inference, trades, ledger mutation or secret output."""
import time
from .providers import CoinbaseMarket
from .transport import DataError,deadline,COLLECTION_TOTAL_SECONDS
from .risk import profile_feasibility


def diagnose(cfg):
    checks={}
    provider=CoinbaseMarket()
    def check(name,read):
        begin=time.monotonic()
        try:
            with deadline(COLLECTION_TOTAL_SECONDS):
                detail=read()
            checks[name]=dict(ok=True,elapsed_seconds=time.monotonic()-begin,detail=detail)
        except (DataError,ValueError) as exc:
            checks[name]=dict(ok=False,elapsed_seconds=time.monotonic()-begin,
                error=dict(message=str(exc),**(exc.details() if isinstance(exc,DataError) else {'code':'invalid_data'})))
    def market():
        candles=provider.candles(cfg.mint,120,cfg.timeframe_seconds)
        if time.time()-(candles[-1].timestamp+cfg.timeframe_seconds)>cfg.timeframe_seconds:
            raise DataError('Feed Coinbase atrasado',code='stale_data',source='coinbase_candles')
        quote=provider.market(cfg.mint,candles,cfg.timeframe_seconds)
        if time.time()-(candles[-1].timestamp+cfg.timeframe_seconds)>cfg.timeframe_seconds:
            raise DataError('Candles expiraram durante a coleta; atualize o contexto',code='stale_data',source='coinbase_candles')
        return dict(closed_bars=len(candles),last_closed_at=candles[-1].timestamp+cfg.timeframe_seconds,
                    observed_at=quote['observed_at'],price=quote['price'],source=quote['source'])
    check('coinbase_market',market)
    feasibility=profile_feasibility(cfg)
    sources_ready=all(x['ok'] for x in checks.values())
    return dict(ready=sources_ready and feasibility.get('baseline_can_fit',True),sources_ready=sources_ready,
                profile_feasibility=feasibility,checked_at=int(time.time()),
                chain=cfg.chain,execution=cfg.execution,checks=checks,
                interpretation=('Coinbase source checks passed; profile feasibility is a necessary condition, not an entry signal.' if sources_ready else
                    'Inspect the failed source stage; proxy_tunnel is before TLS/API response. Only Coinbase is used.'))
