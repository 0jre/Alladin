"""Explicit controlled paper validation, kept separate from alpha decisions."""
import json
from dataclasses import asdict,replace
from unittest.mock import patch
from alladin.models import Proposal,Snapshot,Candle
from alladin.transport import DataError
from alladin.mcp_server import handle
from test_pipeline import PipelineTests


class ExecutionCheckTests(PipelineTests):
    def args(self,action='OPEN'):
        d=dict(action=action,check_id='explicit-test',purpose='execution_validation')
        if action=='OPEN':
            d['proposal']=asdict(Proposal('LONG','spot',.75,.013,.0286,1,
                'Controlled execution validation, no alpha claim','execution_validation'))
        return d

    def test_controlled_roundtrip_full_balance_and_statistics_separated(self):
        opened=self.service.command('execution_check',self.args(),'check-open')
        self.assertEqual(opened['events'][0]['event'],'OPEN')
        self.assertEqual(opened['events'][0]['source'],'controlled_execution_check')
        self.assertEqual(opened['events'][0]['quote_source'],'coinbase_advanced_sol_spot')
        self.assertTrue(opened['events'][0]['approval']['approved'])
        self.assertLessEqual(opened['events'][0]['approval']['estimated_stop_loss_usdc'],5)
        self.assertEqual(opened['events'][0]['proposal']['strategy'],'execution_validation')
        self.assertAlmostEqual(self.service.status()['cash_usdc'],0,places=7)
        self.assertEqual(self.service.command('execution_check',self.args(),'check-open'),opened)
        with self.assertRaises(ValueError):self.service.command('execution_check',self.args(),'double')
        closed=self.service.command('execution_check',self.args('CLOSE'),'check-close')
        self.assertEqual(closed['events'][0]['event'],'CLOSE')
        self.assertEqual(self.service.status()['positions'],[])
        self.assertEqual(self.service.command('execution_check',self.args('CLOSE'),'check-close'),closed)
        stats=self.service.performance()
        self.assertEqual(stats['execution_validation_roundtrips'],1)
        self.assertEqual(stats['closed_roundtrips'],0)
        self.assertFalse(stats['target']['measured_claim_supported'])
        self.assertTrue(self.service.store.verify_audit()['valid'])
        with self.service.store.connect() as db:self.assertEqual(self.service._load(db)['memory'],[])

    def test_invalid_intent_and_excessive_risk_cannot_open(self):
        args=self.args();args['purpose']='profit'
        with self.assertRaises(ValueError):self.service.command('execution_check',args,'bad-intent')
        args=self.args();args['proposal']['stop_fraction']=.05;args['proposal']['take_fraction']=.11
        with self.assertRaises(ValueError):self.service.command('execution_check',args,'bad-risk')
        self.assertEqual(self.service.status()['cash_usdc'],250)
        self.assertEqual(self.service.status()['positions'],[])

    def test_replay_and_live_execution_are_rejected(self):
        with self.service.store.transaction() as db:
            state=self.service._load(db);state['input_mode']='replay';self.service.store.save(db,state)
        with self.assertRaises(ValueError):self.service.command('execution_check',self.args(),'replay')

    def test_wrong_check_id_does_not_close_position(self):
        self.service.command('execution_check',self.args(),'open')
        args=self.args('CLOSE');args['check_id']='wrong'
        with self.assertRaises(ValueError):self.service.command('execution_check',args,'wrong-close')
        self.assertEqual(len(self.service.status()['positions']),1)
        self.service.command('execution_check',self.args('CLOSE'),'close')

    def test_mcp_execution_check_uses_same_risk_and_broker(self):
        for action,key in [('OPEN','open'),('CLOSE','close')]:
            result=handle(self.service,{'jsonrpc':'2.0','method':'tools/call','params':{
                'name':'execution_check','arguments':{**self.args(action),'idempotency_key':key}}})
            self.assertFalse(result['isError'],result)
        self.assertEqual(self.service.status()['closed_trades'],1)

    def test_no_new_candle_still_observes_position_stop(self):
        self.service.command('execution_check',self.args(),'open')
        fresh=Snapshot(self.now,price=self.price*.97,source='coinbase_advanced_sol_spot',
                       product_id='SOL-USDC',liquidity_usd=1e7,volume_24h_usd=5e7)
        with self.service.store.connect() as db:
            state=self.service._load(db);bars=[Candle(**x) for x in state['history']]
        with patch.object(self.service,'_collect_paper_data',return_value={'candles':bars,'snapshot':fresh}):
            result=self.service.command('paper_tick',{},'mark-stop')
        self.assertEqual(result['result'],'waiting_for_closed_bar')
        self.assertEqual(result['events'][0]['reason'],'observed_stop')
        self.assertEqual(self.service.status()['positions'],[])
        self.service.command('execution_check',self.args('CLOSE'),'cleanup')

    def test_stale_quote_cannot_fill_and_recovery_reuses_key(self):
        with patch('alladin.engine.collect',return_value=Snapshot(self.now-100,price=100,
            source='coinbase_advanced_sol_spot',product_id='SOL-USDC',liquidity_usd=1e7,volume_24h_usd=5e7)):
            with self.assertRaises(DataError):self.service.command('execution_check',self.args(),'retry')
        self.assertEqual(self.service.status()['positions'],[])
        self.service.command('execution_check',self.args(),'retry')
        self.service.command('execution_check',self.args('CLOSE'),'close')

    def test_prepare_reuses_recent_coinbase_observation_without_new_collection(self):
        self.service.command('paper_tick',{},'warm')
        first=self.service.command('prepare_decision',{},'first')['task']
        with patch('alladin.engine.collect',side_effect=AssertionError('redundant collection')):
            second=self.service.command('prepare_decision',{},'second')['task']
        self.assertEqual(first['evidence']['snapshot']['timestamp'],second['evidence']['snapshot']['timestamp'])
        self.assertEqual(first['id'],second['id'])

    def test_absence_of_signal_is_not_a_transport_or_economic_failure(self):
        self.service.command('paper_tick',{},'warm')
        from alladin.features import features
        with self.service.store.connect() as db:state=self.service._load(db)
        f=features([Candle(**x) for x in state['history']])
        f.update(regime='range',efficiency=.4,rsi=50,zscore=0)
        with patch('alladin.engine.features',return_value=f):
            result=self.service.command('prepare_decision',{},'no-signal')
        self.assertEqual(result['result'],'awaiting_external_agents')
        self.assertEqual(result['task']['evidence']['candidates'],[])
        self.assertTrue(result['task']['evidence']['decision_policy']['external_strategies_allowed'])
        self.assertEqual(self.service.status()['positions'],[])
