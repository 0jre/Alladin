import hashlib
import time
from dataclasses import asdict
from .models import Config, Candle, Snapshot, Proposal, Portfolio
from .features import features
from .agents import Council
from .risk import approve, update_breakers
from .broker import PaperBroker
from .storage import Store, canonical

class Service:
    """One persistent state machine, serialized by SQLite write transactions."""
    def __init__(self,cfg,db_path,agent_mode='rules',model=None,max_llm_calls=200,council=None):
        self.cfg,self.store = cfg,Store(db_path)
        self.council = council or Council(agent_mode,model,max_llm_calls)
        self.fingerprint = hashlib.sha256(canonical(asdict(cfg)).encode()).hexdigest()
    def _load(self,db):
        state = self.store.load(db)
        if state:
            if state['config_hash'] != self.fingerprint or state['agent_mode'] != self.council.mode:
                raise ValueError('Config/modo diferente da sessão persistida; use outro banco para nova pesquisa')
            return state
        book = Portfolio(self.cfg.initial_usdc,self.cfg.initial_usdc,self.cfg.initial_usdc)
        return dict(config_hash=self.fingerprint,agent_mode=self.council.mode,
                    portfolio=book.serialize(),history=[],pending=None,snapshot=None,
                    last_timestamp=None,last_digest=None,last_price=None,
                    curve=[],bars_processed=0,last_decision=None)
    def status(self):
        with self.store.connect() as db:
            state = self._load(db)
        book = Portfolio.restore(state['portfolio'])
        price = state['last_price'] or 0
        return dict(chain='solana',execution='paper',asset='SOL/USDC',agent_mode=self.council.mode,
                    bars_processed=state['bars_processed'],last_timestamp=state['last_timestamp'],
                    equity_usdc=book.equity(price),cash_usdc=book.cash,
                    positions=[asdict(p) for p in book.positions],halted=book.halted,
                    halt_reason=book.halt_reason,pending=state['pending'],
                    closed_trades=book.total_closed,costs_usdc=book.fees_paid,
                    last_decision=state['last_decision'],
                    llm_calls_process=self.council.client.calls)
    def command(self,name,args,key):
        allowed = {'ingest','analyze','evaluate','halt','finalize'}
        if name not in allowed:
            raise ValueError('Comando desconhecido ou não permitido')
        with self.store.transaction() as db:
            return self.store.once(db,key,dict(command=name,args=args),
                                   lambda:self._command(db,name,args))
    def _command(self,db,name,args):
        state = self._load(db)
        book = Portfolio.restore(state['portfolio'])
        if name == 'ingest':
            if set(args) != {'candle','snapshot'}:
                raise ValueError('ingest exige somente candle e snapshot')
            b,s = Candle(**args['candle']),Snapshot(**args['snapshot'])
            if b.mint != self.cfg.mint or s.mint != self.cfg.mint:
                raise ValueError('Mint não corresponde ao universo configurado')
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
            if s.timestamp > end:
                raise ValueError('Snapshot do futuro em relação à barra')
            broker = PaperBroker(book,self.cfg)
            events = []
            update_breakers(book,self.cfg,b.open,b.timestamp)
            if state['pending']:
                pending = state['pending']
                p = Proposal(**pending['proposal'])
                if p.action == 'CLOSE':
                    events.extend(broker.close(x,b.open,b.timestamp,'agent_exit') for x in list(book.positions) if x.market == p.market)
                elif not book.halted:
                    old_s = Snapshot(**state['snapshot'])
                    old_f = features([Candle(**x) for x in state['history']])
                    a = approve(p,old_f,old_s,book,self.cfg,b.timestamp,b.open)
                    events.append(dict(event='ENTRY_RECHECK',approval=asdict(a)))
                    if a.approved:
                        events.append(broker.open(p,a,b.open,b.timestamp))
            state['pending'] = None
            if book.halted:
                events.extend(broker.flatten(b.open,b.timestamp,'circuit_breaker'))
            events.extend(broker.on_bar(b))
            equity = update_breakers(book,self.cfg,b.close,end)
            if book.halted:
                events.extend(broker.flatten(b.close,end,'circuit_breaker'))
                equity = book.equity(b.close)
            state['history'] = (state['history']+[asdict(b)])[-500:]
            f = features([Candle(**x) for x in state['history']])
            if f.get('ready'):
                broker.trail(b.close,f['atr'])
            if state['bars_processed']+1 < self.cfg.warmup_bars:
                p,audit = Proposal(thesis='Aquecimento obrigatório'),{'gate':'warmup','mode':self.council.mode}
            else:
                p,audit = self.council.decide(f,s,book,self.cfg,end)
            a = approve(p,f,s,book,self.cfg,end)
            if p.action in {'LONG','SHORT','CLOSE'} and a.approved:
                state['pending'] = dict(proposal=asdict(p),decision_at=end)
            decision = dict(timestamp=end,proposal=asdict(p),approval=asdict(a),council=audit)
            state.update(portfolio=book.serialize(),snapshot=asdict(s),last_timestamp=b.timestamp,
                         last_digest=digest,last_price=b.close,bars_processed=state['bars_processed']+1,
                         last_decision=decision)
            state['curve'].append(dict(timestamp=end,equity=equity,price=b.close,
                                       gross=book.gross(b.close),net=book.net(b.close)))
            state['curve'] = state['curve'][-2000:]
            self.store.save(db,state)
            self.store.event(db,end,'cycle',dict(decision=decision,events=events,equity=equity))
            return dict(result='processed',timestamp=b.timestamp,decision=decision,events=events,equity_usdc=equity)
        if name == 'halt':
            if args:
                raise ValueError('halt não aceita argumentos')
            book.halted,book.halt_reason = True,'operator_halt'
            state['pending'] = None
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
            events = broker.flatten(state['last_price'],state['last_timestamp']+self.cfg.timeframe_seconds,'end_of_research')
            book.halted,book.halt_reason = True,'research_finalized'
            state['pending'] = None
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
