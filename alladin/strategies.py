from .models import Proposal

def candidates(f, s, cfg):
    if not f.get('ready') or f['regime'] == 'shock':
        return []
    stop = min(.08,max(.01,2*f['atr_fraction']))
    ideas = []
    def add(side, strategy, score, rr=2.2):
        for market in cfg.allowed_markets:
            if side < 0 and market == 'spot':
                continue
            ideas.append(Proposal('LONG' if side > 0 else 'SHORT',market,
                                  min(.88,max(0,score)),stop,min(.25,stop*rr),
                                  24,f'{strategy}; regime={f["regime"]}; RSI={f["rsi"]:.1f}',strategy))
    if f['regime'] == 'trend':
        side = 1 if f['ema_gap'] > 0 else -1
        if side*f['higher_trend'] > 0 and side*f['momentum_12'] > .003 and 25 < f['rsi'] < 80:
            add(side,'trend_following',.60 + min(.15,abs(f['ema_gap'])*10) + min(.1,f['efficiency']*.15))
        if f['volume_ratio'] > 1.3:
            if f['price'] > f['breakout_high']:
                add(1,'volume_breakout',.73)
            if f['price'] < f['breakout_low']:
                add(-1,'volume_breakout',.73)
    elif f['regime'] == 'range' and f['efficiency'] < .25:
        if f['zscore'] < -1.7 and f['rsi'] < 35:
            add(1,'mean_reversion',.69,2)
        elif f['zscore'] > 1.7 and f['rsi'] > 65:
            add(-1,'mean_reversion',.69,2)
    # Flow score only changes candidate ranking, never bypasses security gates.
    ranked = []
    for p in ideas:
        side = 1 if p.action == 'LONG' else -1
        score = max(0,min(.9,p.confidence + side*s.buy_sell_imbalance*.03))
        ranked.append(Proposal(**{**p.__dict__,'confidence': score}))
    return sorted(ranked,key=lambda p:p.confidence,reverse=True)
