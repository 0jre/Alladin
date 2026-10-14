"""Operational regressions: fixtures test execution, not market profitability."""
import io
import json
import tempfile
import threading
import os
import subprocess
import sys
from dataclasses import asdict
from concurrent.futures import ThreadPoolExecutor
import time
import unittest
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime,timezone

from alladin.models import Config,Candle,Snapshot,Proposal,Portfolio,SOL
from alladin.engine import Service
from alladin.broker import PaperBroker
from alladin.risk import Approval,approve
from alladin.providers import CoinbaseMarket,collect
from alladin.runtime import PaperRunner
from alladin.transport import HTTP,DataError
from alladin.storage import canonical


class OperationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'session.sqlite'
        self.cfg=Config(initial_usdc=250,timeframe_seconds=60)

    def test_replayed_paper_request_does_not_need_network(self):
        service=Service(self.cfg,self.path)
        with service.store.transaction() as db:
            result=service.store.once(db,'saved',dict(command='paper_tick',args={}),lambda:{'result':'warmed_up'})
        with patch.object(service,'_collect_paper_data',side_effect=AssertionError('network used')):
            self.assertEqual(service.command('paper_tick',{},'saved'),result)
            with self.assertRaises(ValueError):
                service.command('paper_tick',{'bad':True},'saved')

    def test_halt_does_not_wait_for_market_network_collection(self):
        service=Service(self.cfg,self.path)
        entered=threading.Event();release=threading.Event()
        def collect(args):
            entered.set();release.wait(5);raise DataError('fixture unavailable')
        def tick():
            try:service.command('paper_tick',{},'slow')
            except DataError:pass
        with patch.object(service,'_collect_paper_data',side_effect=collect):
            thread=threading.Thread(target=tick)
            thread.start()
            try:
                self.assertTrue(entered.wait(2))
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future=pool.submit(service.command,'halt',{},'stop')
                    try:
                        self.assertEqual(future.result(timeout=1)['result'],'halted')
                    finally:release.set()
            finally:release.set();thread.join(3)
        self.assertTrue(service.status()['halted'])

    def test_worker_rejects_invalid_timeframe_before_start(self):
        service=Service(Config(timeframe_seconds=45),self.path)
        with self.assertRaisesRegex(ValueError,'candles'):PaperRunner(service)

    def test_invalid_key_rejected_before_network(self):
        service=Service(self.cfg,self.path)
        with patch.object(service,'_collect_paper_data',side_effect=AssertionError('network used')):
            with self.assertRaises(ValueError):
                service.command('paper_tick',{},'')

    def test_partial_bar_does_not_trigger_stop_before_entry(self):
        book=Portfolio(250,250,250)
        broker=PaperBroker(book,self.cfg)
        broker.open(Proposal('LONG','spot',.8,.02,.06,24,'fixture','test'),Approval(True,(),20),100,1050)
        self.assertEqual(broker.on_bar(Candle(1020,100,101,90,100,1000)),[])
        self.assertEqual(broker.on_mark(100,1080),[])
        event=broker.on_mark(97,1090)[0]
        self.assertEqual(event['reason'],'observed_stop')
        self.assertEqual(event['price'],97)
        self.assertEqual(event['closed_at'],1090)

    def test_small_account_reward_risk_includes_fixed_roundtrip_fees(self):
        snap=Snapshot(1000,price=100,liquidity_usd=10_000_000,volume_24h_usd=50_000_000,
                      account_checked=True,cluster_verified=True)
        proposal=Proposal('LONG','spot',.8,.01,.029,24,'fixture','test')
        result=approve(proposal,dict(ready=True,regime='trend',cvar95_bar=.01,price=100),
                       snap,Portfolio(250,250,250),self.cfg,1000)
        self.assertFalse(result.approved)
        self.assertEqual(result.reasons,('reward_risk_after_fixed_costs',))

    def test_paper_roundtrip_250_persists_and_restarts_without_duplicate_fills(self):
        class Council:
            mode='rules'
            def decide(self,*args):
                return Proposal('LONG','spot',.8,.02,.06,24,'fixture','test'),{'mode':'fixture'}
        now=1800000065
        bars=[Candle(1800000000-80*60+i*60,100,101,99,100,10000) for i in range(81)]
        snap=Snapshot(now,price=100,liquidity_usd=10_000_000,volume_24h_usd=50_000_000,
                      account_checked=True,cluster_verified=True,source='coinbase_advanced_sol_spot')
        service=Service(self.cfg,self.path,council=Council())
        with patch.object(service,'_collect_paper_data',return_value={'candles':bars[:80],'snapshot':None}),patch('alladin.engine.time.time',return_value=now-60):
            service.command('paper_tick',{},'warm')
        with patch.object(service,'_collect_paper_data',return_value={'candles':bars,'snapshot':snap}),patch('alladin.engine.time.time',return_value=now):
            opened=service.command('paper_tick',{},'open')
        self.assertEqual(opened['events'][0]['event'],'OPEN')
        # Restart, observe a stop at the current quote in the overlapping bar.
        service=Service(self.cfg,self.path,council=Council())
        later=now+60
        later_snap=Snapshot(later,price=97,liquidity_usd=10_000_000,volume_24h_usd=50_000_000,
                           account_checked=True,cluster_verified=True,source='coinbase_advanced_sol_spot')
        bars=bars+[Candle(bars[-1].timestamp+60,100,101,96,97,10000)]
        with patch.object(service,'_collect_paper_data',return_value={'candles':bars,'snapshot':later_snap}),patch('alladin.engine.time.time',return_value=later):
            closed=service.command('paper_tick',{},'close')
            duplicate=service.command('paper_tick',{},'close')
        self.assertEqual(closed,duplicate)
        self.assertEqual(service.status()['closed_trades'],1)
        self.assertEqual(closed['events'][0]['reason'],'observed_stop')
        self.assertLess(service.status()['cash_usdc'],250)
        self.assertTrue(service.store.verify_audit()['valid'])

    def test_gap_with_position_closes_at_current_mark_and_latches_halt(self):
        service=Service(self.cfg,self.path)
        now=1800000065
        bars=[Candle(1800000000-80*60+i*60,100,101,99,100,10000) for i in range(85)]
        with service.store.transaction() as db:
            state=service._load(db)
            book=Portfolio.restore(state['portfolio'])
            PaperBroker(book,self.cfg).open(Proposal('LONG','spot',.8,.02,.06,24,'fixture','test'),Approval(True,(),20),100,now-100)
            state.update(portfolio=book.serialize(),last_timestamp=bars[0].timestamp-600,history=[b.__dict__ for b in bars[:81]])
            service.store.save(db,state)
        snap=Snapshot(now+180,price=95,liquidity_usd=10_000_000,volume_24h_usd=50_000_000,
                      account_checked=True,cluster_verified=True,source='coinbase_advanced_sol_spot')
        with patch.object(service,'_collect_paper_data',return_value={'candles':bars,'snapshot':snap}),patch('alladin.engine.time.time',return_value=now+180):
            result=service.command('paper_tick',{},'recover')
        self.assertTrue(result['halted'])
        self.assertEqual(result['events'][0]['price'],95)
        self.assertEqual(result['events'][0]['reason'],'feed_gap_current_mark')
        self.assertEqual(service.status()['positions'],[])
        self.assertEqual(service.status()['halt_reason'],'feed_gap')

    def test_do_not_mix_live_and_replay_sessions(self):
        service=Service(self.cfg,self.path)
        with service.store.transaction() as db:
            state=service._load(db);state['input_mode']='paper_live';service.store.save(db,state)
        with self.assertRaisesRegex(ValueError,'misture'):
            service.command('ingest',{},'replay')

    def test_slow_council_blocks_entry_but_preserves_call_budget(self):
        now=1800000065
        bars=[Candle(1800000000-80*60+i*60,100,101,99,100,10000) for i in range(81)]
        snap=Snapshot(now,price=100,liquidity_usd=10_000_000,volume_24h_usd=50_000_000,
                      account_checked=True,cluster_verified=True,source='coinbase_advanced_sol_spot')
        service=Service(self.cfg,self.path)
        with patch.object(service,'_collect_paper_data',return_value={'candles':bars[:80],'snapshot':None}),patch('alladin.engine.time.time',return_value=now-60):
            service.command('paper_tick',{},'warm')
        clock=[now]
        def decide(state,*args):
            state['llm_calls']=5
            clock[0]+=31
            return Proposal('LONG','spot',.8,.02,.06,24,'fixture','test'),{}
        with patch.object(service,'_collect_paper_data',return_value={'candles':bars,'snapshot':snap}), \
             patch.object(service,'_decide',side_effect=decide),patch('alladin.engine.time.time',side_effect=lambda:clock[0]):
            result=service.command('paper_tick',{},'slow')
        self.assertEqual(result['decision']['proposal']['action'],'HOLD')
        self.assertIn('expirou',result['decision']['council']['error'])
        self.assertEqual(service.status()['llm_calls_persisted'],5)
        self.assertEqual(service.status()['positions'],[])

    def test_stale_wrong_product_and_nonfinite_books_are_rejected(self):
        now=1800000000
        for product,observed,bid in [('BTC-USD',now,'99'),('SOL-USDC',now-100,'99'),('SOL-USDC',now,'NaN')]:
            class Http:
                def json(self,url,**kwargs):
                    if '/ticker?' in url:return {'trades':[{'price':'100','size':'1','side':'BUY'}]}
                    return {'pricebook':{'product_id':product,
                        'time':datetime.fromtimestamp(observed,timezone.utc).isoformat(),
                        'bids':[{'price':bid,'size':'10'}],'asks':[{'price':'101','size':'10'}]}}
            provider=CoinbaseMarket(Http())
            with patch('alladin.providers.time.time',return_value=now),patch.object(provider,'_volume',return_value=10000000):
                with self.assertRaises(DataError):provider.market()

    def test_retry_after_nonfinite_is_ignored(self):
        for value in ('NaN','Infinity','-Infinity','not-a-date'):
            error=urllib.error.HTTPError('https://example.test',429,'limit',{'Retry-After':value},io.BytesIO())
            self.assertIsNone(HTTP._retry_after(error))
        with self.assertRaises(ValueError):HTTP(timeout=float('nan'))

    def test_market_timestamp_is_not_rejuvenated_by_rpc_delay(self):
        fake=SimpleNamespace(inspect=lambda mint:{'mint_authority':None,'freeze_authority':None,
            'top10_account_share':None,'token_program':'x','slot':1,'warnings':[]})
        with patch('alladin.providers.time.time',return_value=200):
            with self.assertRaises(DataError):collect(rpc=fake,market={'observed_at':100,'price':100})

    def test_volume_cache_uses_only_completed_24_hour_window(self):
        now=1800000000//3600*3600+30
        provider=CoinbaseMarket()
        bars=[Candle(now//3600*3600-26*3600+i*3600,100,101,99,100,10) for i in range(26)]
        with patch('alladin.providers.time.time',return_value=now),patch.object(provider,'candles',return_value=bars) as fetch:
            self.assertEqual(provider._volume([],60),240)
            self.assertEqual(provider._volume([],60),240)
            self.assertEqual(fetch.call_count,1)

    def test_worker_failure_exits_server_for_supervisor_restart(self):
        cfg_path=Path(self.tmp.name)/'config.json'
        cfg_path.write_text(json.dumps(asdict(self.cfg)))
        script="""
import sys
from unittest.mock import patch
from alladin.__main__ import main
sys.argv=['alladin','--config',sys.argv[1],'--db',sys.argv[2],'serve','--port','0','--paper-worker']
with patch('alladin.runtime.PaperRunner.run',side_effect=RuntimeError('fixture failure')):
    raise SystemExit(main())
"""
        process=subprocess.run([sys.executable,'-c',script,str(cfg_path),str(self.path)],
            capture_output=True,text=True,timeout=10,env={**os.environ,'LAB_API_TOKEN':'x'*40})
        self.assertEqual(process.returncode,1,process.stderr)
        self.assertIn('worker_failed',process.stdout)
        self.assertNotIn('Traceback',process.stderr)

    def test_sigterm_stops_server_cleanly_and_preserves_sqlite(self):
        cfg_path=Path(self.tmp.name)/'config.json'
        cfg_path.write_text(json.dumps(asdict(self.cfg)))
        process=subprocess.Popen([sys.executable,'-m','alladin','--config',str(cfg_path),
            '--db',str(self.path),'serve','--port','0'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,env={**os.environ,'LAB_API_TOKEN':'x'*40})
        try:
            line=process.stdout.readline()
            self.assertEqual(json.loads(line)['status'],'listening')
            process.terminate()
            _,error=process.communicate(timeout=10)
            self.assertEqual(process.returncode,0,error)
            self.assertTrue(Service(self.cfg,self.path).store.verify_audit()['valid'])
        finally:
            if process.poll() is None:process.kill();process.communicate()

    def test_worker_retries_same_key_and_waits_after_completion(self):
        class Stop:
            def __init__(self):self.waits=[]
            def is_set(self):return False
            def wait(self,delay):self.waits.append(delay);return False
        keys=[]
        def command(name,args,key):
            keys.append(key)
            if len(keys)==1:raise DataError('busy',retry_after=40)
            return {'result':'processed'}
        stop=Stop()
        service=SimpleNamespace(store=SimpleNamespace(path=self.path),command=command)
        runner=PaperRunner(service,10,stop_event=stop,emit=lambda _:None)
        runner.run(max_cycles=1)
        self.assertEqual(keys[0],keys[1])
        self.assertEqual(stop.waits,[40])
        self.assertFalse(runner.health()['running'])
        self.assertEqual(runner.health()['failures'],0)

    def test_worker_lease_blocks_duplicate_and_releases_after_stop(self):
        entered=threading.Event();release=threading.Event()
        def command(*args):entered.set();release.wait(5);return {'result':'processed'}
        service=SimpleNamespace(store=SimpleNamespace(path=self.path),command=command)
        first=PaperRunner(service,10,emit=lambda _:None)
        thread=threading.Thread(target=lambda:first.run(1))
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            second=PaperRunner(service,10,emit=lambda _:None)
            with self.assertRaisesRegex(ValueError,'worker'):second.run(1)
        finally:
            release.set();thread.join(3)
        self.assertFalse(thread.is_alive())
        second.run(1)


if __name__=='__main__':unittest.main()
