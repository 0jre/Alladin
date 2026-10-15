"""Shared Coinbase spot paper ledger, two-phase intents and deterministic risk.

All network reads precede the SQLite write transaction. External sessions own
reasoning. This module never signs an exchange order or calls a model.
"""
from copy import deepcopy
from dataclasses import asdict
from decimal import Decimal, ROUND_DOWN
from datetime import datetime, timezone
import hashlib
import json
import math
import threading
import time
import uuid

from .instruments import product_id, size_order
from .spot_market import SpotMarket, entry_blocks, fresh, walk
from .spot_policy import SpotPolicy, dec, text
from .storage import Store, canonical
from .transport import DataError, deadline

D = Decimal


def identity(prefix):
    return prefix + '_' + uuid.uuid4().hex


def day(now):
    return datetime.fromtimestamp(now,timezone.utc).date().isoformat()


def correlation(a,b):
    n = min(len(a),len(b),64)
    if n < 30:
        return None
    a,b = a[-n:],b[-n:]
    am,bm = sum(a)/n,sum(b)/n
    den = math.sqrt(sum((x-am)**2 for x in a)*sum((x-bm)**2 for x in b))
    return sum((x-am)*(y-bm) for x,y in zip(a,b))/den if den else None


class SpotService:
    VERSION = 'coinbase-portfolio-v1'
    READS = {'list_products','catalog','instrument','instrument_book','get_market_snapshot',
             'get_orderbook','get_candles','scan_opportunities','get_session_brief','get_portfolio',
             'get_positions','get_risk_budget','get_fills','get_trade_journal','get_performance',
             'get_system_status','get_open_orders','get_order','get_fee_tier'}
    READS |= {'estimate_execution','get_microstructure','reconcile'}
    WRITES = {'log_thesis','propose_trade','commit_trade','close_position','set_protection',
              'halt_trading','halt','paper_tick','cancel_order','cancel_all'}

    def __init__(self,cfg,db_path,market=None,clock=time.time):
        self.cfg,self.store,self.clock = cfg,Store(db_path),clock
        self.market = market or SpotMarket(clock=clock)
        self.command_lock = threading.RLock()
        with self.store.transaction() as db:
            state = self.store.load(db)
            if state is None:
                state = dict(schema=self.VERSION,config_hash=cfg.fingerprint,policy=asdict(cfg),
                    execution='paper',balances={k:str(dec(v)) for k,v in cfg.initial_balances.items()},
                    positions={},theses={},proposals={},orders={},fills=[],revision=0,
                    peak=None,initial_equity=None,day=day(clock()),day_start_equity=None,
                    realized={},fees={},halted=False,halt_reason='',cooldown_until=0,
                    loss_streak=0,entry_times=[],last_timestamp=None,marks={},fx={},
                    legacy_closed_count=0,legacy_fees_paid='0')
                self.store.save(db,state)
                self.store.event(db,int(clock()),'portfolio_created',dict(execution='paper',policy=asdict(cfg)))
                postings=[]
                for currency,value in state['balances'].items():
                    postings.extend([dict(account='cash',currency=currency,amount=value),
                                     dict(account='opening_capital',currency=currency,amount=str(-dec(value)))])
                self._post(db,'portfolio_opening',postings,dict(origin='configured_initial_balances'))
            self._validate(state)

    def _validate(self,state):
        if state.get('schema') != self.VERSION:
            raise ValueError('LEGACY_ACCOUNT: explicitly migrate the flat legacy account; never replace its balance')
        if state.get('config_hash') != self.cfg.fingerprint:
            raise ValueError('POLICY_MISMATCH: use the account policy; changes require explicit operator migration')
        return state

    def _load(self,db):
        return self._validate(self.store.load(db))

    def _state(self):
        with self.store.connect() as db:
            return self._load(db)

    @classmethod
    def migrate(cls,cfg,path,legacy_cfg,clock=time.time):
        """Explicit flat-only upgrade. Preserve the exact legacy snapshot and seals."""
        store = Store(path)
        if not store.verify_audit()['valid']:
            raise ValueError('AUDIT_INVALID: migration refused')
        with store.transaction() as db:
            old = store.load(db)
            if old is None or old.get('schema') == cls.VERSION:
                raise ValueError('Migration requires an existing legacy account')
            p = old['portfolio']
            if p.get('positions') or old.get('pending') or old.get('execution_check') or old.get('pending_book'):
                raise ValueError('ACCOUNT_NOT_FLAT: settle legacy positions and pending activity first')
            if cfg.reporting_currency != 'USDC':
                raise ValueError('Legacy account reporting currency must remain USDC')
            # Never promote the original daily loss/drawdown limits in migration.
            from .engine import config_fingerprint
            if old['config_hash'] != config_fingerprint(legacy_cfg):
                raise ValueError('Legacy configuration does not match persisted fingerprint')
            original = asdict(legacy_cfg)
            for name in ('max_daily_loss','max_drawdown','risk_per_trade','max_open_risk'):
                if dec(getattr(cfg,name)) > dec(original[name]):
                    raise ValueError('Migration cannot increase '+name)
            archive = deepcopy(old)
            balances = {'USDC':str(dec(p['cash']))}
            now = clock()
            state = dict(schema=cls.VERSION,config_hash=cfg.fingerprint,policy=asdict(cfg),execution='paper',
                balances=balances,positions={},theses={},proposals={},orders={},fills=[],revision=0,
                peak=str(dec(p['peak'])),initial_equity=str(dec(p['initial'])),
                day=day(now),day_start_equity=str(dec(p['day_start_equity'])) if p.get('day') == day(now) else str(dec(p['cash'])),
                realized={},fees={},halted=p['halted'],halt_reason=p['halt_reason'],
                cooldown_until=p.get('cooldown_until',0),loss_streak=0,entry_times=[],last_timestamp=None,
                marks={},fx={},legacy_closed_count=p.get('total_closed',len(p.get('closed',[]))),
                legacy_fees_paid=str(dec(p.get('fees_paid',0))),legacy_snapshot=archive)
            store.save(db,state)
            store.event(db,int(now),'portfolio_migrated',dict(execution='paper',cash=balances,
                previous_config_hash=old['config_hash'],policy_hash=cfg.fingerprint,legacy_snapshot_sha256=hashlib.sha256(canonical(archive).encode()).hexdigest(),
                postings=[dict(account='cash',currency='USDC',amount=balances['USDC']),
                          dict(account='legacy_carry_forward',currency='USDC',amount=str(-dec(balances['USDC'])))]))
        return cls(cfg,path,clock=clock)

    def _collect(self,state,pid=None,observe=False):
        observations = {}
        books = {}
        instruments = {}
        if pid:
            if observe:
                observations[pid] = self.market.observation(pid,self.cfg.timeframe_seconds)
                instruments[pid] = observations[pid]['instrument']
                books[pid] = observations[pid]['book']
            else:
                instruments[pid] = self.market.instrument(pid)
                books[pid] = self.market.book(pid)
        for name,pos in state['positions'].items():
            if name not in books:
                books[name] = self.market.book(name)
            instruments.setdefault(name,pos['instrument'])
        currencies = set(state['balances']) | {p['quote_currency'] for p in state['positions'].values()}
        if pid:
            currencies.add(instruments[pid]['quote_currency_id'])
        fx = {self.cfg.reporting_currency:'1'}
        inverse_fx=set()
        needed = {c for c in currencies if c != self.cfg.reporting_currency and
                  (dec(state['balances'].get(c,0)) != 0 or any(p['quote_currency']==c for p in state['positions'].values()) or
                   (pid and instruments[pid]['quote_currency_id']==c))}
        if needed:
            catalog = self.market.catalog()['products']
            for currency in sorted(needed):
                direct = [r for r in catalog if r.get('product_type')=='SPOT' and r.get('base_currency_id')==currency and r.get('quote_currency_id')==self.cfg.reporting_currency]
                inverse = [r for r in catalog if r.get('product_type')=='SPOT' and r.get('quote_currency_id')==currency and r.get('base_currency_id')==self.cfg.reporting_currency]
                if direct:
                    b = self.market.book(direct[0]['product_id'])
                    fx[currency] = b['bid']
                elif inverse:
                    b = self.market.book(inverse[0]['product_id'])
                    fx[currency] = str(1/dec(b['ask']))
                    inverse_fx.add(currency)
                else:
                    raise DataError('FX_UNAVAILABLE: no Coinbase conversion book for '+currency)
                books['fx:'+currency] = b
        # Metadata/candle reads can be slow. Refresh early book observations
        # that aged during collection; never just restamp a cached quote.
        from .spot_market import stamp
        for name,book in list(books.items()):
            if self.clock()-stamp(book['source_time']) > max(1,self.cfg.max_snapshot_age_seconds-10):
                books[name]=self.market.book(book['product_id'])
        if pid and pid in observations:
            observations[pid]['book']=books[pid]
        for currency in needed:
            b=books['fx:'+currency]
            fx[currency]=str(1/dec(b['ask'])) if currency in inverse_fx else b['bid']
        return dict(books=books,instruments=instruments,observations=observations,fx=fx)

    def _fresh(self,data):
        for book in data['books'].values():
            fresh(book,self.clock(),self.cfg.max_snapshot_age_seconds)

    def _valuation(self,state,data):
        fx = data['fx']
        cash = sum((dec(value)*dec(fx[currency]) for currency,value in state['balances'].items() if dec(value)),D(0))
        gross = D(0)
        open_risk = D(0)
        for pid,p in state['positions'].items():
            price = dec(data['books'][pid]['bid'])
            value = price*dec(p['quantity'])*dec(fx[p['quote_currency']])
            gross += value
            open_risk += max(D(0),(price-dec(p['stop_price']))*dec(p['quantity'])*dec(fx[p['quote_currency']]))
            open_risk += value*dec(self.cfg.taker_fee_bps)/10000
        return cash+gross,gross,open_risk

    def _breakers(self,state,data):
        equity,gross,risk = self._valuation(state,data)
        if state['initial_equity'] is None:
            state['initial_equity'] = str(equity)
            state['peak'] = str(equity)
            state['day_start_equity'] = str(equity)
        if state['day'] != day(self.clock()):
            state['day'] = day(self.clock())
            state['day_start_equity'] = str(equity)
        state['peak'] = str(max(dec(state['peak']),equity))
        reason = ''
        if equity <= dec(state['day_start_equity'])*(1-dec(self.cfg.max_daily_loss)):
            reason = 'daily_loss_limit'
        if equity <= dec(state['peak'])*(1-dec(self.cfg.max_drawdown)):
            reason = 'drawdown_limit'
        if reason and not state['halted']:
            state.update(halted=True,halt_reason=reason,revision=state['revision']+1)
        return equity,gross,risk

    def _risk(self,state,data,plan,quantity=None):
        self._fresh(data)
        pid = plan['product_id']
        instrument = data['instruments'][pid]
        blocks = entry_blocks(instrument)
        if blocks:
            raise ValueError('PRODUCT_BLOCKED: '+','.join(blocks))
        equity,gross,open_risk = self._breakers(state,data)
        if state['halted'] or self.clock() < state['cooldown_until']:
            raise ValueError('REDUCE_ONLY: account is halted or cooling down')
        if equity <= 0:
            raise ValueError('NO_EQUITY: account has no available equity')
        if pid in state['positions'] or len(state['positions']) >= self.cfg.max_positions:
            raise ValueError('POSITION_LIMIT: duplicate product or position count limit')
        # Multiple quote pairs for the same base must not evade concentration.
        base,quote = instrument['base_currency_id'],instrument['quote_currency_id']
        if any(p['base_currency']==base for p in state['positions'].values()):
            raise ValueError('ASSET_ALREADY_HELD: use the existing base-asset position')
        book = data['books'][pid]
        ask,bid = dec(book['ask']),dec(book['bid'])
        if (ask-bid)/((ask+bid)/2)*10000 > dec(self.cfg.max_spread_bps):
            raise ValueError('SPREAD_LIMIT: spread is above policy')
        stop,target = dec(plan['stop_price']),dec(plan['take_profit_price'])
        if not stop < bid < ask < target:
            raise ValueError('INVALID_PROTECTION: require stop < bid < ask < target')
        if (ask-stop)/ask > D('.15') or (ask-stop)/ask < D('.001'):
            raise ValueError('STOP_DISTANCE: permitted stop distance is 0.1% to 15%')
        fx = dec(data['fx'][quote])
        obs = data['observations'].get(pid)
        if obs is None:
            raise ValueError('EVIDENCE_REQUIRED: entry needs current candles and volume')
        if dec(obs['volume_24h_quote'])*fx < dec(self.cfg.min_volume_24h):
            raise ValueError('VOLUME_LIMIT: insufficient completed market evidence')
        if self.clock()-obs['last_closed_at'] > obs.get('timeframe_seconds',self.cfg.timeframe_seconds):
            raise DataError('STALE_CANDLES: refresh entry context')
        fee = dec(self.cfg.taker_fee_bps)/10000
        slip = dec(self.cfg.max_slippage_bps)/10000
        unit_loss = (ask*(1+slip)-stop*(1-slip)+ask*fee+stop*fee)*fx
        requested = min(dec(plan['risk_fraction']),dec(self.cfg.risk_per_trade))
        daily_left = equity-dec(state['day_start_equity'])*(1-dec(self.cfg.max_daily_loss))
        dd_left = equity-dec(state['peak'])*(1-dec(self.cfg.max_drawdown))
        risk_left = min(equity*requested,equity*dec(self.cfg.max_open_risk)-open_risk,daily_left-open_risk,dd_left-open_risk)
        cash = dec(state['balances'].get(quote,0))
        cap = min(cash/(ask*(1+slip)*(1+fee)),
                  dec(instrument['base_max_size'],'base_max_size',D('1e-25')),
                  dec(instrument['quote_max_size'],'quote_max_size',D('1e-25'))/(ask*(1+slip)),
                  max(D(0),equity*dec(self.cfg.max_position_fraction))/(ask*fx),
                  max(D(0),equity*dec(self.cfg.max_gross_fraction)-gross)/(ask*fx),
                  max(D(0),risk_left)/unit_loss,
                  dec(obs['volume_24h_quote'])*dec(self.cfg.max_participation)/ask)
        for key,limit in [('agent_id',self.cfg.max_agent_fraction),('strategy',self.cfg.max_strategy_fraction)]:
            exposure = sum((dec(p['quantity'])*dec(data['books'][name]['bid'])*dec(data['fx'][p['quote_currency']])
                            for name,p in state['positions'].items() if p[key]==plan[key]),D(0))
            cap = min(cap,max(D(0),equity*dec(limit)-exposure)/(ask*fx))
        correlated = D(0)
        for name,p in state['positions'].items():
            rho = (correlation(obs['features']['returns'],p.get('returns',[]))
                   if p.get('returns_closed_at')==obs['last_closed_at'] else None)
            # Missing evidence is conservative, not an invented zero correlation.
            if rho is None or abs(rho) >= float(dec(self.cfg.correlation_threshold)):
                correlated += dec(p['quantity'])*dec(data['books'][name]['bid'])*dec(data['fx'][p['quote_currency']])
        cap = min(cap,max(D(0),equity*dec(self.cfg.max_correlated_fraction)-correlated)/(ask*fx))
        if quantity is not None:
            if dec(quantity) > cap:
                raise ValueError('RISK_CHANGED: prepared quantity exceeds current shared budget; propose again')
            cap = dec(quantity)
        else:
            cap *= D('.98')  # reserve room for drift; commit never increases size
        qty = dec(size_order(instrument,cap))
        limit = dec(plan['limit_price']) if plan['order_type']=='LIMIT_IOC' else None
        fill = walk(book,'BUY',qty,self.cfg.taker_fee_bps,self.cfg.max_slippage_bps,self.cfg.price_collar_bps,limit)
        if dec(fill['unfilled']) and plan['partial_fill_policy']=='REJECT':
            raise ValueError('INSUFFICIENT_DEPTH: full quantity is not executable')
        qty = dec(size_order(instrument,fill['quantity']))
        fill = walk(book,'BUY',qty,self.cfg.taker_fee_bps,self.cfg.max_slippage_bps,self.cfg.price_collar_bps,limit)
        notional = dec(fill['quote_notional'])
        for field,op in [('quote_min_size','min'),('quote_max_size','max')]:
            boundary = dec(instrument[field],field,D('1e-25'))
            if (op=='min' and notional<boundary) or (op=='max' and notional>boundary):
                raise ValueError('QUOTE_SIZE_LIMIT: order outside Coinbase notional limits')
        cost = dec(fill['fee'])
        vwap = dec(fill['vwap'])
        loss = (vwap-stop*(1-slip))*qty+cost+stop*qty*fee
        reward = (target*(1-slip)-vwap)*qty-cost-target*qty*fee
        if loss <= 0 or reward/loss < dec(self.cfg.min_reward_risk):
            raise ValueError('NET_REWARD_RISK: target does not cover spread, fees and stressed exit')
        now = self.clock()
        times = state['entry_times']
        if sum(t>now-60 for t in times)>=self.cfg.max_orders_per_minute or sum(t>now-86400 for t in times)>=self.cfg.max_orders_per_day:
            raise ValueError('ORDER_RATE_LIMIT: wait; do not loop new proposals')
        return dict(fill=fill,quantity=str(qty),estimated_loss_reporting=str(loss*fx),net_reward_risk=str(reward/loss),
                    equity=str(equity),quote_currency=quote,base_currency=base,reporting_currency=self.cfg.reporting_currency)

    def _post(self,db,kind,postings,metadata):
        totals = {}
        for posting in postings:
            c = posting['currency']
            totals[c] = totals.get(c,D(0))+dec(posting['amount'])
        if any(totals.values()):
            raise RuntimeError('Unbalanced accounting transaction')
        self.store.event(db,int(self.clock()),kind,dict(execution='paper',postings=postings,**metadata))

    def _entry(self,db,state,data,proposal,approval):
        plan = proposal['plan']
        pid = plan['product_id']
        qty = dec(approval['quantity'])
        fill = approval['fill']
        from .execution_core import fill as native_fill
        fill=native_fill(self.cfg,state,data['instruments'][pid],data['books'][pid],'BUY',qty,
                         proposal['id'],fill,dec(plan['limit_price']) if plan['order_type']=='LIMIT_IOC' else None)
        self._fresh(data)
        if self.clock()>proposal['expires_at']:
            raise ValueError('PROPOSAL_EXPIRED: native execution completed too late; no ledger fill committed')
        quote,base = approval['quote_currency'],approval['base_currency']
        notional,fee = dec(fill['quote_notional']),dec(fill['fee'])
        state['balances'][quote] = str(dec(state['balances'].get(quote,0))-notional-fee)
        if dec(state['balances'][quote]) < 0:
            raise RuntimeError('Negative balance after risk approval')
        position = dict(id=identity('pos'),product_id=pid,base_currency=base,quote_currency=quote,
            quantity=str(qty),entry_price=fill['vwap'],cost_basis=str(notional),entry_fee=str(fee),
            stop_price=plan['stop_price'],take_profit_price=plan['take_profit_price'],
            trailing_fraction=plan.get('trailing_fraction'),high_water=fill['vwap'],
            opened_at=self.clock(),expires_at=self.clock()+plan['horizon_seconds'],
            agent_id=plan['agent_id'],strategy=plan['strategy'],thesis_id=plan['thesis_id'],
            purpose=plan.get('purpose','strategy'),
            returns=data['observations'][pid]['features']['returns'],
            returns_closed_at=data['observations'][pid]['last_closed_at'],instrument=data['instruments'][pid])
        state['positions'][pid] = position
        state['fees'][quote] = str(dec(state['fees'].get(quote,0))+fee)
        order = dict(id=identity('ord'),client_order_id=proposal['id'],product_id=pid,side='BUY',
            status='PARTIALLY_FILLED_CANCELLED' if qty<dec(proposal['approval']['quantity']) else 'FILLED',
            quantity=str(qty),price=fill['vwap'],fee=str(fee),timestamp=self.clock(),position_id=position['id'],
            thesis_id=plan['thesis_id'],purpose=plan.get('purpose','strategy'),execution='paper',
            engine=fill['engine'],engine_version=fill['engine_version'],native_fills=fill.get('native_fills',[]))
        state['orders'][order['id']] = order
        state['fills'].append(order)
        state['entry_times'] = [t for t in state['entry_times'] if t>self.clock()-86400]+[self.clock()]
        state['revision'] += 1
        proposal.update(status='COMMITTED',order_id=order['id'])
        postings = [dict(account='cash',currency=quote,amount=str(-notional-fee)),
                    dict(account='inventory_cost:'+position['id'],currency=quote,amount=str(notional)),
                    dict(account='fees',currency=quote,amount=str(fee)),
                    dict(account='inventory:'+position['id'],currency=base,amount=str(qty)),
                    dict(account='clearing',currency=base,amount=str(-qty))]
        self._post(db,'spot_entry',postings,dict(order=order,approval=approval,proposal_id=proposal['id']))
        return dict(result='filled',execution='paper',order=order,position=position)

    def _exit(self,db,state,data,pid,fraction=D(1),reason='external_close'):
        self._fresh(data)
        pos = state['positions'][pid]
        instrument = pos['instrument']
        requested = dec(pos['quantity'])*fraction
        qty = dec(size_order(instrument,requested))
        fill = walk(data['books'][pid],'SELL',qty,self.cfg.taker_fee_bps,
                    self.cfg.max_slippage_bps,self.cfg.price_collar_bps)
        qty = dec(size_order(instrument,fill['quantity']))
        fill = walk(data['books'][pid],'SELL',qty,self.cfg.taker_fee_bps,
                    self.cfg.max_slippage_bps,self.cfg.price_collar_bps)
        from .execution_core import fill as native_fill
        fill=native_fill(self.cfg,state,instrument,data['books'][pid],'SELL',qty,identity('close'),fill)
        self._fresh(data)
        ratio = qty/dec(pos['quantity'])
        basis,entry_fee = dec(pos['cost_basis'])*ratio,dec(pos['entry_fee'])*ratio
        proceeds,fee = dec(fill['quote_notional']),dec(fill['fee'])
        pnl = proceeds-fee-basis-entry_fee
        quote,base = pos['quote_currency'],pos['base_currency']
        state['balances'][quote] = str(dec(state['balances'].get(quote,0))+proceeds-fee)
        state['realized'][quote] = str(dec(state['realized'].get(quote,0))+pnl)
        state['fees'][quote] = str(dec(state['fees'].get(quote,0))+fee)
        pos['quantity'] = str(dec(pos['quantity'])-qty)
        pos['cost_basis'] = str(dec(pos['cost_basis'])-basis)
        pos['entry_fee'] = str(dec(pos['entry_fee'])-entry_fee)
        complete = dec(pos['quantity'])==0
        if complete:
            del state['positions'][pid]
        if pnl < 0:
            state['loss_streak'] += 1
            state['cooldown_until'] = max(state['cooldown_until'],self.clock()+self.cfg.cooldown_seconds)
        else:
            state['loss_streak'] = 0
        if state['loss_streak'] >= self.cfg.max_consecutive_losses:
            state.update(halted=True,halt_reason='consecutive_loss_limit')
        order = dict(id=identity('ord'),client_order_id=identity('close'),product_id=pid,side='SELL',
            status='FILLED' if complete else 'PARTIALLY_FILLED_CANCELLED',quantity=str(qty),price=fill['vwap'],
            fee=str(fee),realized_pnl=str(pnl),quote_currency=quote,timestamp=self.clock(),position_id=pos['id'],
            thesis_id=pos['thesis_id'],purpose=pos.get('purpose','strategy'),reason=reason,execution='paper',
            engine=fill['engine'],engine_version=fill['engine_version'],native_fills=fill.get('native_fills',[]))
        state['orders'][order['id']] = order
        state['fills'].append(order)
        state['revision'] += 1
        postings = [dict(account='cash',currency=quote,amount=str(proceeds-fee)),
                    dict(account='inventory_cost:'+pos['id'],currency=quote,amount=str(-basis)),
                    dict(account='fees',currency=quote,amount=str(fee)),
                    dict(account='realized_gross_pnl',currency=quote,amount=str(basis-proceeds)),
                    dict(account='inventory:'+pos['id'],currency=base,amount=str(-qty)),
                    dict(account='clearing',currency=base,amount=str(qty))]
        self._post(db,'spot_exit',postings,dict(order=order))
        return dict(result='closed' if complete else 'partially_closed',execution='paper',order=order)

    def status(self):
        state = self._state()
        equity=dec(state.get('equity',state['initial_equity'] or 0))
        daily_left=max(D(0),equity-dec(state['day_start_equity'] or equity)*(1-dec(self.cfg.max_daily_loss)))
        risk_left=max(D(0),equity*dec(self.cfg.max_open_risk)-dec(state.get('open_risk',0)))
        return dict(execution='paper',backend='portfolio',schema=self.VERSION,agent_mode='external',
            execution_engine=self.cfg.execution_engine,
            product_scope='coinbase_spot',balances=state['balances'],reporting_currency=self.cfg.reporting_currency,
            positions=list(state['positions'].values()),halted=state['halted'],halt_reason=state['halt_reason'],
            cooldown_until=state['cooldown_until'],last_timestamp=state['last_timestamp'],
            last_decision=None,equity_reporting=state.get('equity'),valuation_observed_at=state['last_timestamp'],
            valuation_stale=state['last_timestamp'] is None or self.clock()-state['last_timestamp']>self.cfg.max_snapshot_age_seconds,
            fees_by_currency=state['fees'],realized_pnl_by_currency=state['realized'],
            policy=asdict(self.cfg),revision=state['revision'],legacy_closed_count=state['legacy_closed_count'],
            budget=dict(equity_reporting=str(equity),remaining_daily_loss_reporting=str(daily_left),
                        remaining_open_risk_reporting=str(risk_left),gross_reporting=state.get('gross'),
                        stale=state['last_timestamp'] is None or self.clock()-state['last_timestamp']>self.cfg.max_snapshot_age_seconds))

    def performance(self):
        s = self._state()
        all_closed = [x for x in s['fills'] if x['side']=='SELL']
        closed = [x for x in all_closed if x.get('purpose')!='execution_validation']
        return dict(execution='paper',sell_fills=len(closed),wins=sum(dec(x['realized_pnl'])>0 for x in closed),
                    realized_pnl_by_currency=s['realized'],fees_by_currency=s['fees'],
                    open_positions=len(s['positions']),legacy_closed_count=s['legacy_closed_count'],
                    execution_validation_sell_fills=len(all_closed)-len(closed),
                    interpretation='Observed paper fills, including partial closes; not a profitability guarantee.')

    def diagnostics(self):
        return dict(execution='paper',backend='portfolio',status=self.status(),audit=self.store.verify_audit())

    def command(self,name,args,key):
        if not isinstance(args,dict) or name not in self.READS|self.WRITES:
            raise ValueError('Unknown portfolio command or invalid arguments')
        if name in self.READS:
            with deadline(120):
                return self._read(name,args)
        request = dict(backend=self.VERSION,command=name,args=args)
        with self.store.connect() as db:
            old = self.store.lookup(db,key,request)
            if old is not None:
                return old
        with deadline(120):
            return self._write(name,args,key,request)

    @staticmethod
    def _args(args,required=(),optional=()):
        if not set(required)<=set(args) or not set(args)<=set(required)|set(optional):
            raise ValueError('Invalid fields; required='+','.join(required))
        if 'dry_run' in args and type(args['dry_run']) is not bool:
            raise ValueError('dry_run must be boolean')

    def _read(self,name,args):
        if name=='reconcile':
            self._args(args)
            with self.store.connect() as db:
                return self._reconcile(db,self._load(db))
        if name in {'estimate_execution','get_microstructure'}:
            self._args(args,('product_id','quote_budget') if name=='estimate_execution' else ('product_id',))
            book=self.market.book(product_id(args['product_id']))
            if name=='estimate_execution':
                instrument=self.market.instrument(args['product_id'])
                qty=size_order(instrument,dec(args['quote_budget'],'quote_budget',D('1e-25'))/dec(book['ask']))
                result=walk(book,'BUY',qty,self.cfg.taker_fee_bps,self.cfg.max_slippage_bps,self.cfg.price_collar_bps)
                return dict(execution='paper',estimate=result,source_time=book['source_time'],execution_authorized=False)
            bids=sum((dec(x['size'])*dec(x['price']) for x in book['pricebook']['bids']),D(0))
            asks=sum((dec(x['size'])*dec(x['price']) for x in book['pricebook']['asks']),D(0))
            return dict(execution='paper',book_imbalance=str((bids-asks)/(bids+asks)),
                        bid_depth_quote=str(bids),ask_depth_quote=str(asks),trade_flow_available=False,
                        source_time=book['source_time'],note='Visible L2 imbalance is not taker trade flow.')
        if name in {'get_session_brief','get_portfolio','get_positions','get_risk_budget','get_system_status','get_performance','get_fee_tier','get_fills','get_trade_journal','get_open_orders'}:
            self._args(args)
            if name == 'get_fee_tier':
                return dict(execution='paper',taker_fee_bps=self.cfg.taker_fee_bps,source='configured_assumption',account_tier_verified=False)
            if name == 'get_performance':
                return self.performance()
            s = self._state()
            if name == 'get_open_orders':
                return dict(execution='paper',orders=[],note='IOC remainder is cancelled; no resting orders are simulated')
            if name in {'get_fills','get_trade_journal'}:
                return dict(execution='paper',fills=s['fills'][-100:],theses=list(s['theses'].values())[-100:])
            if name == 'get_positions':
                return dict(execution='paper',positions=list(s['positions'].values()))
            return self.status()
        if name == 'get_order':
            self._args(args,('order_id',))
            return dict(execution='paper',order=self._state()['orders'][args['order_id']])
        if name in {'catalog','list_products'}:
            self._args(args,optional=('refresh','quote_currency','limit','offset'))
            result = self.market.catalog(args.get('refresh',False))
            products = []
            for row in result['products']:
                if args.get('quote_currency') and row.get('quote_currency_id') != args['quote_currency']:
                    continue
                row = deepcopy(row)
                row['alladin_capabilities'] = dict(catalog=True,paper_execution=not entry_blocks(row),
                    execution_adapter='spot' if row.get('product_type')=='SPOT' else None,
                    live_execution=False,execution_blocks=entry_blocks(row),account_eligibility='unverified')
                products.append(row)
            offset,limit = args.get('offset',0),args.get('limit',100)
            if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=500:
                raise ValueError('Invalid catalog pagination')
            return dict(execution='paper',products=products[offset:offset+limit],total=len(products),
                        next_offset=offset+limit if offset+limit<len(products) else None,
                        catalog_sha256=result['catalog_sha256'],observed_at=result['observed_at'])
        if name in {'instrument','instrument_book','get_orderbook','get_market_snapshot','get_candles'}:
            self._args(args,('product_id',))
            pid = product_id(args['product_id'])
            if name=='instrument':
                r=self.market.instrument(pid)
                r['alladin_capabilities']=dict(paper_execution=not entry_blocks(r),execution_blocks=entry_blocks(r),live_execution=False)
            elif name in {'instrument_book','get_orderbook'}:
                r=self.market.book(pid)
            elif name=='get_candles':
                r=dict(product_id=pid,timeframe_seconds=self.cfg.timeframe_seconds,candles=[vars(x) for x in self.market.candles(pid,self.cfg.timeframe_seconds)])
            else:
                r=self.market.observation(pid,self.cfg.timeframe_seconds)
            return dict(execution='paper',data=r)
        if name=='scan_opportunities':
            return self._scan(args)
        raise ValueError('Unknown read command')

    def _scan(self,args):
        self._args(args,optional=('limit','product_ids'))
        limit=args.get('limit',self.cfg.max_scan_products)
        if type(limit) is not int or not 1<=limit<=self.cfg.max_scan_products:
            raise ValueError('Scan limit exceeds policy')
        explicit=args.get('product_ids')
        if explicit is not None and (not isinstance(explicit,list) or not 1<=len(explicit)<=limit):
            raise ValueError('product_ids must be a bounded list')
        s=self._state()
        if explicit is not None:
            requested={product_id(p) for p in explicit}
            products=[self.market.instrument(pid) for pid in sorted(requested)]
        else:
            products=self.market.catalog()['products']
        eligible=[p for p in products if not entry_blocks(p)]
        def priority(p):
            # Prefer funded quotes, then momentum and activity. No hardcoded
            # token or meme list; low-liquidity pumps are not automatically buys.
            try:
                move=dec(str(p.get('price_percentage_change_24h','0')).rstrip('%'))
                volume=dec(p.get('volume_24h','0'),minimum=0)*dec(p.get('price','0'),minimum=0)
                return (dec(s['balances'].get(p['quote_currency_id'],0))>0,move>0,float(min(abs(move),D(50))),float(volume))
            except ValueError:
                return (False,False,0,0)
        eligible.sort(key=priority,reverse=True)
        # Diversify base assets even when Coinbase lists quote aliases.
        chosen,seen=[],set()
        for p in eligible:
            if p['base_currency_id'] in seen:
                continue
            chosen.append(p);seen.add(p['base_currency_id'])
            if len(chosen)>=limit:
                break
        rows=[]
        for p in chosen:
            pid=p['product_id']
            try:
                obs=self.market.observation(pid,self.cfg.timeframe_seconds)
                f=obs['features'];ask=dec(obs['book']['ask']);bid=dec(obs['book']['bid'])
                atr=dec(f['atr']);fee=dec(self.cfg.taker_fee_bps)/10000
                stop=max(ask*D('.85'),min(bid*D('.999'),ask-atr*2))
                target=ask+atr*4
                loss=ask-stop+ask*fee+stop*fee
                reward=target-ask-ask*fee-target*fee
                rr=reward/loss if loss>0 else D(0)
                blocks=[]
                if f['ema_gap']<=0 or f['momentum_12']<=0:blocks.append('no_positive_trend')
                if f['rsi']>75:blocks.append('overextended_rsi')
                if f['regime']=='shock':blocks.append('volatility_shock')
                if dec(obs['spread_bps'])>dec(self.cfg.max_spread_bps):blocks.append('spread_limit')
                if rr<dec(self.cfg.min_reward_risk):blocks.append('costs_consume_target')
                if dec(s['balances'].get(p['quote_currency_id'],0))<=0:blocks.append('quote_currency_not_funded')
                if s['halted'] or self.clock()<s['cooldown_until']:blocks.append('account_reduce_only')
                if p['quote_currency_id']==self.cfg.reporting_currency and dec(obs['volume_24h_quote'])<dec(self.cfg.min_volume_24h):blocks.append('volume_limit')
                score=(max(-1,min(1,f['momentum_12']*20))*30+max(-1,min(1,f['ema_gap']*50))*25+
                       min(f['volume_ratio'],3)*10+f['efficiency']*20-f['atr_fraction']*100-dec(obs['spread_bps']).__float__()/5)
                rows.append(dict(product_id=pid,score=score,eligible_for_proposal=not blocks,blocks=blocks,
                    stop_price=str(stop),take_profit_price=str(target),net_reward_risk_scenario=str(rr),
                    quote_currency=p['quote_currency_id'],features=f,spread_bps=obs['spread_bps'],
                    timeframe_seconds=obs.get('timeframe_seconds',self.cfg.timeframe_seconds),
                    observed_at=obs['book']['source_time'],interpretation='Advisory continuation scenario, not predicted profit or a probability'))
            except (DataError,ValueError,KeyError) as exc:
                rows.append(dict(product_id=pid,eligible_for_proposal=False,blocks=['data_unavailable'],error=str(exc)[:200],score=-1000))
        rows.sort(key=lambda x:(x['eligible_for_proposal'],x['score']),reverse=True)
        return dict(execution='paper',candidates=rows,scanned=len(rows),catalog_count=len(products),
                    automatic_execution=False,selection='funded quotes, positive 24h change, then technical confirmation; bounded subset',
                    note='External session decides. No token class guarantees profit; proposal revalidates all shared risk.')

    def _write(self,name,args,key,request):
        s=self._state()
        data=None
        if name=='log_thesis':
            self._args(args,('product_id','agent_id','strategy','thesis','invalidation','horizon_seconds'),('dry_run','purpose'))
            if args.get('purpose','strategy') not in ('strategy','execution_validation'):
                raise ValueError('Invalid thesis purpose')
            product_id(args['product_id'])
            for k in ('agent_id','strategy','thesis','invalidation'):text(args[k],k,2000 if k in ('thesis','invalidation') else 100)
            if type(args['horizon_seconds']) is not int or not 60<=args['horizon_seconds']<=604800:
                raise ValueError('horizon_seconds must be between 60 and 604800')
        elif name=='propose_trade':
            self._args(args,('thesis_id','stop_price','take_profit_price','risk_fraction'),
                       ('order_type','limit_price','partial_fill_policy','trailing_fraction','dry_run'))
            thesis=s['theses'].get(args['thesis_id'])
            if thesis is None:raise ValueError('THESIS_REQUIRED: log_thesis first')
            for k in ('stop_price','take_profit_price'):dec(args[k],k,D('1e-25'))
            dec(args['risk_fraction'],'risk_fraction',D('0.000001'),dec(self.cfg.risk_per_trade))
            if args.get('order_type','MARKET_IOC') not in ('MARKET_IOC','LIMIT_IOC'):raise ValueError('Only MARKET_IOC and LIMIT_IOC paper orders are supported')
            if args.get('partial_fill_policy','REJECT') not in ('ACCEPT','REJECT'):raise ValueError('Unknown partial fill policy')
            if args.get('order_type')=='LIMIT_IOC':dec(args.get('limit_price'),'limit_price',D('1e-25'))
            elif 'limit_price' in args:raise ValueError('limit_price requires LIMIT_IOC')
            if 'trailing_fraction' in args:dec(args['trailing_fraction'],'trailing_fraction',D('.001'),D('.15'))
            data=self._collect(s,thesis['product_id'],True)
        elif name=='commit_trade':
            self._args(args,('proposal_id',),('dry_run',))
            proposal=s['proposals'].get(args['proposal_id'])
            if proposal is None:raise ValueError('UNKNOWN_PROPOSAL: propose_trade first')
            if proposal['status']=='COMMITTED':
                with self.store.transaction() as db:
                    current=self._load(db)
                    def duplicate():
                        return dict(result='already_committed',execution='paper',order=current['orders'][current['proposals'][args['proposal_id']]['order_id']])
                    return self.store.once(db,key,request,duplicate)
            self._proposal_current(s,proposal)
            data=self._collect(s,proposal['plan']['product_id'],True)
        elif name in ('close_position','set_protection'):
            self._args(args,('product_id',),('fraction','dry_run') if name=='close_position' else ('stop_price','take_profit_price','trailing_fraction','dry_run'))
            pid=product_id(args['product_id'])
            if pid not in s['positions']:raise ValueError('POSITION_NOT_FOUND')
            if name=='close_position':dec(args.get('fraction','1'),'fraction',D('.000001'),1)
            data=self._collect(s,pid)
        elif name=='paper_tick':
            self._args(args)
            data=self._collect(s)
        elif name in ('halt','halt_trading','cancel_all'):
            self._args(args,optional=('dry_run',))
        elif name=='cancel_order':
            self._args(args,('proposal_id',),('dry_run',))
        with self.store.transaction() as db:
            current=self._load(db)
            old=self.store.lookup(db,key,request)
            if old is not None:return old
            if name in {'propose_trade','commit_trade'} and not self._reconcile(db,current)['valid']:
                raise ValueError('RECONCILIATION_DRIFT: ledger and state disagree; new entries blocked')
            if data is not None:
                # A concurrent mutation invalidates the pre-I/O account view.
                if current['revision']!=s['revision']:
                    raise ValueError('CONTEXT_CHANGED: account changed during collection; retry same request')
                self._fresh(data)
            def apply():
                nonlocal current
                dry=args.get('dry_run',False)
                state=deepcopy(current) if dry else current
                result=self._apply(db,state,name,args,data,dry)
                if not dry:
                    self.store.save(db,state)
                    self.store.event(db,int(self.clock()),'portfolio_command',dict(command=name,result=result,execution='paper'))
                return result
            return self.store.once(db,key,request,apply)

    def _proposal_current(self,s,p):
        if p['status']!='PROPOSED' or self.clock()>p['expires_at'] or s['revision']!=p['revision']:
            raise ValueError('PROPOSAL_EXPIRED_OR_INVALIDATED: prepare a new proposal')

    def _reconcile(self,db,state):
        cash={}
        inventory={}
        balanced=True
        for (payload,) in db.execute('SELECT payload FROM events ORDER BY seq'):
            event=json.loads(payload)
            totals={}
            for p in event.get('postings',[]):
                currency,amount=p['currency'],dec(p['amount'])
                totals[currency]=totals.get(currency,D(0))+amount
                if p['account']=='cash':cash[currency]=cash.get(currency,D(0))+amount
                if p['account'].startswith('inventory:'):
                    name=p['account'].split(':',1)[1]
                    inventory[name]=inventory.get(name,D(0))+amount
            balanced=balanced and not any(totals.values())
        actual={k:dec(v) for k,v in state['balances'].items()}
        cash_ok=all(cash.get(k,D(0))==actual.get(k,D(0)) for k in set(cash)|set(actual))
        positions={p['id']:dec(p['quantity']) for p in state['positions'].values()}
        inventory_ok=all(inventory.get(k,D(0))==positions.get(k,D(0)) for k in set(inventory)|set(positions))
        return dict(execution='paper',valid=balanced and cash_ok and inventory_ok,
                    cash_matches=cash_ok,positions_match=inventory_ok,balanced_postings=balanced,
                    exchange_reconciliation=False,note='Internal paper ledger reconciliation; no exchange account is connected.')

    def _apply(self,db,s,name,args,data,dry):
        if name=='log_thesis':
            thesis={k:v for k,v in args.items() if k!='dry_run'}
            thesis.update(id=identity('th'),created_at=self.clock())
            if not dry:s['theses'][thesis['id']]=thesis
            return dict(result='thesis_logged' if not dry else 'dry_run',execution='paper',thesis=thesis)
        if name=='propose_trade':
            thesis=s['theses'][args['thesis_id']]
            plan={**thesis,**{k:v for k,v in args.items() if k!='dry_run'}}
            plan.update(order_type=args.get('order_type','MARKET_IOC'),partial_fill_policy=args.get('partial_fill_policy','REJECT'))
            approval=self._risk(s,data,plan)
            p=dict(id=identity('pr'),plan=plan,approval=approval,revision=s['revision'],created_at=self.clock(),
                expires_at=self.clock()+self.cfg.proposal_ttl_seconds,status='PROPOSED',reference_ask=data['books'][plan['product_id']]['ask'],
                evidence_sha256=hashlib.sha256(canonical(data['observations'][plan['product_id']]).encode()).hexdigest())
            if not dry:
                # Keep old committed proposals for duplicate detection. Expire
                # unused proposals rather than renewing their authority.
                for old in s['proposals'].values():
                    if old['status']=='PROPOSED' and old['expires_at']<self.clock():old['status']='EXPIRED'
                s['proposals'][p['id']]=p
                self.store.event(db,int(self.clock()),'spot_proposal_evidence',dict(
                    proposal_id=p['id'],evidence=data['observations'][plan['product_id']],
                    evidence_sha256=p['evidence_sha256'],policy_sha256=self.cfg.fingerprint,
                    account_revision=s['revision'],execution='paper'))
            return dict(result='proposed' if not dry else 'dry_run',execution='paper',proposal=p)
        if name=='commit_trade':
            p=s['proposals'][args['proposal_id']]
            if p['status']=='COMMITTED':return dict(result='already_committed',execution='paper',order=s['orders'][p['order_id']])
            self._proposal_current(s,p)
            ask=dec(data['books'][p['plan']['product_id']]['ask'])
            if abs(ask/dec(p['reference_ask'])-1)*10000>dec(self.cfg.max_quote_drift_bps):
                raise ValueError('PRICE_MOVED: proposal quote drift exceeds policy; propose again')
            approval=self._risk(s,data,p['plan'],p['approval']['quantity'])
            # Check TTL after final validation as well as before collection.
            self._proposal_current(s,p)
            if dry:return dict(result='dry_run',execution='paper',approval=approval)
            result=self._entry(db,s,data,p,approval)
            self._observe_state(s,data)
            return result
        if name=='close_position':
            if dry:
                pos=s['positions'][args['product_id']]
                qty=size_order(pos['instrument'],dec(pos['quantity'])*dec(args.get('fraction','1')))
                estimate=walk(data['books'][args['product_id']],'SELL',qty,self.cfg.taker_fee_bps,self.cfg.max_slippage_bps,self.cfg.price_collar_bps)
                return dict(result='dry_run',execution='paper',estimate=estimate,position=pos)
            result=self._exit(db,s,data,args['product_id'],dec(args.get('fraction','1')))
            self._observe_state(s,data)
            return result
        if name=='set_protection':
            p=s['positions'][args['product_id']]
            bid=dec(data['books'][args['product_id']]['bid'])
            stop=dec(args.get('stop_price',p['stop_price']),'stop_price',D('1e-25'))
            target=dec(args.get('take_profit_price',p['take_profit_price']),'take_profit_price',D('1e-25'))
            if stop<dec(p['stop_price']) or not stop<bid<target:
                raise ValueError('PROTECTION_RISK_INCREASE: stop can only tighten below current bid')
            if 'trailing_fraction' in args:
                trail=dec(args['trailing_fraction'],'trailing_fraction',D('.001'),D('.15'))
                if p.get('trailing_fraction') and trail>dec(p['trailing_fraction']):raise ValueError('Trailing protection cannot loosen')
                p['trailing_fraction']=str(trail)
            p.update(stop_price=str(stop),take_profit_price=str(target))
            s['revision']+=1
            return dict(result='dry_run' if dry else 'protection_updated',execution='paper',position=p,
                        protection_type='backend_observed_paper; requires running worker')
        if name in ('halt','halt_trading'):
            s.update(halted=True,halt_reason='operator_halt',revision=s['revision']+1)
            for p in s['proposals'].values():
                if p['status']=='PROPOSED':p['status']='CANCELLED'
            return dict(result='dry_run' if dry else 'halted',execution='paper',positions_left_open=len(s['positions']),reduce_only=True)
        if name in ('cancel_order','cancel_all'):
            proposals=s['proposals'].values() if name=='cancel_all' else [s['proposals'][args['proposal_id']]]
            for p in proposals:
                if p['status']=='PROPOSED':p['status']='CANCELLED'
                elif name=='cancel_order':raise ValueError('Only an uncommitted proposal can be cancelled')
            return dict(result='dry_run' if dry else 'cancelled',execution='paper')
        if name=='paper_tick':
            self._breakers(s,data)
            events=[]
            for pid,p in list(s['positions'].items()):
                bid=dec(data['books'][pid]['bid'])
                high=max(dec(p['high_water']),bid)
                if p.get('trailing_fraction'):
                    p['stop_price']=str(max(dec(p['stop_price']),high*(1-dec(p['trailing_fraction']))))
                p['high_water']=str(high)
                reason=''
                if bid<=dec(p['stop_price']):reason='observed_stop'
                elif bid>=dec(p['take_profit_price']):reason='observed_target'
                elif self.clock()>=p['expires_at']:reason='time_exit'
                if reason:events.append(self._exit(db,s,data,pid,reason=reason))
            self._observe_state(s,data)
            return dict(result='portfolio_observed',execution='paper',events=events,equity=s['equity'],positions=len(s['positions']))
        raise ValueError('Unknown write command')

    def _observe_state(self,s,data):
        equity,gross,risk=self._breakers(s,data)
        s.update(equity=str(equity),gross=str(gross),open_risk=str(risk),last_timestamp=self.clock(),
                 marks={k:v['bid'] for k,v in data['books'].items()},fx=data['fx'])
