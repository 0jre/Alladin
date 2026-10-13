import csv
import json
import math
import random
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import asdict
from statistics import mean,pstdev
from .models import Candle,Snapshot,SOL,utc_timestamp

def demo_feed(count=600,seed=42,timeframe=900):
    """Explicitly synthetic causal fixture, never marketed as historical market data."""
    rng = random.Random(seed)
    price = 150
    start = 1767225600
    for i in range(count):
        drift = .0010 if i < count//3 else -.0010 if i < 2*count//3 else 0
        op = price
        price *= math.exp(drift+rng.gauss(0,.004))
        high = max(op,price)*(1+rng.uniform(.001,.005))
        low = min(op,price)*(1-rng.uniform(.001,.005))
        ts = start+i*timeframe
        funding = .00002 if i%4 == 0 else 0
        b = Candle(ts,op,high,low,price,rng.uniform(40000,120000),funding)
        s = Snapshot(ts+timeframe,price=price,liquidity_usd=10000000,volume_24h_usd=50000000,
                     buy_sell_imbalance=rng.uniform(-.2,.2),account_checked=True,cluster_verified=True,
                     oracle_price=price,oracle_timestamp=ts+timeframe,expected_funding_hourly=.00002,
                     perp_market_verified=True,source='SYNTHETIC_FIXTURE',
                     warnings=('Todos os campos de mercado e segurança são sintéticos.',))
        yield b,s

def jsonl_feed(path):
    with Path(path).open() as f:
        for line_no,line in enumerate(f,1):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                if set(d) != {'candle','snapshot'}:
                    raise ValueError('Esperado candle e snapshot')
                yield Candle(**d['candle']),Snapshot(**d['snapshot'])
            except (ValueError,KeyError,TypeError) as e:
                raise ValueError(f'Feed inválido na linha {line_no}: {e}') from None

def write_demo(path,count=600):
    p = Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('w') as f:
        for b,s in demo_feed(count):
            f.write(json.dumps(dict(candle=asdict(b),snapshot=asdict(s)),allow_nan=False)+'\n')

def export(service,destination):
    out = Path(destination)
    out.mkdir(parents=True,exist_ok=True)
    with service.store.connect() as db:
        state = service._load(db)
        rows = db.execute('SELECT seq,ts,kind,payload FROM events ORDER BY seq').fetchall()
    curve,trades = [],[]
    with (out/'audit.jsonl').open('w') as f:
        for seq,ts,kind,payload in rows:
            d = json.loads(payload)
            f.write(json.dumps(dict(seq=seq,timestamp=ts,kind=kind,payload=d),allow_nan=False)+'\n')
            if kind == 'cycle':
                curve.append(dict(timestamp=ts,equity=d['equity']))
            trades.extend(x for x in d.get('events',[]) if x.get('event') == 'CLOSE')
    final = service.status()['equity_usdc']
    if curve:
        curve.append(dict(timestamp=curve[-1]['timestamp'],equity=final))
    peak = service.cfg.initial_usdc
    maxdd = 0
    for point in curve:
        peak = max(peak,point['equity'])
        maxdd = max(maxdd,1-point['equity']/peak)
    pnl = [t['net_pnl'] for t in trades]
    profit,loss = sum(max(0,p) for p in pnl),-sum(min(0,p) for p in pnl)
    returns = [b['equity']/a['equity']-1 for a,b in zip(curve,curve[1:]) if a['equity']>0]
    summary = dict(chain='solana',execution='paper',agent_mode=service.council.mode,
                   source=state['snapshot']['source'] if state['snapshot'] else None,
                   initial_usdc=service.cfg.initial_usdc,final_usdc=final,
                   return_pct=(final/service.cfg.initial_usdc-1)*100,
                   max_drawdown_pct=maxdd*100,closed_trades=len(pnl),
                   win_fraction=sum(p>0 for p in pnl)/len(pnl) if pnl else None,
                   profit_factor=profit/loss if loss else None,
                   mean_trade_net_pnl=mean(pnl) if pnl else None,
                   costs_usdc=service.status()['costs_usdc'],
                   funding_paid_usdc=sum(t['funding_paid'] for t in trades),
                   bar_return_mean=mean(returns) if returns else None,
                   bar_return_std=pstdev(returns) if returns else None,
                   halted=service.status()['halted'],halt_reason=service.status()['halt_reason'],
                   llm_calls_process=service.council.client.calls,
                   warnings=['Não mede vantagem preditiva ou prontidão de produção.',
                             'Custos hipotéticos; perp é aproximação, não réplica de Drift/Adrena.',
                             'Sem Sharpe anualizado: intervalo/amostra não justificam extrapolação.'])
    (out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False,allow_nan=False))
    with (out/'equity.csv').open('w',newline='') as f:
        w = csv.DictWriter(f,fieldnames=['timestamp','equity'])
        w.writeheader(); w.writerows(curve)
    with (out/'trades.csv').open('w',newline='') as f:
        fields = list(trades[0]) if trades else ['position_id','net_pnl']
        w = csv.DictWriter(f,fieldnames=fields)
        w.writeheader(); w.writerows(trades)
    return summary
