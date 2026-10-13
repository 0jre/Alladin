"""Causal features using closed candles only. Scores are descriptive, not forecasts."""
import math
from statistics import mean, pstdev

def ema(values, length):
    result = values[0]
    alpha = 2/(length+1)
    for v in values[1:]:
        result = alpha*v + (1-alpha)*result
    return result

def rsi(closes, length=14):
    diffs = [b-a for a,b in zip(closes, closes[1:])][-length:]
    up, down = mean(max(d,0) for d in diffs), mean(max(-d,0) for d in diffs)
    return 50 if up == down == 0 else 100 if down == 0 else 100-100/(1+up/down)

def adx(bars,length=14):
    """Wilder directional movement / ADX; initial smoothing uses first length bars."""
    tr,plus,minus = [],[],[]
    for a,b in zip(bars,bars[1:]):
        up,down = b.high-a.high,a.low-b.low
        tr.append(max(b.high-b.low,abs(b.high-a.close),abs(b.low-a.close)))
        plus.append(up if up>down and up>0 else 0)
        minus.append(down if down>up and down>0 else 0)
    smooth_tr,smooth_plus,smooth_minus = sum(tr[:length]),sum(plus[:length]),sum(minus[:length])
    dx = []
    for i in range(length-1,len(tr)):
        if i>=length:
            smooth_tr = smooth_tr-smooth_tr/length+tr[i]
            smooth_plus = smooth_plus-smooth_plus/length+plus[i]
            smooth_minus = smooth_minus-smooth_minus/length+minus[i]
        p = 100*smooth_plus/smooth_tr if smooth_tr else 0
        m = 100*smooth_minus/smooth_tr if smooth_tr else 0
        dx.append(100*abs(p-m)/(p+m) if p+m else 0)
    value = mean(dx[:length]) if dx else 0
    for d in dx[length:]:
        value = (value*(length-1)+d)/length
    return value

def features(bars):
    if len(bars) < 80:
        return {'ready': False, 'count': len(bars)}
    closes = [b.close for b in bars]
    c = closes[-1]
    returns = [math.log(b/a) for a,b in zip(closes, closes[1:])][-64:]
    true_ranges = [max(b.high-b.low, abs(b.high-a.close), abs(b.low-a.close))
                   for a,b in zip(bars,bars[1:])]
    atr = mean(true_ranges[-14:])
    fast, slow = ema(closes[-80:],12), ema(closes[-80:],36)
    fast_prev = ema(closes[-81:-1],12)
    path = sum(abs(b-a) for a,b in zip(closes[-21:-1],closes[-20:]))
    efficiency = abs(closes[-1]-closes[-21])/path if path else 0
    sd = pstdev(closes[-20:])
    z = (c-mean(closes[-20:]))/sd if sd else 0
    sorted_losses = sorted(-r for r in returns)
    tail = sorted_losses[max(0, int(len(returns)*.95)):]
    cvar = max(0,mean(tail))
    # Slow-context signal from non-overlapping groups of four closed bars.
    period = bars[-1].timestamp-bars[-2].timestamp
    groups = {}
    for bar in bars:
        groups.setdefault(bar.timestamp//(period*4),[]).append(bar)
    higher = [group[-1].close for group in groups.values() if len(group)==4]
    htrend = (ema(higher,5)/ema(higher,15)-1) if len(higher) >= 15 else 0
    vol = pstdev(returns)
    directional = adx(bars[-80:])
    macd_series = [ema(closes[max(0,i-80):i],12)-ema(closes[max(0,i-80):i],26)
                   for i in range(len(closes)-19,len(closes)+1)]
    macd = macd_series[-1]
    macd_signal = ema(macd_series,9)
    bb_width = 4*sd/mean(closes[-20:])
    typical = [(b.high+b.low+b.close)/3 for b in bars[-20:]]
    base_volumes = [b.volume/t for b,t in zip(bars[-20:],typical)]
    denom = sum(base_volumes)
    vwap = sum(t*v for t,v in zip(typical,base_volumes))/denom if denom else c
    regime = 'shock' if atr/c > .05 or abs(returns[-1]) > .04 else 'trend' if efficiency > .30 else 'range'
    last20 = bars[-21:-1]
    avgvolume = mean(b.volume for b in bars[-21:-1])
    return dict(ready=True, count=len(bars), price=c, ema_fast=fast, ema_slow=slow,
                ema_slope=(fast-fast_prev)/c, ema_gap=(fast-slow)/c,
                atr=atr, atr_fraction=atr/c, rsi=rsi(closes), zscore=z,
                efficiency=efficiency, volatility_bar=vol, cvar95_bar=cvar,
                higher_trend=htrend, regime=regime,
                adx=directional,macd=macd,macd_signal=macd_signal,
                macd_histogram=(macd-macd_signal)/c,bollinger_width=bb_width,
                approximate_vwap=vwap,vwap_deviation=c/vwap-1,
                breakout_high=max(b.high for b in last20), breakout_low=min(b.low for b in last20),
                volume_ratio=bars[-1].volume/avgvolume if avgvolume else 0,
                momentum_12=c/closes[-13]-1,
                historical_var95_bar=max(0,sorted_losses[int(len(returns)*.95)]))
