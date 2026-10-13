import copy
import io
import json
import math
import os
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from dataclasses import asdict,replace
from unittest.mock import patch
from pathlib import Path

from alladin.models import *
from alladin.features import features
from alladin.risk import approve,Approval,security_checks,update_breakers
from alladin.broker import PaperBroker
from alladin.agents import Council,OpenAIJSON,validate_report
from alladin.engine import Service
from alladin.research import demo_feed,export
from alladin.server import build_server
from alladin.transport import DataError,HTTP

class Transport429Tests(unittest.TestCase):
    def test_retries_upstream_429_after_retry_after(self):
        sleeps=[]
        calls=[]
        def open_request(request,timeout):
            calls.append(1)
            if len(calls)==1:
                raise urllib.error.HTTPError(request.full_url,429,'rate limited',
                                             {'Retry-After':'2'},io.BytesIO(b''))
            return io.BytesIO(b'{"ok":true}')
        with patch('alladin.transport.urllib.request.build_opener') as build:
            build.return_value.open.side_effect=open_request
            result=HTTP(retries=2,retry_cap=8,sleeper=sleeps.append,
                        random_value=lambda:0).json('https://api.example.test/data')
        self.assertEqual(result,{'ok':True})
        self.assertEqual(len(calls),2)
        self.assertEqual(sleeps,[2])

    def test_persistent_upstream_429_becomes_generic_data_error(self):
        calls=[]
        def open_request(request,timeout):
            calls.append(1)
            raise urllib.error.HTTPError(request.full_url,429,'rate limited',
                                         {'Retry-After':'20'},io.BytesIO(b''))
        with patch('alladin.transport.urllib.request.build_opener') as build:
            build.return_value.open.side_effect=open_request
            with self.assertRaises(DataError) as raised:
                HTTP(retries=3,retry_cap=8,sleeper=lambda _:self.fail('must not sleep'),
                     random_value=lambda:0).json('https://api.example.test/data')
        self.assertEqual(len(calls),1)
        self.assertEqual(raised.exception.retry_after,20)
        self.assertNotIn('429',str(raised.exception))

def feature_fixture():
    return dict(ready=True,price=100,regime='trend',cvar95_bar=.01,atr=1,
                atr_fraction=.01,ema_gap=.01,higher_trend=.01,momentum_12=.03,
                rsi=60,efficiency=.5,volume_ratio=1,breakout_high=110,breakout_low=90)

def snapshot(ts=1000,price=100):
    return Snapshot(ts,price=price,liquidity_usd=10_000_000,volume_24h_usd=50_000_000,
                    account_checked=True,cluster_verified=True,oracle_price=price,
                    oracle_timestamp=ts,expected_funding_hourly=.00001,
                    perp_market_verified=True,source='TEST_FIXTURE')

def proposal(market='spot',action='LONG'):
    return Proposal(action,market,.8,.02,.06,24,'Test','trend_following')

class ModelAndFeatureTests(unittest.TestCase):
    def test_only_solana(self):
        with self.assertRaises(ValueError):
            Config(chain='bitcoin')
        with self.assertRaises(ValueError):
            Candle(0,1,1,1,1,1,chain='bitcoin')
        with self.assertRaises(ValueError):
            Config(chain='base')
    def test_no_live_mode(self):
        with self.assertRaises(ValueError):
            Config(execution='live')
    def test_reject_nan(self):
        with self.assertRaises(ValueError):
            Proposal(confidence=float('nan'))
        with self.assertRaises(ValueError):
            Candle(0,100,float('inf'),99,100,1)
    def test_reject_bad_ohlc(self):
        with self.assertRaises(ValueError):
            Candle(0,100,99,90,98,1)
    def test_security_flags_must_be_boolean(self):
        with self.assertRaises(ValueError):
            replace(snapshot(),account_checked='false')
    def test_pubkey(self):
        self.assertEqual(pubkey(SOL),SOL)
        self.assertEqual(pubkey(USDC),USDC)
        with self.assertRaises(ValueError):
            pubkey('a'*44)
    def test_constant_price_features(self):
        f = features([Candle(i*900,100,100,100,100,10) for i in range(80)])
        self.assertEqual(f['rsi'],50)
        self.assertEqual(f['regime'],'range')
        self.assertEqual(f['cvar95_bar'],0)
    def test_indicator_prefix_causal(self):
        rows = list(demo_feed(200))
        f = features([b for b,s in rows[:100]])
        other = [b for b,s in rows[:100]]+[Candle(999999,1000,1000,1000,1000,10)]
        self.assertEqual(f,features(other[:100]))

