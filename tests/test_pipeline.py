"""Offline source-contract integration: no fabricated fixture is a live trade."""
import json
import math
import tempfile
import threading
import unittest
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from unittest.mock import patch
from alladin.models import Config,MAINNET_GENESIS,TOKEN_PROGRAM,Proposal
from alladin.engine import Service
from alladin.client import BackendClient
from alladin.server import build_server
from alladin.mcp_server import handle
from alladin.transport import DataError


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.cfg=replace(Config.load(Path(__file__).resolve().parents[1]/'config.json'),timeframe_seconds=60)
        self.service=Service(self.cfg,Path(self.tmp.name)/'paper.sqlite')
        self.now=1800000065
        self.price=100+.05*79+.12*math.sin(79)
        self.clock=patch('alladin.engine.time.time',return_value=self.now);self.clock.start();self.addCleanup(self.clock.stop)
        self.http=patch('alladin.transport.HTTP.json',side_effect=self.source_json);self.http.start();self.addCleanup(self.http.stop)
        self.last_decision=None

    def source_json(self,url,payload=None,**kwargs):
        self.assertIsNone(payload,'No RPC POST is permitted')
        self.assertEqual(urlsplit(url).hostname,'api.coinbase.com')
        parsed=urlsplit(url);query=parse_qs(parsed.query)
        if parsed.path.endswith('/candles'):
            hour=query['granularity'][0]=='ONE_HOUR';step=3600 if hour else 60;count=26 if hour else 80
            end=self.now//step*step
            return {'candles':[dict(start=str(end-(count-i)*step),open=str(p),high=str(p+.36),
                low=str(p-.36),close=str(p),volume='100000') for i in range(count)
                for p in [100+.05*i+.12*math.sin(i)]]}
        if parsed.path.endswith('/ticker'):
            return {'trades':[{'price':str(self.price),'size':'100','side':side} for side in ('BUY','SELL')]}
        if parsed.path.endswith('/product_book'):
            return {'pricebook':{'product_id':'SOL-USDC','time':datetime.fromtimestamp(self.now,timezone.utc).isoformat(),
                'bids':[{'price':str(self.price-.005),'size':'100000'}],
                'asks':[{'price':str(self.price+.005),'size':'100000'}]}}
        raise AssertionError('Unexpected HTTP source')

    def submission(self,task,action):
        if action=='LONG':
            decision=(dict(task['evidence']['candidates'][0]) if task['evidence']['candidates'] else
                      dict(Proposal('LONG','spot',.8,.01,.026,4,
                           'Offline evidence-backed hypothesis','external_hypothesis').__dict__))
            decision.pop('mint')
            self.last_decision=dict(decision)
        else:decision=dict(self.last_decision,action=action)
        decision.update(evidence_keys=['features.ema_gap','snapshot.price'],invalidation='Fixture trend invalidation',
            entry_conditions=['features.ema_gap'],exit_conditions=['configured_stop','configured_take'],counterevidence_keys=[])
        report=dict(stance=action,score=.8,summary='Offline contract fixture assessment',
            evidence_keys=['features.ema_gap','snapshot.price'],concerns=[],missing_data=[],
            invalidation='Offline fixture changes',risk_flags=[],blocking=False,score_is_probability=False)
        return dict(task_id=task['id'],evidence_sha256=task['evidence_sha256'],session_id='OFFLINE_CONTRACT_FIXTURE',
                    reports={name:dict(report) for name in ('market','quality','flow','challenger')},decision=decision)

    def roundtrip(self,call):
        warm=call('paper_tick',{},'warm');self.assertEqual(warm['result'],'warmed_up')
        first=call('prepare_decision',{},'first')['task']
        self.assertEqual(first['evidence']['features']['regime'],'trend')
        self.assertTrue(first['evidence']['candidate_economics'][0]['approval']['approved'])
        args=self.submission(first,'LONG')
        opened=call('submit_decision',args,'open')
        self.assertEqual(opened['events'][0]['event'],'OPEN',opened)
        self.assertAlmostEqual(self.service.status()['cash_usdc'],0,places=7)
        self.assertLessEqual(opened['decision']['approval']['estimated_stop_loss_usdc'],5)
        self.assertEqual(call('submit_decision',args,'open'),opened)
        second=call('prepare_decision',{},'second')['task']
        args=self.submission(second,'CLOSE');closed=call('submit_decision',args,'close')
        self.assertEqual(closed['events'][0]['event'],'CLOSE')
        self.assertEqual(call('submit_decision',args,'close'),closed)
        status=self.service.status()
        self.assertEqual(status['closed_trades'],1);self.assertEqual(status['positions'],[])
        self.assertGreater(status['costs_usdc'],0);self.assertLess(status['cash_usdc'],250)
        self.assertTrue(self.service.store.verify_audit()['valid'])
        return dict(opened=opened,closed=closed,status=status,audit=self.service.store.verify_audit())

    def test_complete_source_to_http_roundtrip(self):
        server=build_server(self.service,0,token='x'*40)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            client=BackendClient('http://127.0.0.1:'+str(server.server_port),token='x'*40)
            # HTTP wraps command results; the public client must unwrap them.
            self.roundtrip(client.command)
        finally:server.shutdown();server.server_close();thread.join()

    def test_complete_source_to_mcp_roundtrip(self):
        def call(name,args,key):
            response=handle(self.service,{'jsonrpc':'2.0','method':'tools/call','params':{
                'name':name,'arguments':dict(args,idempotency_key=key)}})
            self.assertFalse(response['isError'],response)
            return json.loads(response['content'][0]['text'])
        self.roundtrip(call)

    def test_external_strategy_roundtrip_without_internal_candidate(self):
        with patch('alladin.agents.candidates',return_value=[]):
            self.service.command('paper_tick',{},'warm')
            first=self.service.command('prepare_decision',{},'prepare')['task']
            self.assertEqual(first['evidence']['candidates'],[])
            self.assertTrue(first['evidence']['decision_policy']['external_strategies_allowed'])
            args=self.submission(first,'LONG')
            opened=self.service.command('submit_decision',args,'entry')
            self.assertEqual(opened['events'][0]['event'],'OPEN',opened)
            self.assertEqual(self.service.status()['positions'][0]['strategy'],'external_hypothesis')
            self.assertEqual(self.service.command('submit_decision',args,'entry'),opened)
            second=self.service.command('prepare_decision',{},'exit-task')['task']
            closed=self.service.command('submit_decision',self.submission(second,'CLOSE'),'exit')
            self.assertEqual(closed['events'][0]['event'],'CLOSE',closed)
            self.assertEqual(self.service.status()['positions'],[])
            self.assertEqual(self.service.status()['closed_trades'],1)
            self.assertTrue(self.service.store.verify_audit()['valid'])

    def test_external_strategy_without_baseline_cannot_bypass_risk_or_consensus(self):
        with patch('alladin.agents.candidates',return_value=[]):
            self.service.command('paper_tick',{},'warm')
            for case in ('risk','consensus'):
                task=self.service.command('prepare_decision',{},'prepare-'+case)['task']
                args=self.submission(task,'LONG')
                if case=='risk':
                    args['decision'].update(stop_fraction=.05,take_fraction=.15)
                else:
                    for name in ('market','flow'):args['reports'][name]['stance']='HOLD'
                result=self.service.command('submit_decision',args,'submit-'+case)
                self.assertEqual(result['events'],[],result)
                self.assertEqual(result['decision']['proposal']['action'],'HOLD')
                self.assertEqual(result['decision']['council']['gate'],
                                 'manager_risk_veto' if case=='risk' else 'consensus_abstention')
            self.assertEqual(self.service.status()['cash_usdc'],250)
            self.assertEqual(self.service.status()['positions'],[])

    def test_failed_source_retries_same_key_without_resetting_or_filling(self):
        with patch('alladin.transport.HTTP.json',side_effect=DataError('fixture blocked',code='network_timeout',stage='proxy_tunnel')):
            with self.assertRaises(DataError) as error:self.service.command('paper_tick',{},'recover')
            self.assertEqual(error.exception.source,'coinbase_candles')
        self.assertEqual(self.service.status()['cash_usdc'],250)
        self.assertEqual(self.service.command('paper_tick',{},'recover')['result'],'warmed_up')
        self.assertEqual(self.service.status()['positions'],[])
