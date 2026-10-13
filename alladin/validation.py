"""Fixed-parameter chronological out-of-sample blocks and execution cost stress."""
import json
from pathlib import Path
from dataclasses import asdict,replace
from .engine import Service
from .research import jsonl_feed,export

def assert_causal_feed(rows,timeframe):
    """Recusa snapshot, disponibilidade ou mint que a decisão da barra ainda não podia ver."""
    previous = {}
    for b,s in rows:
        if s.mint != b.mint:
            raise ValueError('Lookahead: mint divergente entre candle e snapshot')
        end = b.timestamp+timeframe
        if s.timestamp > end or (s.available_at is not None and s.available_at > end):
            raise ValueError('Lookahead: dado posterior ao fechamento')
        prev = previous.get(b.mint)
        if prev is not None and b.timestamp != prev+timeframe:
            raise ValueError('Lacuna no feed de validação')
        previous[b.mint] = b.timestamp
    return sorted(previous)

def validate(cfg,feed_path,output,folds=3):
    if not 2 <= folds <= 10:
        raise ValueError('folds deve estar entre 2 e 10')
    rows=list(jsonl_feed(feed_path))
    cohorts=assert_causal_feed(rows,cfg.timeframe_seconds)
    available=len(rows)-cfg.warmup_bars
    if available < folds*40:
        raise ValueError('Feed precisa de warmup + pelo menos 40 barras de avaliação por fold')
    out=Path(output)
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    for stress in [1,2]:
        stress_cfg=replace(cfg,fee_bps=cfg.fee_bps*stress,slippage_bps=cfg.slippage_bps*stress,
                           fixed_cost_usdc=cfg.fixed_cost_usdc*stress)
        for fold in range(folds):
            start=cfg.warmup_bars+available*fold//folds
            end=cfg.warmup_bars+available*(fold+1)//folds
            folder=out/f'cost_{stress}x_fold_{fold+1}'
            folder.mkdir(exist_ok=True)
            db=folder/'session.sqlite'
            if db.exists():
                raise ValueError('Pasta de validação já contém sessão; escolha outro output')
            service=Service(stress_cfg,db,'rules')
            # Context is earlier data only; no entry until the first evaluation bar.
            armed = {stress_cfg.mint}
            for b,s in rows[start-cfg.warmup_bars:end]:
                if b.mint not in armed:
                    service.command('admit',dict(snapshot=asdict(s)),f'admit:{b.mint}')
                    service.command('watch',dict(mint=b.mint,arm=True),f'watch:{b.mint}')
                    armed.add(b.mint)
                service.command('ingest',dict(candle=asdict(b),snapshot=asdict(s)),f'bar:{b.mint}:{b.timestamp}')
            service.command('finalize',{},'finalize')
            summary=export(service,folder)
            summary.update(fold=fold+1,cost_multiplier=stress,evaluation_start=rows[start][0].timestamp,
                           evaluation_end=rows[end-1][0].timestamp,evaluation_bars=end-start,
                           warmup_bars=cfg.warmup_bars)
            results.append(summary)
    report=dict(method='fixed_parameter_chronological_folds',folds=folds,
                optimized=False,llm_evaluated=False,cohorts=cohorts,results=results,
                warnings=['Sem otimização ou seleção pelo retorno desses folds.',
                          'Indicadores recebem apenas warmup anterior; conta reinicia por fold.',
                          'Dados sintéticos continuam sintéticos; executar em histórico real antes de inferir vantagem.'])
    (out/'validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False))
    return report
