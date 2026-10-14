"""Evidence and deterministic economics for finance-agent deliberation."""
import hashlib
import math
from dataclasses import asdict,replace

from .risk import approve
from .storage import canonical


def candidate_economics(proposals,f,s,book,cfg,now):
    rows=[]
    stress=replace(cfg,fee_bps=cfg.fee_bps*2,slippage_bps=cfg.slippage_bps*2,
                   fixed_cost_usdc=cfg.fixed_cost_usdc*2)
    for proposal in proposals:
        p=replace(proposal,mint=s.mint)
        approval=approve(p,f,s,book,cfg,now,s.price)
        stressed=approve(p,f,s,book,stress,now,s.price)
        affordable=max(0,book.cash-cfg.fixed_cost_usdc)/(1+(cfg.fee_bps+cfg.slippage_bps)/10000)
        reference=approval.notional or min(affordable,book.equity(s.price)*cfg.max_position_fraction)
        costs=(2*(cfg.fee_bps+cfg.slippage_bps)/10000+2*cfg.fixed_cost_usdc/reference) if reference>0 else None
        net_rr=(p.take_fraction-costs)/(p.stop_fraction+costs) if costs is not None else None
        rows.append(dict(action=p.action,market=p.market,strategy=p.strategy,
                         stop_fraction=p.stop_fraction,take_fraction=p.take_fraction,
                         approval=asdict(approval),stress_2x=asdict(stressed),
                         reference_notional_usdc=reference,reference_is_approved=approval.approved,
                         estimated_roundtrip_cost_fraction=costs,net_reward_risk=net_rr))
    return rows


def evidence_envelope(f,s,book,cfg,proposals,now,memory=()):
    if f.get('bar_closed_at',now)>now:
        raise ValueError('Indicadores posteriores ao instante da decisão')
    portfolio=book.serialize()
    portfolio['closed']=portfolio['closed'][-20:]
    envelope=dict(schema_version='1.0',as_of=now,
        mandate=dict(chain=cfg.chain,market='spot',execution=cfg.execution,mint=s.mint,
                     sizing_mode=cfg.sizing_mode,confidence_is_win_probability=False),
        features=dict(f),snapshot={k:v for k,v in asdict(s).items() if k not in {
            'account_checked','cluster_verified','slot','mint_authority','freeze_authority','token_program',
            'top10_account_share','extensions','extensions_decoded','transfer_fee_bps'}},portfolio=portfolio,
        candidates=[asdict(replace(p,mint=s.mint)) for p in proposals],config=asdict(cfg),
        candidate_economics=candidate_economics(proposals,f,s,book,cfg,now),
        data_quality=dict(snapshot_age_seconds=now-s.timestamp,
            missing_domains=['onchain_data','macro_news','order_routing','DEX_executable_liquidity','MEV',
                             'network_execution_costs','calibrated_win_probability','out_of_sample_edge'],
            volume_quote_is_estimated=True,source=s.source),
        memory=list(memory)[-20:],
        research_validation=dict(status='not_supplied',win_probability_calibrated=False,
                                 near_perfect_hit_rate_validated=False))
    registry={}
    def visit(value,path):
        if isinstance(value,dict):
            for key,item in value.items():visit(item,path+'.'+str(key) if path else str(key))
        elif isinstance(value,(tuple,list)):
            for i,item in enumerate(value):visit(item,path+'.'+str(i))
        elif value is not None:
            if isinstance(value,float) and not math.isfinite(value):
                raise ValueError('Evidência numérica não finita')
            source=(s.source if path.startswith('snapshot.') else
                    'computed_closed_candles' if path.startswith('features.') else 'backend')
            available=(s.timestamp if path.startswith('snapshot.') else
                       f.get('bar_closed_at',now) if path.startswith('features.') else now)
            registry[path]=dict(value=value,source=source,available_at=available)
    visit(envelope,'')
    envelope['evidence_registry']=registry
    envelope['evidence_sha256']=hashlib.sha256(canonical(envelope).encode()).hexdigest()
    return envelope