class RiskTests(unittest.TestCase):
    def setUp(self):
        self.cfg=Config();self.book=Portfolio(10000,10000,10000)
        self.f=feature_fixture();self.s=snapshot()
    def test_approval_budget(self):
        a=approve(proposal(),self.f,self.s,self.book,self.cfg,1000)
        self.assertTrue(a.approved)
        self.assertLessEqual(a.notional,1500)
        self.assertLessEqual(a.estimated_stop_loss_usdc,30.000001)
    def test_stale_and_future(self):
        self.assertFalse(approve(proposal(),self.f,self.s,self.book,self.cfg,5000).approved)
        self.assertFalse(approve(proposal(),self.f,self.s,self.book,self.cfg,900).approved)
    def test_mint_authority_block(self):
        self.assertIn('active_token_authority',security_checks(replace(self.s,mint_authority=USDC),self.cfg,1000))
    def test_missing_security_block(self):
        a=approve(proposal(),self.f,replace(self.s,account_checked=False),self.book,self.cfg,1000)
        self.assertFalse(a.approved)
    def test_perp_missing_oracle_block(self):
        a=approve(proposal('perp'),self.f,replace(self.s,oracle_price=None),self.book,self.cfg,1000)
        self.assertIn('market_not_enabled',a.reasons)
    def test_oracle_deviation_block(self):
        a=approve(proposal('perp'),self.f,replace(self.s,oracle_price=90),self.book,self.cfg,1000)
        self.assertIn('market_not_enabled',a.reasons)
    def test_funding_erodes_edge(self):
        a=approve(proposal('perp'),self.f,replace(self.s,expected_funding_hourly=.01),self.book,self.cfg,1000)
        self.assertIn('market_not_enabled',a.reasons)
    def test_short_spot_block(self):
        self.assertFalse(approve(proposal('spot','SHORT'),self.f,self.s,self.book,self.cfg,1000).approved)
    def test_halt_latches_after_day_change(self):
        self.book.peak=11000
        update_breakers(self.book,self.cfg,100,1000)
        self.assertTrue(self.book.halted)
        update_breakers(self.book,self.cfg,100,100000)
        self.assertTrue(self.book.halted)
    def test_combined_exposure(self):
        self.book.cash=8500
        self.book.positions=[Position('p','spot',1,15,100,98,106,0,0,99999,'x',0)]
        a=approve(proposal('perp'),self.f,self.s,self.book,self.cfg,1000)
        self.assertIn('market_not_enabled',a.reasons)
    def test_gap_recheck(self):
        a=approve(proposal(),self.f,self.s,self.book,self.cfg,1000,103)
        self.assertIn('reference_price_deviation',a.reasons)

class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.cfg=Config(fee_bps=0,slippage_bps=0,fixed_cost_usdc=0)
        self.book=Portfolio(10000,10000,10000)
        self.broker=PaperBroker(self.book,self.cfg)
    def open(self,market='spot',side='LONG'):
        self.broker.open(proposal(market,side),Approval(True,(),1000,2),100,1000)
        return self.book.positions[0]
    def test_spot_equity_and_roundtrip(self):
        p=self.open()
        self.assertEqual(self.book.equity(100),10000)
        self.assertEqual(self.book.equity(110),10100)
        self.broker.close(p,110,2000,'test')
        self.assertEqual(self.book.cash,10100)
        self.assertEqual(self.book.closed[0]['net_pnl'],100)
    def test_perp_short_accounting(self):
        p=self.open('perp','SHORT')
        self.assertEqual(self.book.equity(90),10100)
        self.broker.close(p,90,2000,'test')
        self.assertEqual(self.book.cash,10100)
    def test_both_stop_and_take_stop_first(self):
        self.open()
        e=self.broker.on_bar(Candle(1900,100,108,97,100,10))
        self.assertEqual(e[0]['reason'],'stop')
        self.assertEqual(e[0]['price'],98)
    def test_gap_stop_worse_fill(self):
        self.open()
        e=self.broker.on_bar(Candle(1900,90,92,89,91,10))
        self.assertEqual(e[0]['price'],90)
        self.assertEqual(e[0]['reason'],'gap_stop')
    def test_funding_long_pays_short_receives(self):
        self.open('perp')
        e=self.broker.on_bar(Candle(1900,100,101,99,100,10,.001))
        self.assertEqual(e[0]['amount'],1)
        self.assertEqual(self.book.equity(100),9999)
        self.broker.flatten(100,2000,'test')
        self.assertEqual(self.book.closed[0]['net_pnl'],-1)
    def test_liquidation_gap_caps_collateral(self):
        self.open('perp')
        self.broker.on_bar(Candle(1900,10,11,9,10,1))
        self.assertEqual(self.book.cash,9500)
    def test_duplicate_position_refused(self):
        self.open()
        with self.assertRaises(ValueError):
            self.open()

