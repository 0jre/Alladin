from dataclasses import dataclass
from datetime import datetime, timezone
from .models import SOL, TOKEN_PROGRAM, TOKEN_2022

@dataclass(frozen=True)
class Approval:
    approved: bool
    reasons: tuple
    notional: float = 0.0
    leverage: float = 1.0
    estimated_stop_loss_usdc: float = 0.0

def security_checks(s,cfg,now):
    reasons = []
    if s.chain != cfg.chain:
        reasons.append('wrong_chain_or_mint')
    if s.chain == 'solana':
        # On-chain controls only exist for SPL/Token-2022 mints.
        if not s.account_checked or not s.cluster_verified:
            reasons.append('unverified_onchain_data')
        if s.token_program == TOKEN_2022:
            if not s.extensions_decoded:
                reasons.append('token2022_extensions_not_decoded')
            if set(s.extensions) & {'non_transferable', 'permanent_delegate', 'pausable', 'default_frozen'}:
                reasons.append('dangerous_token2022_extension')
            if 'transfer_hook' in s.extensions:
                reasons.append('unknown_transfer_hook')
            if 'transfer_fee' in s.extensions and not cfg.allow_transfer_fee:
                reasons.append('transfer_fee_blocked')
        elif s.token_program != TOKEN_PROGRAM:
            reasons.append('unsupported_token_program')
        if s.mint_authority is not None or s.freeze_authority is not None:
            reasons.append('active_token_authority')
        if s.mint != SOL and (s.top10_account_share is None or s.top10_account_share > cfg.max_top10_account_share):
            reasons.append('holder_concentration_unknown_or_high')
    # Price/liquidity gates apply to the current Solana spot observation.
    if s.timestamp > now or now-s.timestamp > cfg.max_snapshot_age_seconds:
        reasons.append('future_or_stale_snapshot')
    if s.liquidity_usd < cfg.min_liquidity_usd:
        reasons.append('insufficient_liquidity')
    if s.volume_24h_usd < cfg.min_volume_24h_usd:
        reasons.append('insufficient_volume')
    return reasons

def update_breakers(book,cfg,price,timestamp):
    equity = book.equity(price)
    day = datetime.fromtimestamp(timestamp,timezone.utc).date().isoformat()
    if day != book.day:
        book.day, book.day_start_equity = day, equity
    book.peak = max(book.peak,equity)
    if equity <= 0:
        book.halted,book.halt_reason = True,'equity_nonpositive'
    elif 1-equity/book.peak >= cfg.max_drawdown:
        book.halted,book.halt_reason = True,'maximum_drawdown'
    elif book.day_start_equity and 1-equity/book.day_start_equity >= cfg.max_daily_loss:
        book.halted,book.halt_reason = True,'daily_loss'
    # Latching: a daily halt needs a new research run; never silently resumes.
    return equity

def approve(p,f,s,book,cfg,now,entry_price=None,instrument=None):
    if p.action in {'HOLD','CLOSE'}:
        return Approval(True,('non_entry',))
    price = entry_price or f.get('price') or s.price
    reasons = security_checks(s,cfg,now)
    if getattr(p, 'mint', s.mint) != s.mint:
        reasons.append('proposal_mint_mismatch')
    if s.mint != cfg.mint:
        if not instrument or instrument.get('status') != 'negotiable' or instrument.get('mint') != s.mint:
            reasons.append('mint_not_negotiable')
        if not (s.sell_simulated and s.route_buy and s.route_sell):
            reasons.append('exit_route_not_proven')
    if book.halted:
        reasons.append('circuit_breaker:'+book.halt_reason)
    if now < book.cooldown_until:
        reasons.append('cooldown')
    if p.market not in cfg.allowed_markets:
        reasons.append('market_not_enabled')
    if p.market == 'spot' and p.action == 'SHORT':
        reasons.append('spot_cannot_short')
    if any(x.market == p.market and x.mint == getattr(p, 'mint', SOL) for x in book.positions):
        reasons.append('market_position_already_open')
    if p.confidence < cfg.min_confidence:
        reasons.append('low_score')
    if not f.get('ready') or f.get('regime') == 'shock':
        reasons.append('warmup_or_shock')
    if f.get('cvar95_bar',1) > cfg.max_historical_cvar:
        reasons.append('historical_tail_risk')
    if abs(price/s.price-1) > cfg.max_entry_gap_fraction:
        reasons.append('reference_price_deviation')
    equity = book.equity(price)
    cost_fraction = 2*(cfg.fee_bps+cfg.slippage_bps)/10000
    # RR net of estimated roundtrip costs, not model confidence / win probability.
    if (p.take_fraction-cost_fraction)/(p.stop_fraction+cost_fraction) < cfg.min_reward_risk:
        reasons.append('reward_risk_after_costs')
    leverage = 1 if p.market == 'spot' else cfg.max_leverage
    if p.market == 'perp':
        if not s.perp_market_verified or s.oracle_price is None or s.oracle_timestamp is None or s.expected_funding_hourly is None:
            reasons.append('missing_perp_oracle_or_funding')
        else:
            if s.oracle_timestamp > now or now-s.oracle_timestamp > cfg.max_oracle_age_seconds:
                reasons.append('stale_perp_oracle')
            if abs(price/s.oracle_price-1) > cfg.max_oracle_deviation:
                reasons.append('oracle_deviation')
            side = 1 if p.action == 'LONG' else -1
            adverse_funding = max(0,side*s.expected_funding_hourly)*p.horizon_bars*cfg.timeframe_seconds/3600
            if (p.take_fraction-cost_fraction-adverse_funding)/(p.stop_fraction+cost_fraction) < cfg.min_reward_risk:
                reasons.append('funding_erodes_reward_risk')
            if 1/leverage - p.stop_fraction <= cfg.maintenance_fraction + cost_fraction:
                reasons.append('stop_too_close_to_liquidation')
    if reasons:
        return Approval(False,tuple(reasons))
    existing_risk = sum(x.qty*max(0,x.side*(price-x.stop)) for x in book.positions)
    budget = min(equity*cfg.risk_per_trade,max(0,equity*cfg.max_open_risk-existing_risk))
    budget -= 2*cfg.fixed_cost_usdc
    notional = max(0,budget)/(p.stop_fraction+cost_fraction)
    side = 1 if p.action == 'LONG' else -1
    # Combined exposure limit; no fake diversification across positions.
    notional = min(notional,equity*cfg.max_position_fraction,
                   max(0,equity*cfg.max_gross_fraction-book.gross(price)),
                   max(0,equity*cfg.max_net_fraction-side*book.net(price)),
                   s.liquidity_usd*cfg.max_pool_participation)
    available = max(0,book.cash-cfg.fixed_cost_usdc)
    notional = min(notional,available/(1/leverage+(cfg.fee_bps+cfg.slippage_bps)/10000))
    if notional < 10:
        return Approval(False,('insufficient_budget',))
    total_cost_fraction = cost_fraction+2*cfg.fixed_cost_usdc/notional
    if (p.take_fraction-total_cost_fraction)/(p.stop_fraction+total_cost_fraction) < cfg.min_reward_risk:
        return Approval(False,('reward_risk_after_fixed_costs',))
    return Approval(True,('risk_constraints_passed',),notional,leverage,
                    notional*(p.stop_fraction+cost_fraction)+2*cfg.fixed_cost_usdc)
