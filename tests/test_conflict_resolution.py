import json
import tempfile
import unittest
from dataclasses import asdict,replace
from pathlib import Path
from unittest.mock import patch
from alladin.models import Config
from alladin.engine import Service
from alladin.providers import CoinbaseMarket
from alladin.transport import HTTP_TOTAL_SECONDS,COLLECTION_TOTAL_SECONDS
from alladin.risk import profile_feasibility


class ConflictResolutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'policy.sqlite'
        self.new=Config.load(Path(__file__).resolve().parents[1]/'config.json')
        self.old=replace(self.new,min_reward_risk=1.8)
        self.previous=Service(self.old,self.path)
        with self.previous.store.transaction() as db:
            state=self.previous._load(db)
            state['portfolio'].update(cash=249,fees_paid=1,day='2026-10-14',day_start_equity=250,
                                      peak=252,cooldown_until=123456,total_closed=3)
            state['pending']={'test':'cancel'};state['external_task']={'test':'cancel'}
            self.previous.store.save(db,state)
            self.before=state['portfolio']

    def test_revision_preserves_portfolio_losses_fees_and_cooldown(self):
        service=Service(self.new,self.path)
        result=service.revise_policy(self.old)
        self.assertEqual(result['changes'],{'min_reward_risk':{'before':1.8,'after':1.5}})
        with service.store.connect() as db:state=service._load(db)
        self.assertEqual(state['portfolio'],self.before)
        self.assertIsNone(state['pending']);self.assertIsNone(state['external_task'])
        count=service.store.verify_audit()['count']
        self.assertEqual(service.revise_policy(self.old)['result'],'already_revised')
        self.assertEqual(service.store.verify_audit()['count'],count)
        self.assertTrue(service.store.verify_audit()['valid'])
        with self.assertRaises(ValueError):service.revise_policy(replace(self.old,min_reward_risk=1.9))

    def test_no_implicit_migration_and_no_loss_limit_change(self):
        service=Service(self.new,self.path)
        with self.assertRaises(ValueError):service.status()
        with self.assertRaises(ValueError):service.revise_policy(replace(self.old,risk_per_trade=.03))
        with self.previous.store.connect() as db:self.assertEqual(self.previous._load(db)['portfolio'],self.before)

    def test_wrong_previous_config_and_missing_session_rejected(self):
        service=Service(self.new,self.path)
        with self.assertRaises(ValueError):service.revise_policy(replace(self.old,min_reward_risk=1.9))
        empty=Service(self.new,Path(self.tmp.name)/'empty.sqlite')
        with self.assertRaises(ValueError):empty.revise_policy(self.old)

    def test_limits_and_costs_stay_equal_and_profile_is_feasible(self):
        changed={k for k,v in asdict(self.old).items() if asdict(self.new)[k]!=v}
        self.assertEqual(changed,{'min_reward_risk'})
        self.assertEqual(self.new.risk_per_trade,.02);self.assertEqual(self.new.max_daily_loss,.02)
        self.assertEqual(self.new.max_drawdown,.06)
        self.assertFalse(profile_feasibility(self.old)['baseline_can_fit'])
        self.assertTrue(profile_feasibility(self.new)['baseline_can_fit'])

    def test_provider_and_collection_budgets_cover_observed_slow_market(self):
        self.assertEqual(COLLECTION_TOTAL_SECONDS,45)
        self.assertEqual(HTTP_TOTAL_SECONDS,20)
        self.assertEqual(CoinbaseMarket().http.timeout,20)
        with patch('alladin.engine.deadline') as deadline:
            with self.assertRaises(ValueError):
                Service(self.new,Path(self.tmp.name)/'budget.sqlite').command('paper_tick',{'invalid':True},'bad')
            deadline.assert_called_once_with(45)
        # Existing timeout tests prove nested demo deadlines can be shorter than these defaults.

    def test_doctor_rechecks_candle_age_after_slow_quote_collection(self):
        from alladin.diagnostics import diagnose
        from alladin.models import Candle
        clock=[1000]
        class Provider:
            def candles(self,*args):return [Candle(900,100,101,99,100,1e6)]
            def market(self,*args):
                clock[0]=1030
                return {'observed_at':1030,'price':100,'source':'coinbase_advanced_sol_spot'}
        with patch('alladin.diagnostics.CoinbaseMarket',return_value=Provider()),patch('alladin.diagnostics.time.time',side_effect=lambda:clock[0]):
            result=diagnose(replace(self.new,timeframe_seconds=60))
        self.assertFalse(result['sources_ready'])
        self.assertEqual(result['checks']['coinbase_market']['error']['code'],'stale_data')