class AgentTests(unittest.TestCase):
    def test_report_invented_evidence(self):
        r=dict(stance='HOLD',score=.5,summary='x',evidence_keys=['invented'],concerns=[])
        with self.assertRaises(DataError):
            validate_report(r,{'price'})
    def test_no_key_no_silent_rule_fallback(self):
        with patch.dict(os.environ,{},clear=True):
            p,a=Council('llm').decide(feature_fixture(),snapshot(),Portfolio(10000,10000,10000),Config(),1000)
        self.assertEqual(p.action,'HOLD')
        self.assertIn('error',a)
    def test_llm_budget(self):
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test','OPENAI_MODEL':'test'}):
            client=OpenAIJSON(max_calls=0)
            with self.assertRaises(DataError):
                client.ask('test',{}, {},'test')
    def test_structured_council(self):
        class Fake:
            calls=0
            def ask(self,role,evidence,schema,name):
                if name=='manager':
                    d=asdict(proposal())
                    d.pop('mint',None)
                    return d
                return dict(stance='LONG',score=.8,summary='Brief assessment',evidence_keys=['price'],concerns=[])
        p,a=Council('llm',client=Fake()).decide(feature_fixture(),snapshot(),Portfolio(10000,10000,10000),Config(),1000)
        self.assertEqual(p.action,'LONG')
        self.assertEqual(len(a['reports']),5)
    def test_refusal_holds(self):
        class FakeHTTP:
            def json(self,*args,**kwargs):
                return {'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'x'}]}]}
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test','OPENAI_MODEL':'test'}):
            c=OpenAIJSON(http=FakeHTTP())
            with self.assertRaises(DataError):
                c.ask('test',{}, {},'test')

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'test.sqlite'
        self.service=Service(Config(),self.path)
        self.first=next(demo_feed())
    def tearDown(self):self.temp.cleanup()
    def ingest(self,b,s,key):
        return self.service.command('ingest',{'candle':asdict(b),'snapshot':asdict(s)},key)
    def test_idempotency_and_restart(self):
        b,s=self.first
        a=self.ingest(b,s,'one');c=self.ingest(b,s,'one')
        self.assertEqual(a,c)
        self.assertEqual(len(self.service.store.audit()),1)
        restarted=Service(Config(),self.path)
        self.assertEqual(restarted.status()['bars_processed'],1)
    def test_entry_only_on_next_bar(self):
        class FixedCouncil:
            mode='rules'
            client=type('Client',(),{'calls':0})()
            def decide(self,f,s,book,cfg,now):
                return proposal(),{'mode':'test'}
        self.service=Service(Config(),self.path,council=FixedCouncil())
        rows=[(Candle(1767225600+i*900,100,100.5,99.5,100,100000),snapshot(1767225600+(i+1)*900)) for i in range(81)]
        for i,(b,s) in enumerate(rows[:80]):
            r=self.ingest(b,s,str(i))
        self.assertEqual(len(self.service.status()['positions']),0)
        self.assertEqual(self.service.status()['pending']['decision_at'],rows[80][0].timestamp)
        r=self.ingest(*rows[80],'80')
        self.assertTrue(any(e['event']=='OPEN' for e in r['events']))
        self.assertEqual(self.service.status()['positions'][0]['opened_at'],rows[80][0].timestamp)
    def test_current_snapshot_cannot_authorize_past_entry(self):
        class FixedCouncil:
            mode='rules'
            client=type('Client',(),{'calls':0})()
            def decide(self,f,s,book,cfg,now):
                return proposal(),{'mode':'test'}
        self.service=Service(Config(),self.path,council=FixedCouncil())
        rows=[(Candle(1767225600+i*900,100,100.5,99.5,100,100000),snapshot(1767225600+(i+1)*900)) for i in range(81)]
        for i,(b,s) in enumerate(rows[:80]):self.ingest(b,s,str(i))
        b,s=rows[80]
        # Previous price was 100: gap to 105 must fail even if new snapshot is 105.
        r=self.ingest(replace(b,open=105,high=105.5,low=104.5,close=105),replace(s,price=105,oracle_price=105),'80')
        self.assertFalse(any(e['event']=='OPEN' for e in r['events']))
    def test_conflicting_key_refused(self):
        b,s=self.first
        self.ingest(b,s,'one')
        with self.assertRaises(ValueError):
            self.ingest(replace(b,volume=b.volume+1),s,'one')
    def test_duplicate_bar_different_key(self):
        b,s=self.first
        self.ingest(b,s,'one')
        self.assertEqual(self.ingest(b,s,'two')['result'],'duplicate_bar')
    def test_gap_rejected_transaction_rolls_back(self):
        b,s=self.first
        self.ingest(b,s,'one')
        with self.assertRaises(ValueError):
            self.ingest(replace(b,timestamp=b.timestamp+1800),replace(s,timestamp=s.timestamp+1800),'two')
        self.assertEqual(self.service.status()['bars_processed'],1)
    def test_future_snapshot_rejected(self):
        b,s=self.first
        with self.assertRaises(ValueError):
            self.ingest(b,replace(s,timestamp=s.timestamp+1),'one')
    def test_config_change_refused(self):
        b,s=self.first
        self.ingest(b,s,'one')
        with self.assertRaises(ValueError):
            Service(Config(initial_usdc=2000),self.path).status()
    def test_feed_prefix_independent_of_future(self):
        rows=list(demo_feed(130))
        other=Service(Config(),Path(self.temp.name)/'other.sqlite')
        for i,(b,s) in enumerate(rows[:100]):
            a=self.ingest(b,s,str(i))
            c=other.command('ingest',dict(candle=asdict(b),snapshot=asdict(s)),str(i))
            self.assertEqual(a,c)
        self.assertEqual(self.service.status(),other.status())
    def test_halt_clears_pending(self):
        b,s=self.first
        self.ingest(b,s,'one')
        self.service.command('halt',{},'halt')
        self.assertTrue(self.service.status()['halted'])
        self.assertIsNone(self.service.status()['pending'])

class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.token='x'*40
        self.service=Service(Config(),Path(self.temp.name)/'http.sqlite')
        self.server=build_server(self.service,0,self.token)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join();self.temp.cleanup()
    def request(self,path,body=None,auth=True,key='test'):
        headers={'Content-Type':'application/json','Idempotency-Key':key}
        if auth:headers['Authorization']='Bearer '+self.token
        data=None if body is None else json.dumps(body).encode()
        req=urllib.request.Request(self.url+path,data=data,headers=headers)
        return urllib.request.urlopen(req,timeout=5)
    def test_auth_required(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.request('/v1/status',auth=False)
        self.assertEqual(e.exception.code,401)
    def test_health_and_json_contract(self):
        with self.request('/health',auth=False) as r:
            body=json.load(r)
            self.assertEqual(body['execution'],'paper')
        self.assertEqual(body['venue'],'coinbase_advanced')
        with self.request('/v1/contract') as r:self.assertIn('ingest',json.load(r)['commands'])
    def test_unknown_command_not_shell(self):
        with self.assertRaises(urllib.error.HTTPError) as e:
            self.request('/v1/commands',{'command':'exec','args':{'cmd':'ls'}})
        self.assertEqual(e.exception.code,400)
    def test_idempotent_http_ingest(self):
        b,s=next(demo_feed())
        body={'command':'ingest','args':{'candle':asdict(b),'snapshot':asdict(s)}}
        with self.request('/v1/commands',body) as r:a=json.load(r)
        with self.request('/v1/commands',body) as r:c=json.load(r)
        self.assertEqual(a,c)
        self.assertEqual(self.service.status()['bars_processed'],1)
    def test_provider_throttle_never_leaks_as_429(self):
        with patch('alladin.server.execute',side_effect=DataError(
                'Fonte de dados temporariamente indisponível',retry_after=5)):
            with self.assertRaises(urllib.error.HTTPError) as raised:
                self.request('/v1/commands',{'command':'paper_tick','args':{}})
        self.assertEqual(raised.exception.code,503)
        body=json.loads(raised.exception.read())
        self.assertEqual(body['error'],'provider_unavailable')
        self.assertEqual(body['retry_after_seconds'],5)
        self.assertNotIn('429',json.dumps(body))

if __name__=='__main__':unittest.main()
