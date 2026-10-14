"""Paper only: explicit conservative OHLC event ordering and isolated perp approximation."""
import hashlib
from .models import Position, SOL

class PaperBroker:
    def __init__(self,book,cfg):
        self.book,self.cfg = book,cfg
    def costs(self,notional):
        return notional*(self.cfg.fee_bps+self.cfg.slippage_bps)/10000+self.cfg.fixed_cost_usdc
    def open(self,p,a,price,ts):
        if not a.approved or a.notional <= 0 or self.book.halted:
            raise ValueError('Entrada sem aprovação válida')
        mint = getattr(p, 'mint', SOL)
        if any(x.market == p.market and x.mint == mint for x in self.book.positions):
            raise ValueError('Posição duplicada')
        side = 1 if p.action == 'LONG' else -1
        if p.action not in {'LONG','SHORT'} or p.market == 'spot' and side == -1:
            raise ValueError('Entrada inválida')
        qty = a.notional/price
        cost = self.costs(a.notional)
        margin = a.notional if p.market == 'spot' else a.notional/a.leverage
        if margin+cost > self.book.cash+1e-8:
            raise ValueError('Saldo fictício insuficiente')
        self.book.cash = max(0,self.book.cash-margin-cost)  # normalize sub-cent floating-point residue
        self.book.fees_paid += cost
        pid = hashlib.sha256(f'{ts}:{mint}:{p.market}:{side}'.encode()).hexdigest()[:16]
        pos = Position(pid,p.market,side,qty,price,price*(1-side*p.stop_fraction),
                       price*(1+side*p.take_fraction),0 if p.market == 'spot' else margin,
                       ts,ts+p.horizon_bars*self.cfg.timeframe_seconds,p.strategy,cost,best_close=price,mint=mint)
        self.book.positions.append(pos)
        return dict(event='OPEN',position_id=pid,market=p.market,side=side,qty=qty,price=price,cost=cost)
    def close(self,pos,price,ts,reason):
        cost = self.costs(pos.qty*price)
        pnl = pos.side*pos.qty*(price-pos.entry)
        settlement = pos.qty*price if pos.market == 'spot' else max(0,pos.margin+pnl)
        # Isolated margin loss capped at collateral, unlike full protocol liquidation mechanics.
        if pos.market == 'perp' and pos.margin+pnl < 0:
            pnl = -pos.margin
        self.book.cash += settlement-cost
        self.book.fees_paid += cost
        realized = pnl-pos.entry_cost-cost-pos.funding_paid
        event = dict(event='CLOSE',position_id=pos.id,market=pos.market,mint=pos.mint,side=pos.side,
                     qty=pos.qty,entry=pos.entry,price=price,opened_at=pos.opened_at,
                     closed_at=ts,reason=reason,strategy=pos.strategy,net_pnl=realized,
                     funding_paid=pos.funding_paid,cost=cost)
        self.book.closed.append(event)
        self.book.total_closed += 1
        self.book.closed = self.book.closed[-200:]
        self.book.positions.remove(pos)
        if realized < 0:
            self.book.cooldown_until = max(self.book.cooldown_until,ts+self.cfg.cooldown_bars*self.cfg.timeframe_seconds)
        return event
    def on_bar(self,b):
        events = []
        for pos in list(self.book.positions):
            if pos.mint != b.mint:
                continue
            if pos.opened_at > b.timestamp:
                continue  # This bar includes prices observed before this position existed.
            if pos.market == 'perp' and b.funding_rate:
                funding = pos.side*pos.qty*b.open*b.funding_rate
                pos.margin -= funding
                pos.funding_paid += funding
                events.append(dict(event='FUNDING',position_id=pos.id,amount=funding))
            # Gap stops occur at open, followed by liquidation/stop/take within bar.
            adverse = b.low if pos.side == 1 else b.high
            liq = (pos.entry-pos.margin/pos.qty)/(1-self.cfg.maintenance_fraction) if pos.side == 1 else \
                  (pos.entry+pos.margin/pos.qty)/(1+self.cfg.maintenance_fraction)
            if pos.side*(b.open-pos.stop) <= 0:
                events.append(self.close(pos,b.open,b.timestamp,'gap_stop'))
            elif pos.market == 'perp' and pos.margin+pos.side*pos.qty*(b.open-pos.entry) <= pos.qty*b.open*self.cfg.maintenance_fraction:
                events.append(self.close(pos,b.open,b.timestamp,'liquidation_at_open_approx'))
            elif pos.market == 'perp' and pos.side*(liq-pos.stop) > 0 and pos.margin+pos.side*pos.qty*(adverse-pos.entry) <= pos.qty*adverse*self.cfg.maintenance_fraction:
                events.append(self.close(pos,liq,b.timestamp,'liquidation_approx'))
            elif pos.side*(adverse-pos.stop) <= 0:
                events.append(self.close(pos,pos.stop,b.timestamp,'stop'))
            elif pos.market == 'perp' and pos.margin+pos.side*pos.qty*(adverse-pos.entry) <= pos.qty*adverse*self.cfg.maintenance_fraction:
                events.append(self.close(pos,liq,b.timestamp,'liquidation_approx'))
            elif pos.side*((b.high if pos.side == 1 else b.low)-pos.take) >= 0:
                # Favorable gaps do not improve modeled take fill.
                events.append(self.close(pos,pos.take,b.timestamp,'take_profit'))
            elif b.timestamp >= pos.expires_at:
                events.append(self.close(pos,b.close,b.timestamp,'time_exit'))
        return events
    def on_mark(self,price,ts,mint=SOL):
        """Current observations can trigger exits, without inventing intrabar prices."""
        events = []
        for pos in list(self.book.positions):
            if pos.mint != mint or ts < pos.opened_at:
                continue
            reason = ('observed_stop' if pos.side*(price-pos.stop) <= 0 else
                      'observed_take' if pos.side*(price-pos.take) >= 0 else
                      'time_exit' if ts >= pos.expires_at else None)
            if reason:
                events.append(self.close(pos,price,ts,reason))
        return events
    def trail(self,price,atr,mint=SOL):
        for p in self.book.positions:
            if p.mint != mint:
                continue
            if p.side*(price-p.best_close) > 0:
                p.best_close = price
            candidate = p.best_close-p.side*atr*self.cfg.trailing_atr_multiple
            # Trailing stops updated after bar closes; apply only on subsequent bars.
            if p.side*(candidate-p.stop) > 0 and p.side*(price-candidate) > 0:
                p.stop = candidate
    def flatten(self,price,ts,reason,mint=None):
        return [self.close(p,price,ts,reason) for p in list(self.book.positions) if mint is None or p.mint == mint]
