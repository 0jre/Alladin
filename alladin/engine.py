import hashlib
import json
import threading
import time
from dataclasses import asdict, replace
from .models import Candle, Snapshot, Proposal, Portfolio
from .features import features
from .agents import Council
from .risk import approve, update_breakers, Approval
from .broker import PaperBroker
from .storage import Store, canonical
from .universe import seed_primary, classify_snapshot
from .providers import CoinbaseMarket, collect
from .transport import DataError,deadline,check_deadline,COLLECTION_TOTAL_SECONDS
from .evaluation import assess_trades
from .external import context_hash
import uuid

def config_fingerprint(cfg):
    payload=asdict(cfg)
    if cfg.sizing_mode=='risk_budget':
        payload.pop('sizing_mode')
    return hashlib.sha256(canonical(payload).encode()).hexdigest()


class Service:
    """One persistent state machine, serialized by SQLite write transactions."""
    def __init__(self,cfg,db_path,agent_mode='external',council=None):
        self.cfg,self.store = cfg,Store(db_path)
        self.council = council or Council(agent_mode)
        self.fingerprint=config_fingerprint(cfg)
        self.command_lock = threading.RLock()
        self._provider = None
    def revise_policy(self,previous_cfg):
        """Explicit, atomic revision of the return criterion; never reset risk history."""
        before,after=asdict(previous_cfg),asdict(self.cfg)
        changes={key:{'before':before[key],'after':after[key]} for key in before if before[key]!=after[key]}
        if set(changes)!={'min_reward_risk'}:
            raise ValueError('Revisão permite somente min_reward_risk; demais limites devem ser preservados')
        old_hash=config_fingerprint(previous_cfg)
        with self.store.transaction() as db:
            state=self.store.load(db)
            if state is None or state.get('agent_mode')!=self.council.mode:
                raise ValueError('Sessão existente compatível obrigatória; revisão não cria carteira')
            if state.get('config_hash')==self.fingerprint:
                row=db.execute("SELECT payload FROM events WHERE kind='policy_revision' ORDER BY seq DESC LIMIT 1").fetchone()
                previous=json.loads(row[0]) if row else {}
                if previous.get('previous_config_sha256')!=old_hash or previous.get('config_sha256')!=self.fingerprint:
                    raise ValueError('Revisão já existente tem outra origem; configuração anterior incorreta')
                return dict(result='already_revised',changes=changes)
            if state.get('config_hash')!=old_hash:
                raise ValueError('Configuração anterior não corresponde à sessão; revisão recusada')
            portfolio_digest=hashlib.sha256(canonical(state['portfolio']).encode()).hexdigest()
            state['config_hash']=self.fingerprint
            state['pending']=None
            state['pending_book']={}
            state['external_task']=None
            result=dict(result='policy_revised',changes=changes,previous_config_sha256=old_hash,
                        config_sha256=self.fingerprint,portfolio_sha256=portfolio_digest,
                        cancelled_pending_decisions=True)
            self.store.save(db,state)
            self.store.event(db,int(time.time()),'policy_revision',result)
            return result

    def _ensure(self,state):
        for key,default in [('series',{}),('pending_book',{}),('blocked_mints',{}),
                            ('universe',{}),('memory',[]),
                            ('curve',[]),('history',[]),('external_task',None),
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
        if book.halted:
            return replace(Proposal(thesis='Sessão bloqueada: '+book.halt_reason),mint=s.mint),{'gate':'halted','mode':self.council.mode}
        if hasattr(self.council,'memory'):
            self.council.memory = list(state.get('memory',[]))
        evidence_features=dict(f)
        if state.get('history'):
            evidence_features['bar_closed_at']=state['history'][-1]['timestamp']+self.cfg.timeframe_seconds
        evidence_features['timeframe_seconds']=self.cfg.timeframe_seconds
        p,audit = self.council.decide(evidence_features,s,book,self.cfg,end)
        return replace(p,mint=s.mint),audit
    def _prepare_external(self,db,state,book,f,s,now,args):
        if args or self.council.mode!='external':
            raise ValueError('prepare_decision exige modo external e nenhum argumento')
        if state['bars_processed']<self.cfg.warmup_bars:
            raise ValueError('Aquecimento obrigatório')
        _,audit=self._decide(state,f,s,book,now)
        task=audit.pop('task',None)
        if task is None:
            state['external_task']=None
            self.store.save(db,state)
            result=dict(result='abstained',council=audit)
            self.store.event(db,int(time.time()),'prepare_decision',result)
            return result
        created=int(time.time())
        if state.get('input_mode')=='paper_live' and not -5<=created-s.timestamp<=min(30,self.cfg.max_snapshot_age_seconds):
            raise DataError('Cotação expirou; colete novo contexto antes de preparar')
        task.update(id=uuid.uuid4().hex,context_sha256=context_hash(state),
                    evidence_sha256=audit['evidence_sha256'],created_at=created,
                    expires_at=created+min(300,self.cfg.timeframe_seconds),
                    status='prepared',protocol='external-session-v2')
        state['external_task']=task
        self.store.save(db,state)
        self.store.event(db,created,'prepare_decision',dict(id=task['id'],evidence_sha256=task['evidence_sha256']))
        return dict(result='awaiting_external_agents',task=task)

    def _submit_external(self,db,state,book,f,s,now,args,fresh=None):
        required={'task_id','evidence_sha256','reports','decision','session_id'}
        if self.council.mode!='external' or set(args)!=required:
            raise ValueError('submit_decision exige task_id, evidence_sha256, reports, decision e session_id')
        if not isinstance(args['session_id'],str) or not 1<=len(args['session_id'])<=200:
            raise ValueError('session_id inválido; não envie credenciais')
        task=state.get('external_task')
        if not task or task['id']!=args['task_id'] or task['status']!='prepared':
            raise ValueError('Tarefa inexistente, substituída ou já consumida')
        if args['evidence_sha256']!=task['evidence_sha256'] or context_hash(state)!=task['context_sha256']:
            raise ValueError('Contexto mudou; prepare uma nova decisão')
        wall=int(time.time())
        if wall>task['expires_at'] or wall<task['created_at']-5:
            raise ValueError('Tarefa expirada; prepare uma nova decisão')
        live=state.get('input_mode')=='paper_live'
        execution_snapshot=fresh if live else s
        if live:
            if execution_snapshot is None or not -5<=wall-execution_snapshot.timestamp<=min(30,self.cfg.max_snapshot_age_seconds):
                raise DataError('Cotação expirada; nenhuma operação executada')
            if wall>=state['last_timestamp']+2*self.cfg.timeframe_seconds:
                raise ValueError('Nova barra fechou; atualize o feed e prepare nova decisão')
            if abs(execution_snapshot.price/s.price-1)>self.cfg.max_entry_gap_fraction:
                raise ValueError('Preço desviou do contexto; prepare nova decisão')
        ef=dict(f,bar_closed_at=state['last_timestamp']+self.cfg.timeframe_seconds,
                timeframe_seconds=self.cfg.timeframe_seconds)
        self.council.memory=list(state.get('memory',[]))
        p,audit=self.council.decide(ef,s,book,self.cfg,now,
            submission={k:args[k] for k in ('reports','decision')})
        if audit.get('evidence_sha256')!=task['evidence_sha256']:
            raise ValueError('Evidências divergentes')
        audit['session_id']=args['session_id']
        mark=execution_snapshot
        approval=approve(p,ef,mark,book,self.cfg,wall if live else now,mark.price,state['universe'].get(s.mint))
        audit['execution_snapshot']=asdict(mark)
        audit['task_id']=task['id']
        events=[]
        if live:
            broker=PaperBroker(book,self.cfg)
            events.extend(broker.on_mark(mark.price,wall,s.mint))
            update_breakers(book,self.cfg,mark.price,wall)
            if book.halted:
                events.extend(broker.flatten(mark.price,wall,'circuit_breaker',mint=s.mint))
            approval=approve(p,ef,mark,book,self.cfg,wall,mark.price,state['universe'].get(s.mint))
            if p.action=='CLOSE' and not book.halted:
                events.extend(broker.close(pos,mark.price,wall,'external_session_exit')
                              for pos in list(book.positions) if pos.mint==s.mint and pos.market=='spot')
            elif p.action=='LONG' and approval.approved and not book.halted:
                events.append(self._execute_entry(broker,p,approval,mark.price,wall,state,decision_audit=audit,source=mark.source))
            state['curve'].append(dict(timestamp=wall,equity=book.equity(mark.price),price=mark.price,
                                       gross=book.gross(mark.price),net=book.net(mark.price)))
            state['curve']=state['curve'][-2000:]
            state['portfolio']=book.serialize()
            state['snapshot']=asdict(mark)
            state['last_price']=mark.price
            self._remember(state,events)
        elif p.action in {'LONG','CLOSE'} and approval.approved and not book.halted:
            state['pending']=dict(proposal=asdict(p),decision_at=now)
        decision=dict(timestamp=now,proposal=asdict(p),approval=asdict(approval),council=audit)
        state['last_decision']=decision
        task['status']='consumed'
        result=dict(result='submitted',decision=decision,events=events,execution='paper' if live else 'next_replay_bar')
        self.store.save(db,state)
        self.store.event(db,wall,'submit_decision',dict(task_id=task['id'],session_id=args['session_id'],**result))
        return result

    def _remember(self,state,events):
        for e in events:
            if isinstance(e,dict) and e.get('event') == 'CLOSE':
                state['memory'].append(dict(mint=e.get('mint'),side=e.get('side'),net_pnl=e.get('net_pnl'),reason=e.get('reason')))
        state['memory'] = state['memory'][-20:]
    def _execute_entry(self,broker,p,a,price,ts,state,decision_audit=None,source=None):
        if self.cfg.execution != 'paper':
            raise ValueError('Alladin só permite fills paper; execução externa não existe')
        if p.market != 'spot':
            raise ValueError('Alladin só permite posições spot')
        event=broker.open(p,a,price,ts)
        decision=(state.get('last_decision') or {}).get('council',{}) if decision_audit is None else decision_audit
        event['decision_context']=dict(agent_mode=self.council.mode,protocol=decision.get('protocol'),session_id=decision.get('session_id'),
            prompt_bundle_sha256=(decision.get('prompt_pack') or {}).get('bundle_sha256'),
            evidence_sha256=decision.get('evidence_sha256'))
        event['source']=source or (state.get('snapshot') or {}).get('source')
        return event
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
        a = approve(p,f,s,book,self.cfg,end,instrument=inst)
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
        return dict(chain=self.cfg.chain,venue='coinbase_advanced',data_sources=['coinbase'],product_id='SOL-USDC',onchain_verification=False,execution=self.cfg.execution,asset=f'{self.cfg.mint}/USDC',agent_mode=self.council.mode,
                    sizing_mode=self.cfg.sizing_mode,bars_processed=state['bars_processed'],last_timestamp=state['last_timestamp'],
                    equity_usdc=book.equity(price),cash_usdc=book.cash,
                    gross_usdc=book.gross(price),net_usdc=book.net(price),
                    positions=[asdict(p) for p in book.positions],halted=book.halted,
                    halt_reason=book.halt_reason,pending=state['pending'],
                    pending_book=state['pending_book'],
                    closed_trades=book.total_closed,costs_usdc=book.fees_paid,
                    last_decision=state['last_decision'],
                    series={m:dict(bars_processed=s['bars_processed'],last_price=s['last_price'])
                            for m,s in state.get('series',{}).items()},
                    external_task=state.get('external_task'),
                    universe={k:v['status'] for k,v in state.get('universe',{}).items()},
                    blocked_mints=sorted(state.get('blocked_mints',{})))
    def diagnostics(self):
        from .diagnostics import diagnose
        return diagnose(self.cfg)

    def performance(self):
        with self.store.connect() as db:
            db.execute('BEGIN')
            state=self._load(db)
            trades=[]
            entries={}
            for row in db.execute('SELECT payload FROM events ORDER BY seq'):
                payload=json.loads(row[0])
                for event in payload.get('events',[]):
                    if event.get('event')=='OPEN':
                        entries[event['position_id']]=event
                    elif event.get('event')=='CLOSE':
                        entry=entries.pop(event['position_id'],{})
                        trades.append({**event,'decision_context':entry.get('decision_context'),
                                       'entry_source':entry.get('source')})
        source=(state.get('snapshot') or {}).get('source')
        result=assess_trades(trades,source,self.council.mode)
        book=Portfolio.restore(state['portfolio'])
        result['open_positions_not_scored']=len(book.positions)
        result['imported_roundtrips_not_scored']=max(0,book.total_closed-len(trades))
        if book.positions or result['imported_roundtrips_not_scored']:
            result['target']['measured_claim_supported']=False
            result['limitations'].append('Open positions or imported trades without complete events prevent a complete-history validation claim.')
        result['initial_usdc']=self.cfg.initial_usdc
        result['audit_verification_endpoint']='/v1/audit/verify'
        return result
    def command(self,name,args,key):
        if name in {'paper_tick','prepare_decision','submit_decision'}:
            with deadline(COLLECTION_TOTAL_SECONDS):
                return self._bounded_command(name,args,key)
        return self._bounded_command(name,args,key)

    def _bounded_command(self,name,args,key):
        check_deadline()
        if name == 'paper_tick':
            with self.command_lock:
                return self._serialized_command(name,args,key)
        return self._serialized_command(name,args,key)
    def _serialized_command(self,name,args,key):
        allowed = {'ingest','paper_tick','analyze','evaluate','halt','finalize','universe','admit','watch','unwatch','prepare_decision','submit_decision'}
        if not isinstance(name,str) or name not in allowed:
            raise ValueError('Comando desconhecido ou não permitido')
        if not isinstance(args,dict):
            raise ValueError('args deve ser um objeto')
        request = dict(command=name,args=args)
        with self.store.connect() as db:
            state = self._load(db)  # reject incompatible persisted sessions before any network IO
            old = self.store.lookup(db,key,request)
            if old is not None:
                return old
            if name in {'paper_tick','ingest'}:
                mode = 'paper_live' if name == 'paper_tick' else 'replay'
                if state.get('input_mode') not in (None,mode):
                    raise ValueError('Não misture paper-live e replay no mesmo banco')
        if name=='prepare_decision' and (args or self.council.mode!='external'):
            raise ValueError('prepare_decision exige modo external e nenhum argumento')
        if name=='submit_decision' and (state.get('external_task') or {}).get('protocol')!='external-session-v2':
            raise ValueError('Tarefa de protocolo antigo ou ausente; execute prepare_decision novamente')
        paper_data = self._collect_paper_data(args) if name == 'paper_tick' else None
        if name in {'prepare_decision','submit_decision'} and state.get('input_mode')=='paper_live':
            # Reasoning runs in the caller's session. Refresh execution observations
            # outside the write transaction; bind the submission again inside it.
            if not state['history']:
                raise ValueError('Feed obrigatório')
            provider=self._provider or CoinbaseMarket()
            candles=[Candle(**row) for row in state['history']]
            paper_data={'snapshot':collect(self.cfg.mint,market=lambda:provider.market(
                self.cfg.mint,candles=candles,timeframe_seconds=self.cfg.timeframe_seconds))}
        check_deadline()
        with self.store.transaction() as db:
            check_deadline()
            return self.store.once(db,key,dict(command=name,args=args),
                                   lambda:self._command(db,name,args,paper_data))
    def _collect_paper_data(self,args):
        """Fetch public data before opening the SQLite write transaction."""
        if args:
            raise ValueError('paper_tick não aceita argumentos; coleta fontes Solana read-only')
        if self.cfg.execution != 'paper' or self.cfg.chain != 'solana':
            raise ValueError('paper_tick exige execução paper exclusivamente na Solana')
        if set(self.cfg.allowed_markets) != {'spot'}:
            raise ValueError('paper_tick exige mercado spot')
        step = self.cfg.timeframe_seconds
        if step % 60 or step // 60 not in {1,5,15}:
            raise ValueError('timeframe paper deve ser 1, 5 ou 15 minutos')
        # Read the last committed bar to avoid fetching a new quote when no new candle exists.
        with self.store.connect() as db:
            state = self._load(db)
        if self._provider is None:
            self._provider = CoinbaseMarket()
        provider = self._provider
        candles = provider.candles(self.cfg.mint, count=120, aggregate=step)
        if int(time.time()) - (candles[-1].timestamp+step) > step:
            raise DataError('Feed Coinbase atrasado; ciclo bloqueado')
        snap = None
        if state['last_timestamp'] is not None and candles[-1].timestamp > state['last_timestamp']:
            # Coinbase book timestamp must remain the original observation time.
            snap = collect(self.cfg.mint,market=lambda:provider.market(
                self.cfg.mint,candles=candles,timeframe_seconds=step))
        return dict(candles=candles,snapshot=snap)
    def _command(self,db,name,args,paper_data=None):
        state = self._load(db)
        book = Portfolio.restore(state['portfolio'])
        if name in {'paper_tick','ingest'}:
            mode = 'paper_live' if name == 'paper_tick' else 'replay'
            if state.get('input_mode') not in (None,mode):
                raise ValueError('Não misture paper-live e replay no mesmo banco')
            state['input_mode'] = mode
        if name in {'universe','admit','watch','unwatch'}:
            return self._universe(db,state,name,args)
        if name == 'paper_tick':
            step = self.cfg.timeframe_seconds
            candles = paper_data['candles']
            if state['last_timestamp'] is None:
                if len(candles) < self.cfg.warmup_bars:
                    raise ValueError('OHLCV Coinbase insuficiente para aquecimento')
                history = candles[-self.cfg.warmup_bars:]
                for left,right in zip(history,history[1:]):
                    if right.timestamp != left.timestamp+step:
                        raise ValueError('Lacuna no OHLCV de aquecimento')
                if history[-1].timestamp+step > time.time()+5:
                    raise ValueError('Última barra de aquecimento ainda está aberta')
                state['history'] = [asdict(b) for b in history]
                state['last_timestamp'] = history[-1].timestamp
                state['last_price'] = history[-1].close
                state['bars_processed'] = len(history)
                state['last_digest'] = hashlib.sha256(canonical(state['history']).encode()).hexdigest()
                self.store.save(db,state)
                self.store.event(db,int(time.time()),'warmup',dict(source='coinbase_advanced_sol_spot',
                                  bars=len(history),last_timestamp=history[-1].timestamp,
                                  last_price=history[-1].close))
                return dict(result='warmed_up',bars=len(history),last_bar=history[-1].timestamp,
                            next_action='prepare_decision pode coletar snapshot atual; nenhum trade no aquecimento')
            next_ts = state['last_timestamp']+step
            bar = next((b for b in candles if b.timestamp == next_ts),None)
            if bar is None:
                newest = candles[-1].timestamp
                if newest <= state['last_timestamp']:
                    return dict(result='waiting_for_closed_bar',last_bar=state['last_timestamp'])
            if candles[-1].timestamp != next_ts:
                recovery_events = []
                if book.positions or state['pending']:
                    snap = paper_data['snapshot']
                    if snap is None or not -5 <= int(time.time())-snap.timestamp <= 30:
                        raise DataError('Snapshot atual obrigatório para recuperar gap')
                    # An unobserved interval cannot supply historical stop fills.
                    # Close at the current mark and latch the safety halt.
                    book.halted,book.halt_reason = True,'feed_gap'
                    recovery_events = PaperBroker(book,self.cfg).flatten(
                        snap.price,snap.timestamp,'feed_gap_current_mark',mint=self.cfg.mint)
                    state['pending'] = None
                    state['portfolio'] = book.serialize()
                    state['snapshot'] = asdict(snap)
                    self._remember(state,recovery_events)
                    state['curve'].append(dict(timestamp=snap.timestamp,equity=book.equity(snap.price),
                                               price=snap.price,gross=book.gross(snap.price),net=book.net(snap.price)))
                    state['curve'] = state['curve'][-2000:]
                history = candles[-self.cfg.warmup_bars:]
                if len(history) < self.cfg.warmup_bars or any(
                        right.timestamp != left.timestamp+step for left,right in zip(history,history[1:])):
                    raise ValueError('Gap no feed; candles recentes insuficientes para reaquecer com segurança')
                state['history'] = [asdict(b) for b in history]
                state['last_timestamp'] = history[-1].timestamp
                state['last_price'] = history[-1].close
                state['last_digest'] = hashlib.sha256(canonical(state['history']).encode()).hexdigest()
                state['bars_processed'] = max(state['bars_processed'],self.cfg.warmup_bars)
                self.store.save(db,state)
                self.store.event(db,int(time.time()),'resync_warmup',dict(
                    source='coinbase_advanced_sol_spot',bars=len(history),
                    skipped_bars=max(0,(history[-1].timestamp-next_ts)//step+1),
                    last_timestamp=history[-1].timestamp,events=recovery_events,
                    reason='feed_gap_halted' if book.halted else 'gap_without_open_position'))
                return dict(result='resynchronized',bars=len(history),last_bar=history[-1].timestamp,
                            events=recovery_events,halted=book.halted,
                            next_action='intervenção requerida' if book.halted else 'indicadores reaquecidos; nenhum fill retroativo')
            snap = paper_data['snapshot']
            if snap is None:
                raise ValueError('Snapshot Solana indisponível para a barra fechada; nada foi negociado')
            payload = dict(candle=asdict(bar),snapshot=asdict(snap))
            return self._paper_tick(db,state,book,bar,snap,payload)
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
            a = approve(p,f,s,book,self.cfg,end,instrument=state['universe'].get(b.mint))
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
        if name=='prepare_decision' and paper_data is not None:
            fresh=paper_data.get('snapshot')
            if fresh is not None:
                state['snapshot']=asdict(fresh)
                state['last_price']=fresh.price
        if not state['history'] or not state['snapshot']:
            raise ValueError('Ainda não há feed: envie barras fechadas e snapshot via ingest')
        f = features([Candle(**x) for x in state['history']])
        s = Snapshot(**state['snapshot'])
        # Analysis uses the last closed bar timestamp. Live freshness status separately.
        now = max(state['last_timestamp']+self.cfg.timeframe_seconds,s.timestamp)
        if name == 'prepare_decision':
            if paper_data is not None:
                s=paper_data['snapshot']
                state['snapshot']=asdict(s)
                state['last_price']=s.price
                now=max(now,s.timestamp)
            return self._prepare_external(db,state,book,f,s,now,args)
        if name == 'submit_decision':
            return self._submit_external(db,state,book,f,s,now,args,fresh=(paper_data or {}).get('snapshot'))
        if name == 'analyze':
            if args:
                raise ValueError('analyze não aceita argumentos')
            p,audit = self._decide(state,f,s,book,now)
            self.store.save(db,state)  # analysis never schedules a trade
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

    def _paper_tick(self,db,state,book,b,s,payload):
        """Forward-only spot paper cycle using current Solana pool observations."""
        if b.mint != self.cfg.mint or s.mint != self.cfg.mint or b.chain != 'solana' or s.chain != 'solana':
            raise ValueError('paper_tick aceita somente o mint Solana configurado')
        if s.source != 'coinbase_advanced_sol_spot' or s.product_id!='SOL-USDC':
            raise ValueError('Snapshot não veio do produto Coinbase configurado')
        now = int(time.time())
        if s.timestamp > now+5 or now-s.timestamp > min(30,self.cfg.max_snapshot_age_seconds):
            raise DataError('Snapshot Solana futuro ou stale')
        if b.timestamp+self.cfg.timeframe_seconds > now+5:
            raise ValueError('Barra OHLCV ainda aberta')
        if s.timestamp < b.timestamp+self.cfg.timeframe_seconds:
            raise DataError('Cotação anterior ao fechamento do candle; ciclo bloqueado')
        if state['last_timestamp'] is None or b.timestamp != state['last_timestamp']+self.cfg.timeframe_seconds:
            raise ValueError('Barra paper fora de sequência; sem preenchimentos retroativos')
        digest = hashlib.sha256(canonical(payload).encode()).hexdigest()
        broker = PaperBroker(book,self.cfg)
        events = broker.on_bar(b)
        events.extend(broker.on_mark(s.price,s.timestamp,b.mint))
        equity = update_breakers(book,self.cfg,s.price,s.timestamp)
        if book.halted:
            events.extend(broker.flatten(s.price,s.timestamp,'circuit_breaker',mint=b.mint))
            equity = book.equity(s.price)
        state['history'] = (state['history']+[asdict(b)])[-500:]
        f = features([Candle(**row) for row in state['history']])
        if f.get('ready'):
            broker.trail(s.price,f['atr'],b.mint)
        p,audit = self._decide(state,f,s,book,s.timestamp)
        if int(time.time())-s.timestamp > min(30,self.cfg.max_snapshot_age_seconds):
            audit['error'] = 'Cotação expirou durante a decisão; entrada bloqueada'
            p = replace(Proposal(thesis=audit['error']),mint=b.mint)
        approval = approve(p,f,s,book,self.cfg,s.timestamp,s.price,state['universe'].get(b.mint))
        if p.action == 'CLOSE':
            events.extend(broker.close(pos,s.price,s.timestamp,'agent_exit')
                          for pos in list(book.positions) if pos.market == p.market and pos.mint == b.mint)
        elif p.action in {'LONG','SHORT'} and approval.approved and not book.halted:
            events.append(self._execute_entry(broker,p,approval,s.price,s.timestamp,state,decision_audit=audit,source=s.source))
        decision = dict(timestamp=s.timestamp,mint=b.mint,proposal=asdict(p),
                        approval=asdict(approval),council=audit,
                        diagnostics=dict(ready=f.get('ready',False),regime=f.get('regime'),
                                         rsi=f.get('rsi'),atr_fraction=f.get('atr_fraction'),
                                         candidate_count=len(audit.get('candidates',[])),
                                         snapshot_age_seconds=int(time.time())-s.timestamp),
                        market_data=dict(source=s.source,bar_timestamp=b.timestamp,
                                         observed_at=s.timestamp,fill_model='coinbase_midpoint_plus_configured_costs'))
        state.update(portfolio=book.serialize(),snapshot=asdict(s),last_timestamp=b.timestamp,
                     last_digest=digest,last_price=s.price,bars_processed=state['bars_processed']+1,
                     last_decision=decision)
        state['curve'].append(dict(timestamp=s.timestamp,equity=book.equity(s.price),price=s.price,
                                   gross=book.gross(s.price),net=book.net(s.price)))
        state['curve'] = state['curve'][-2000:]
        self._remember(state,events)
        self.store.save(db,state)
        self.store.event(db,s.timestamp,'cycle',dict(decision=decision,events=events,
                                                     equity=book.equity(s.price)))
        return dict(result='processed',timestamp=b.timestamp,decision=decision,events=events,
                    equity_usdc=book.equity(s.price))
