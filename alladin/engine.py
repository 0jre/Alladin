import hashlib
import time
from dataclasses import asdict, replace
from .models import Candle, Snapshot, Proposal, Portfolio, finite
from .features import features
from .agents import Council
from .risk import approve, update_breakers, Approval
from .broker import PaperBroker
from .storage import Store, canonical
from .universe import seed_primary, classify_snapshot
from .signer import IsolatedSigner

class Service:
    """One persistent state machine, serialized by SQLite write transactions."""
    def __init__(self,cfg,db_path,agent_mode='rules',model=None,max_llm_calls=200,council=None,quoter=None,signer=None):
        self.cfg,self.store = cfg,Store(db_path)
        self.council = council or Council(agent_mode,model,max_llm_calls)
        self.quoter, self.signer = quoter, signer
        self.fingerprint = hashlib.sha256(canonical(asdict(cfg)).encode()).hexdigest()
    def _ensure(self,state):
        for key,default in [('series',{}),('pending_book',{}),('blocked_mints',{}),
                            ('universe',{}),('memory',[]),('shadow_gaps',[]),
                            ('curve',[]),('history',[]),('llm_calls',0),
                            ('bars_processed',0),('pending',None),('snapshot',None),
                            ('last_timestamp',None),('last_digest',None),
                            ('last_price',None),('last_decision',None)]:
            state.setdefault(key,default)
        if self.cfg.mint not in state['universe']:
            state['universe'][self.cfg.mint] = seed_primary(self.cfg.mint)
        return state
    def _marks(self,state,mint,price):
        marks = {}
        if mint == self.cfg.mint or state.get('last_price') is not None:
            marks[self.cfg.mint] = price if mint == self.cfg.mint else state['last_price']
        for name,series in state.get('series',{}).items():
            if name == mint:
                marks[name] = price
            elif series.get('last_price') is not None:
                marks[name] = series['last_price']
        if len(marks) <= 1:
            return price
        return marks
    def _decide(self,state,f,s,book,end):
        if hasattr(self.council,'client'):
            self.council.client.calls = max(getattr(self.council.client,'calls',0),state.get('llm_calls',0))
        if hasattr(self.council,'memory'):
            self.council.memory = list(state.get('memory',[]))
        p,audit = self.council.decide(f,s,book,self.cfg,end)
        if hasattr(self.council,'client'):
            state['llm_calls'] = self.council.client.calls
        return replace(p,mint=s.mint),audit
    def _remember(self,state,events):
        for e in events:
            if isinstance(e,dict) and e.get('event') == 'CLOSE':
                state['memory'].append(dict(mint=e.get('mint'),side=e.get('side'),net_pnl=e.get('net_pnl'),reason=e.get('reason')))
        state['memory'] = state['memory'][-20:]
    def _shadow_reason(self,state,mint,price):
        if self.cfg.execution != 'shadow':
            return None
        if self.quoter is None:
            return 'shadow_quote_unavailable'
        try:
            quoted = finite(self.quoter(mint),'shadow_price',1e-12)
        except Exception:
            return 'shadow_source_down'
        gap = abs(quoted/price-1) if price else 1
        state['shadow_gaps'] = (state.get('shadow_gaps',[])+[dict(mint=mint,quoted=quoted,mark=price,gap=gap)])[-200:]
        if gap > self.cfg.max_entry_gap_fraction:
            return 'shadow_price_divergence'
        return None
    def _apply_shadow(self,state,p,a,price):
        reason = self._shadow_reason(state,p.mint,price)
        if reason and p.action in {'LONG','SHORT'}:
            return Approval(False,tuple(a.reasons)+(reason,))
        return a
    def _execute_entry(self,broker,p,a,price,ts,state):
        if self.cfg.execution != 'live':
            return broker.open(p,a,price,ts)
        mint = p.mint
        if mint in state['blocked_mints']:
            return dict(event='ENTRY_BLOCKED',mint=mint,reason='mint_blocked_after_unknown_submit')
        if mint not in set(self.cfg.live_allowlist) or a.notional > self.cfg.live_notional_cap:
            return dict(event='ENTRY_BLOCKED',mint=mint,reason='live_policy')
        if not isinstance(self.signer,IsolatedSigner):
            return dict(event='ENTRY_BLOCKED',mint=mint,reason='signer_not_configured')
        result = self.signer.execute(dict(mint=mint,side=p.action,notional=a.notional,price=price,simulated=True,market=p.market))
        if result['status'] == 'confirmed':
            event = broker.open(p,a,result.get('price') or price,ts)
            event['signature'] = result.get('signature')
            event['execution'] = 'live'
            return event
        if result['status'] == 'unknown':
            state['blocked_mints'][mint] = ts
            return dict(event='ENTRY_UNKNOWN',mint=mint,reason='submission_unknown_no_retry')
        return dict(event='ENTRY_REJECTED',mint=mint,reason='submission_rejected')
    def _flatten_known(self,broker,state,ts,reason):
        marks = {}
        if state.get('last_price') is not None:
            marks[self.cfg.mint] = state['last_price']
        for mint,series in state.get('series',{}).items():
            if series.get('last_price') is not None:
                marks[mint] = series['last_price']
        events = []
        for pos in list(broker.book.positions):
            if pos.mint not in marks:
                raise ValueError('Sem preço para liquidar todas as posições')
        for mint in {p.mint for p in broker.book.positions}:
            events.extend(broker.flatten(marks[mint],ts,reason,mint=mint))
        return events
    def _universe(self,db,state,name,args):
        if name == 'universe':
            if args:
                raise ValueError('universe não aceita argumentos')
            self.store.save(db,state)
            return dict(instruments=state['universe'])
        if name == 'admit':
            if set(args) != {'snapshot'}:
                raise ValueError('admit exige snapshot')
            s = Snapshot(**args['snapshot'])
            if s.mint == self.cfg.mint:
                raise ValueError('Mint âncora permanece negociável pela configuração')
            inst = classify_snapshot(s,self.cfg)
            state['universe'][s.mint] = inst
            if inst['status'] != 'eligible':
                state['pending_book'].pop(s.mint,None)
            self.store.save(db,state)
            self.store.event(db,s.timestamp,'admit',inst)
            return inst
        if name == 'watch':
            if set(args)-{'mint','arm'} or 'mint' not in args or type(args.get('arm',False)) is not bool:
                raise ValueError('watch exige mint e arm booleano opcional')
            inst = state['universe'].get(args['mint'])
            if not inst or inst['status'] not in {'eligible','watched','negotiable'}:
                raise ValueError('Mint não elegível')
            active = sum(1 for v in state['universe'].values() if v['status'] in {'watched','negotiable'})
            if inst['status'] == 'eligible' and active >= self.cfg.max_watched:
                raise ValueError('Livro vigiado cheio')
            inst['status'] = 'negotiable' if args.get('arm',False) else 'watched'
            inst['reasons'] = []
            self.store.save(db,state)
            self.store.event(db,int(time.time()),'watch',inst)
            return inst
        if set(args) != {'mint'}:
            raise ValueError('unwatch exige mint')
        if args['mint'] == self.cfg.mint:
            raise ValueError('Mint âncora não sai do livro')
        inst = state['universe'].get(args['mint'])
        if not inst or inst['status'] not in {'watched','negotiable'}:
            raise ValueError('Mint não está vigiado')
        inst['status'] = 'eligible'
        state['pending_book'].pop(args['mint'],None)
        self.store.save(db,state)
        self.store.event(db,int(time.time()),'unwatch',inst)
        return inst
    def _ingest_series(self,db,state,book,b,s,args):
        inst = state['universe'].get(b.mint)
        if not inst or inst['status'] not in {'watched','negotiable'}:
            raise ValueError('Mint fora do livro vigiado')
        slot = state['series'].setdefault(b.mint,dict(history=[],snapshot=None,last_timestamp=None,last_digest=None,last_price=None,bars_processed=0))
        digest = hashlib.sha256(canonical(args).encode()).hexdigest()
        if b.timestamp == slot['last_timestamp']:
            if digest != slot['last_digest']:
                raise ValueError('Barra já processada com conteúdo diferente')
            return dict(result='duplicate_bar',timestamp=b.timestamp,mint=b.mint)
        if slot['last_timestamp'] is not None and b.timestamp != slot['last_timestamp']+self.cfg.timeframe_seconds:
            raise ValueError('Barras fora de ordem ou lacuna: reconstituir feed antes de continuar')
        end = b.timestamp+self.cfg.timeframe_seconds
        if end > time.time()+5:
            raise ValueError('Barra ainda não fechada no horário UTC atual')
        if s.timestamp > end or (s.available_at is not None and s.available_at > end):
            raise ValueError('Snapshot do futuro em relação à barra')
        broker = PaperBroker(book,self.cfg)
        events = []
        mark = self._marks(state,b.mint,b.open)
        update_breakers(book,self.cfg,mark,b.timestamp)
        pending = state['pending_book'].get(b.mint)
        if pending:
            p = Proposal(**pending['proposal'])
            if p.action == 'CLOSE':
                events.extend(broker.close(x,b.open,b.timestamp,'agent_exit') for x in list(book.positions) if x.market == p.market and x.mint == p.mint)
            elif not book.halted and p.mint not in state['blocked_mints']:
                old_s = Snapshot(**slot['snapshot'])
                old_f = features([Candle(**x) for x in slot['history']])
                a = approve(p,old_f,old_s,book,self.cfg,b.timestamp,b.open,inst)
                a = self._apply_shadow(state,p,a,b.open)
                events.append(dict(event='ENTRY_RECHECK',approval=asdict(a)))
                if a.approved:
                    events.append(self._execute_entry(broker,p,a,b.open,b.timestamp,state))
        state['pending_book'].pop(b.mint,None)
        if book.halted:
            events.extend(broker.flatten(b.open,b.timestamp,'circuit_breaker',mint=b.mint))
        events.extend(broker.on_bar(b))
        mark = self._marks(state,b.mint,b.close)
        equity = update_breakers(book,self.cfg,mark,end)
        if book.halted:
            events.extend(broker.flatten(b.close,end,'circuit_breaker',mint=b.mint))
            equity = book.equity(mark)
        slot['history'] = (slot['history']+[asdict(b)])[-500:]
        f = features([Candle(**x) for x in slot['history']])
        if f.get('ready'):
            broker.trail(b.close,f['atr'],b.mint)
        if slot['bars_processed']+1 < self.cfg.warmup_bars:
            p,audit = replace(Proposal(thesis='Aquecimento obrigatório'),mint=b.mint),{'gate':'warmup','mode':self.council.mode}
        elif inst['status'] != 'negotiable':
            # Watched mints only collect features; the council is not consulted.
            p,audit = replace(Proposal(thesis='Mint vigiado, ainda não negociável'),mint=b.mint),{'gate':'watched_only','mode':self.council.mode}
        else:
            p,audit = self._decide(state,f,s,book,end)
        a = self._apply_shadow(state,p,approve(p,f,s,book,self.cfg,end,instrument=inst),b.close)
        if inst['status'] == 'negotiable' and p.action in {'LONG','SHORT','CLOSE'} and a.approved and b.mint not in state['blocked_mints']:
            state['pending_book'][b.mint] = dict(proposal=asdict(p),decision_at=end)
        slot.update(snapshot=asdict(s),last_timestamp=b.timestamp,last_digest=digest,last_price=b.close,bars_processed=slot['bars_processed']+1)
        decision = dict(timestamp=end,mint=b.mint,proposal=asdict(p),approval=asdict(a),council=audit)
        state['portfolio'] = book.serialize()
        state['last_decision'] = decision
        state['curve'].append(dict(timestamp=end,equity=equity,price=b.close,mint=b.mint,gross=book.gross(mark),net=book.net(mark)))
        state['curve'] = state['curve'][-2000:]
        self._remember(state,events)
        self.store.save(db,state)
        self.store.event(db,end,'cycle',dict(decision=decision,events=events,equity=equity))
        return dict(result='processed',timestamp=b.timestamp,mint=b.mint,decision=decision,events=events,equity_usdc=equity)
    def _load(self,db):
        state = self.store.load(db)
        if state:
            if state['config_hash'] != self.fingerprint or state['agent_mode'] != self.council.mode:
                raise ValueError('Config/modo diferente da sessão persistida; use outro banco para nova pesquisa')
            return self._ensure(state)
        book = Portfolio(self.cfg.initial_usdc,self.cfg.initial_usdc,self.cfg.initial_usdc)
        return self._ensure(dict(config_hash=self.fingerprint,agent_mode=self.council.mode,
                    portfolio=book.serialize(),history=[],pending=None,snapshot=None,
                    last_timestamp=None,last_digest=None,last_price=None,
                    curve=[],bars_processed=0,last_decision=None))
    def status(self):
        with self.store.connect() as db:
            state = self._load(db)
        book = Portfolio.restore(state['portfolio'])
        marks = {}
        if state.get('last_price') is not None:
            marks[self.cfg.mint] = state['last_price']
        for mint,series in state.get('series',{}).items():
            if series.get('last_price') is not None:
                marks[mint] = series['last_price']
        # Per-mint marks: a scalar price would misprice positions of other mints.
        price = marks if marks else 0
        client_calls = getattr(getattr(self.council,'client',None),'calls',0)
        return dict(chain=self.cfg.chain,venue='coinbase',execution=self.cfg.execution,asset=f'{self.cfg.mint}/USDC',agent_mode=self.council.mode,
                    bars_processed=state['bars_processed'],last_timestamp=state['last_timestamp'],
                    equity_usdc=book.equity(price),cash_usdc=book.cash,
                    gross_usdc=book.gross(price),net_usdc=book.net(price),
                    positions=[asdict(p) for p in book.positions],halted=book.halted,
                    halt_reason=book.halt_reason,pending=state['pending'],
                    pending_book=state['pending_book'],
                    closed_trades=book.total_closed,costs_usdc=book.fees_paid,
                    last_decision=state['last_decision'],
                    series={m:dict(bars_processed=s['bars_processed'],last_price=s['last_price'])
                            for m,s in state.get('series',{}).items()},
                    llm_calls_process=client_calls,
                    llm_calls_persisted=state.get('llm_calls',0),
                    universe={k:v['status'] for k,v in state.get('universe',{}).items()},
                    blocked_mints=sorted(state.get('blocked_mints',{})))
    def command(self,name,args,key):
        allowed = {'ingest','analyze','evaluate','halt','finalize','universe','admit','watch','unwatch'}
        if name not in allowed:
            raise ValueError('Comando desconhecido ou não permitido')
        with self.store.transaction() as db:
            return self.store.once(db,key,dict(command=name,args=args),
                                   lambda:self._command(db,name,args))
    def _command(self,db,name,args):
        state = self._load(db)
        book = Portfolio.restore(state['portfolio'])
        if name in {'universe','admit','watch','unwatch'}:
            return self._universe(db,state,name,args)
        if name == 'ingest':
            if set(args) != {'candle','snapshot'}:
                raise ValueError('ingest exige somente candle e snapshot')
            b,s = Candle(**args['candle']),Snapshot(**args['snapshot'])
            if b.mint != s.mint:
                raise ValueError('candle e snapshot de mints diferentes')
            if b.chain != self.cfg.chain or s.chain != self.cfg.chain:
                raise ValueError('Barra de outra rede')
            if b.mint != self.cfg.mint:
                return self._ingest_series(db,state,book,b,s,args)
            digest = hashlib.sha256(canonical(args).encode()).hexdigest()
            if b.timestamp == state['last_timestamp']:
                if digest != state['last_digest']:
                    raise ValueError('Barra já processada com conteúdo diferente')
                return dict(result='duplicate_bar',timestamp=b.timestamp)
            if state['last_timestamp'] is not None and b.timestamp != state['last_timestamp']+self.cfg.timeframe_seconds:
                raise ValueError('Barras fora de ordem ou lacuna: reconstituir feed antes de continuar')
            end = b.timestamp+self.cfg.timeframe_seconds
            if end > time.time()+5:
                raise ValueError('Barra ainda não fechada no horário UTC atual')
            if s.timestamp > end or (s.available_at is not None and s.available_at > end):
                raise ValueError('Snapshot do futuro em relação à barra')
            broker = PaperBroker(book,self.cfg)
            events = []
            mark = self._marks(state,b.mint,b.open)
            update_breakers(book,self.cfg,mark,b.timestamp)
            if state['pending']:
                pending = state['pending']
                p = Proposal(**pending['proposal'])
                if p.action == 'CLOSE':
                    events.extend(broker.close(x,b.open,b.timestamp,'agent_exit') for x in list(book.positions) if x.market == p.market and x.mint == p.mint)
                elif not book.halted and p.mint not in state['blocked_mints']:
                    old_s = Snapshot(**state['snapshot'])
                    old_f = features([Candle(**x) for x in state['history']])
                    a = approve(p,old_f,old_s,book,self.cfg,b.timestamp,b.open,state['universe'].get(p.mint))
                    a = self._apply_shadow(state,p,a,b.open)
                    events.append(dict(event='ENTRY_RECHECK',approval=asdict(a)))
                    if a.approved:
                        events.append(self._execute_entry(broker,p,a,b.open,b.timestamp,state))
            state['pending'] = None
            if book.halted:
                events.extend(broker.flatten(b.open,b.timestamp,'circuit_breaker',mint=b.mint))
            events.extend(broker.on_bar(b))
            mark = self._marks(state,b.mint,b.close)
            equity = update_breakers(book,self.cfg,mark,end)
            if book.halted:
                events.extend(broker.flatten(b.close,end,'circuit_breaker',mint=b.mint))
                equity = book.equity(mark)
            state['history'] = (state['history']+[asdict(b)])[-500:]
            f = features([Candle(**x) for x in state['history']])
            if f.get('ready'):
                broker.trail(b.close,f['atr'],b.mint)
            if state['bars_processed']+1 < self.cfg.warmup_bars:
                p,audit = replace(Proposal(thesis='Aquecimento obrigatório'),mint=b.mint),{'gate':'warmup','mode':self.council.mode}
            else:
                p,audit = self._decide(state,f,s,book,end)
            a = self._apply_shadow(state,p,approve(p,f,s,book,self.cfg,end,instrument=state['universe'].get(b.mint)),b.close)
            if p.action in {'LONG','SHORT','CLOSE'} and a.approved:
                state['pending'] = dict(proposal=asdict(p),decision_at=end)
            decision = dict(timestamp=end,proposal=asdict(p),approval=asdict(a),council=audit)
            state.update(portfolio=book.serialize(),snapshot=asdict(s),last_timestamp=b.timestamp,
                         last_digest=digest,last_price=b.close,bars_processed=state['bars_processed']+1,
                         last_decision=decision)
            state['curve'].append(dict(timestamp=end,equity=equity,price=b.close,
                                       gross=book.gross(mark),net=book.net(mark)))
            state['curve'] = state['curve'][-2000:]
            self._remember(state,events)
            self.store.save(db,state)
            self.store.event(db,end,'cycle',dict(decision=decision,events=events,equity=equity))
            return dict(result='processed',timestamp=b.timestamp,decision=decision,events=events,equity_usdc=equity)
        if name == 'halt':
            if args:
                raise ValueError('halt não aceita argumentos')
            book.halted,book.halt_reason = True,'operator_halt'
            state['pending'] = None
            state['pending_book'] = {}
            # Do not fabricate a fresh fill at an old mark. Next feed bar flattens.
            state['portfolio'] = book.serialize()
            self.store.save(db,state)
            self.store.event(db,int(time.time()),'halt',{'flatten':'next_valid_bar'})
            return dict(result='halted',flatten='next_valid_bar',open_positions=len(book.positions))
        if name == 'finalize':
            if args:
                raise ValueError('finalize não aceita argumentos')
            if state['last_price'] is None:
                raise ValueError('Nenhuma barra para finalizar')
            broker = PaperBroker(book,self.cfg)
            ts = state['last_timestamp']+self.cfg.timeframe_seconds
            events = self._flatten_known(broker,state,ts,'end_of_research')
            book.halted,book.halt_reason = True,'research_finalized'
            state['pending'] = None
            state['pending_book'] = {}
            state['portfolio'] = book.serialize()
            state['curve'].append(dict(timestamp=state['last_timestamp']+self.cfg.timeframe_seconds,
                                       equity=book.cash,price=state['last_price'],gross=0,net=0))
            self.store.save(db,state)
            self.store.event(db,int(time.time()),'finalize',{'events':events})
            return dict(result='finalized',events=events,equity_usdc=book.cash)
        if not state['history'] or not state['snapshot']:
            raise ValueError('Ainda não há feed: envie barras fechadas e snapshot via ingest')
        f = features([Candle(**x) for x in state['history']])
        s = Snapshot(**state['snapshot'])
        # Analysis uses the last closed bar timestamp. Live freshness status separately.
        now = state['last_timestamp']+self.cfg.timeframe_seconds
        if name == 'analyze':
            if args:
                raise ValueError('analyze não aceita argumentos')
            p,audit = self.council.decide(f,s,book,self.cfg,now)
            result = dict(features=f,snapshot=asdict(s),proposal=asdict(p),council=audit,
                          approval=asdict(approve(p,f,s,book,self.cfg,now)),as_of=now,
                          wallclock_age_seconds=int(time.time())-now)
        else:
            if set(args) != {'proposal'}:
                raise ValueError('evaluate exige somente proposal')
            p = Proposal(**args['proposal'])
            result = dict(approval=asdict(approve(p,f,s,book,self.cfg,now)),
                          proposal=asdict(p),execution='none',as_of=now)
        self.store.event(db,now,name,result)
        return result
