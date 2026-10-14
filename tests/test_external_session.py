"""External chat sessions supply reasoning; backend supplies deterministic gates."""
import json
import tempfile
import unittest
from dataclasses import asdict,replace
from pathlib import Path
from unittest.mock import patch
from alladin.engine import Service
from alladin.models import Candle,Config,Snapshot
from alladin.mcp_server import handle
from test_finance_prompts import fixture,ModelFixture


class ExternalSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.f,self.s,self.book,self.cfg=fixture()
        self.path=Path(self.tmp.name)/'external.sqlite'
        self.service=Service(self.cfg,self.path)
        with self.service.store.transaction() as db:
            state=self.service._load(db)
            state.update(history=[asdict(Candle(100,100,101,99,100,10000))],
                         snapshot=asdict(self.s),last_timestamp=100,last_price=100,
                         bars_processed=80,input_mode='replay')
            self.service.store.save(db,state)
        self.clock=patch('alladin.engine.time.time',return_value=1000);self.clock.start();self.addCleanup(self.clock.stop)
        self.features=patch('alladin.engine.features',return_value=self.f);self.features.start();self.addCleanup(self.features.stop)
        self.candles=patch('alladin.providers.CoinbaseMarket.candles',return_value=[Candle(100,100,101,99,100,10000)])
        self.candles.start();self.addCleanup(self.candles.stop)

    def prepare(self):
        return self.service.command('prepare_decision',{},'prepare')['task']

    def submission(self,task):
        fake=ModelFixture();env=task['evidence'];reports={}
        for role in ['market','quality','flow','challenger']:
            reports[role]=fake.ask('',env,{},role)
        decision=fake.ask('',env,{},'manager')
        return dict(task_id=task['id'],evidence_sha256=task['evidence_sha256'],
                    session_id='chat-session-fixture',reports=reports,decision=decision)

    def test_default_external_has_no_inference_client(self):
        self.assertEqual(self.service.council.mode,'external')
        self.assertFalse(hasattr(self.service.council,'client'))
        with patch('alladin.transport.HTTP.json',side_effect=AssertionError('No inference')):
            task=self.prepare()
        self.assertEqual(task['status'],'prepared')
        self.assertEqual(task['stages'],[['market','quality','flow'],['challenger'],['manager']])
        self.assertIsNone(self.service.status()['pending'])

    def test_restart_and_idempotent_commit_no_duplicate_trade(self):
        task=self.prepare();args=self.submission(task)
        self.service=Service(self.cfg,self.path)
        result=self.service.command('submit_decision',args,'submit')
        self.assertEqual(result['decision']['proposal']['action'],'LONG',result)
        self.assertEqual(self.service.command('submit_decision',args,'submit'),result)
        self.assertIsNotNone(self.service.status()['pending'])
        with self.assertRaises(ValueError):self.service.command('submit_decision',args,'different')
        self.assertTrue(self.service.store.verify_audit()['valid'])

    def test_expired_task_and_forged_hash_are_rejected(self):
        task=self.prepare();args=self.submission(task)
        with patch('alladin.engine.time.time',return_value=task['expires_at']+1):
            with self.assertRaises(ValueError):self.service.command('submit_decision',args,'expired')
        args['evidence_sha256']='f'*64
        with self.assertRaises(ValueError):self.service.command('submit_decision',args,'forged')
        self.assertIsNone(self.service.status()['pending'])

    def test_halt_and_portfolio_changes_invalidate_context(self):
        task=self.prepare();args=self.submission(task)
        self.service.command('halt',{},'halt')
        with self.assertRaises(ValueError):self.service.command('submit_decision',args,'submit')
        self.assertIsNone(self.service.status()['pending'])

    def test_bad_plan_consumed_as_abstention(self):
        args=self.submission(self.prepare());args['decision']['notional']=250
        result=self.service.command('submit_decision',args,'bad-plan')
        self.assertEqual(result['decision']['proposal']['action'],'HOLD')
        self.assertIn('error',result['decision']['council'])
        self.assertIsNone(self.service.status()['pending'])

    def test_new_preparation_reuses_current_task(self):
        old=self.prepare()
        new=self.service.command('prepare_decision',{},'new-prepare')
        self.assertTrue(new['reused'])
        self.assertEqual(old['id'],new['task']['id'])
        self.assertEqual(self.service.command('submit_decision',self.submission(old),'old')['result'],'submitted')

    def test_mcp_exposes_external_session_protocol(self):
        result=handle(self.service,{'jsonrpc':'2.0','method':'tools/list'})
        self.assertTrue({'prepare_decision','submit_decision'}<={t['name'] for t in result['tools']})
        result=handle(self.service,{'jsonrpc':'2.0','method':'tools/call','params':{
            'name':'prepare_decision','arguments':{'idempotency_key':'prepare'}}})
        self.assertFalse(result['isError'])
        self.assertEqual(json.loads(result['content'][0]['text'])['task']['protocol'],'external-session-v2')

    def live(self):
        with self.service.store.transaction() as db:
            state=self.service._load(db);state['input_mode']='paper_live'
            state['snapshot']['source']='coinbase_advanced_sol_spot'
            self.service.store.save(db,state)
        fresh=replace(self.s,source='coinbase_advanced_sol_spot',product_id='SOL-USDC')
        return patch('alladin.engine.collect',return_value=fresh)

    def test_first_prepare_uses_collected_snapshot_after_warmup(self):
        with self.service.store.transaction() as db:
            state=self.service._load(db);state['snapshot']=None;state['input_mode']='paper_live'
            self.service.store.save(db,state)
        with patch('alladin.engine.collect',return_value=replace(self.s,source='coinbase_advanced_sol_spot',product_id='SOL-USDC')):
            task=self.prepare()
        self.assertEqual(task['status'],'prepared')
        self.assertEqual(task['evidence']['snapshot']['source'],'coinbase_advanced_sol_spot')

    def test_live_refresh_executes_once_and_records_session(self):
        with self.live() as collect:
            task=self.prepare();args=self.submission(task)
            with patch('alladin.engine.time.time',return_value=1100),patch('alladin.engine.collect',return_value=replace(self.s,timestamp=1100,source='coinbase_advanced_sol_spot',product_id='SOL-USDC')):
                result=self.service.command('submit_decision',args,'submit')
                again=self.service.command('submit_decision',args,'submit')
            self.assertEqual(result,again)
            self.assertEqual(len(result['events']),1,result)
            self.assertEqual(result['events'][0]['decision_context']['session_id'],'chat-session-fixture')
            self.assertEqual(len(self.service.status()['positions']),1)

    def test_live_external_open_close_roundtrip_accounts_for_costs(self):
        with self.live():
            first=self.prepare()
            opened=self.service.command('submit_decision',self.submission(first),'roundtrip-open')
            self.assertEqual(opened['events'][0]['event'],'OPEN')
            second=self.service.command('prepare_decision',{},'roundtrip-next')['task']
            args=self.submission(second)
            args['decision']['action']='CLOSE'
            closed=self.service.command('submit_decision',args,'roundtrip-close')
        self.assertEqual(closed['events'][0]['event'],'CLOSE')
        status=self.service.status()
        self.assertEqual(status['positions'],[])
        self.assertEqual(status['closed_trades'],1)
        self.assertGreater(status['costs_usdc'],0)
        self.assertLess(status['cash_usdc'],250)
        self.assertTrue(self.service.store.verify_audit()['valid'])

    def test_live_changed_price_rejects_instead_of_filling_stale_context(self):
        with self.live():task=self.prepare()
        fresh=replace(self.s,timestamp=1100,price=105,source='coinbase_advanced_sol_spot',product_id='SOL-USDC')
        with patch('alladin.engine.time.time',return_value=1100),patch('alladin.engine.collect',return_value=fresh):
            result=self.service.command('submit_decision',self.submission(task),'deviation')
            self.assertEqual(result['result'],'reprepare_required')
            self.assertEqual(self.service.status()['external_task']['status'],'invalidated')
            new=self.service.command('prepare_decision',{},'after-deviation')['task']
            self.assertNotEqual(new['id'],task['id'])
        self.assertEqual(self.service.status()['positions'],[])

    def test_live_stale_closed_risk_data_blocks_entry(self):
        fresh=replace(self.s,timestamp=1800,source='coinbase_advanced_sol_spot',product_id='SOL-USDC')
        with self.live(),patch('alladin.engine.time.time',return_value=1800),patch('alladin.engine.collect',return_value=fresh):
            task=self.prepare()
        with patch('alladin.engine.time.time',return_value=2000),patch('alladin.engine.collect',return_value=replace(fresh,timestamp=2000)),patch('alladin.providers.CoinbaseMarket.candles',return_value=[Candle(0,100,101,99,100,10000)]):
            from alladin.transport import DataError
            with self.assertRaisesRegex(DataError,'Closed feed'):
                self.service.command('submit_decision',self.submission(task),'stale-bars')

    def test_live_stale_execution_quote_blocks_entry(self):
        with self.live():task=self.prepare()
        with patch('alladin.engine.time.time',return_value=1100),patch('alladin.engine.collect',return_value=replace(self.s,source='coinbase_advanced_sol_spot',product_id='SOL-USDC')):
            from alladin.transport import DataError
            with self.assertRaises(DataError):self.service.command('submit_decision',self.submission(task),'stale')
        self.assertEqual(self.service.status()['positions'],[])

    def test_runtime_source_contains_no_embedded_inference_endpoint(self):
        root=Path(__file__).resolve().parents[1]/'alladin'
        source='\n'.join(p.read_text() for p in root.glob('*.py'))
        for forbidden in ['OPENAI_API_KEY','OPENAI_MODEL','api.openai.com','OpenAIJSON','max_llm_calls']:
            self.assertNotIn(forbidden,source)
