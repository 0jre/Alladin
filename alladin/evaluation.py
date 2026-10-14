"""Observed trade statistics; never a guarantee of future returns."""
import math
import json
from statistics import NormalDist,mean


def assess_trades(trades,source,agent_mode,target_entries=900,max_nonwins=2):
    if type(target_entries) is not int or target_entries<1 or type(max_nonwins) is not int or not 0<=max_nonwins<target_entries:
        raise ValueError('Meta de amostra inválida')
    rows=list(trades)
    seen=set()
    for row in rows:
        pid=row.get('position_id')
        pnl=row.get('net_pnl')
        if not isinstance(pid,str) or not pid or pid in seen:
            raise ValueError('Operação sem identificação única')
        seen.add(pid)
        if type(pnl) not in (int,float) or not math.isfinite(pnl):
            raise ValueError('PnL líquido deve ser finito')
    pnl=[row['net_pnl'] for row in rows]
    n=len(pnl)
    wins=sum(value>0 for value in pnl)
    losses=sum(value<0 for value in pnl)
    flat=n-wins-losses
    z=NormalDist().inv_cdf(.975)
    if n:
        rate=wins/n
        denom=1+z*z/n
        center=(rate+z*z/(2*n))/denom
        radius=z*math.sqrt(rate*(1-rate)/n+z*z/(4*n*n))/denom
        interval=[max(0,center-radius),min(1,center+radius)]
    else:
        rate=None
        interval=[None,None]
    window=pnl[-target_entries:]
    nonwins=sum(value<=0 for value in window)
    target=(target_entries-max_nonwins)/target_entries
    eligible=source=='coinbase_advanced_sol_spot' and agent_mode in {'rules','llm'}
    groups={}
    for row in rows:
        context=row.get('decision_context')
        label={key:context.get(key) for key in ('agent_mode','model','prompt_bundle_sha256')} if isinstance(context,dict) else {'context':'unrecorded'}
        key=json.dumps(label,sort_keys=True)
        groups.setdefault(key,{'context':label,'closed_roundtrips':0})['closed_roundtrips']+=1
        if 'entry_source' in row and row['entry_source']!='coinbase_advanced_sol_spot':
            eligible=False
    homogeneous=len(groups)<=1
    profit=sum(max(0,value) for value in pnl)
    loss=-sum(min(0,value) for value in pnl)
    observed=n>=target_entries and nonwins<=max_nonwins
    return dict(closed_roundtrips=n,wins=wins,losses=losses,breakeven=flat,win_rate=rate,
        net_pnl_usdc=sum(pnl),mean_net_pnl_usdc=mean(pnl) if pnl else None,
        profit_factor=profit/loss if loss else None,worst_trade_usdc=min(pnl) if pnl else None,
        win_rate_wilson_95=interval,source_label=source,agent_mode=agent_mode,
        strategy_data_eligible=eligible,
        decision_contexts=list(groups.values()),mixed_decision_contexts=not homogeneous,
        target=dict(entries=target_entries,max_nonwins=max_nonwins,min_win_rate=target,
                    sample_sufficient=n>=target_entries,window_closed_roundtrips=len(window),
                    window_nonwins=nonwins,observed_target_met=observed,
                    lower_bound_reaches_target=bool(n and interval[0]>=target),
                    measured_claim_supported=bool(eligible and homogeneous and observed and n and interval[0]>=target and sum(pnl)>0)),
        guarantees_future_results=False,
        limitations=['Win is strictly positive net PnL after modeled costs; breakeven is a non-win.',
            'The last chronological 900 closed trades are used for the default observed target; none are discarded.',
            'Wilson bounds assume binomial sampling; serial dependence and regime changes weaken inference.',
            'Source labels are metadata, not independent attestation of authentic market data.',
            'Different models or prompt versions cannot be pooled to validate this target.',
            'Controlled or fixture trades do not validate autonomous strategy performance.'])
