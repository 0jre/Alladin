"""Whole-balance paper sizing keeps explicit loss and exposure gates."""
import hashlib
import unittest
from dataclasses import asdict,replace
from pathlib import Path
import tempfile

from alladin.models import Config,Portfolio,Proposal,Snapshot
from alladin.risk import approve
from alladin.broker import PaperBroker
from alladin.engine import Service
from alladin.storage import canonical


class BalanceSizingTests(unittest.TestCase):
    def setUp(self):
        self.cfg=Config(initial_usdc=250,sizing_mode='available_balance',risk_per_trade=.02,
            max_open_risk=.02,max_position_fraction=1,max_gross_fraction=1,max_net_fraction=1)
        self.book=Portfolio(250,250,250)
        self.book.day_start_equity=250
        self.snap=Snapshot(1000,price=100,liquidity_usd=10_000_000,volume_24h_usd=50_000_000,
                           account_checked=True,cluster_verified=True)
        self.features=dict(ready=True,regime='trend',cvar95_bar=.001,price=100)
        self.proposal=Proposal('LONG','spot',.8,.01,.04,24,'fixture','test')

    def approval(self,cfg=None,book=None,snap=None,proposal=None,now=1000):
        return approve(proposal or self.proposal,self.features,snap or self.snap,book or self.book,cfg or self.cfg,now)

    def test_spends_balance_after_reserving_entry_costs(self):
        result=self.approval()
        self.assertTrue(result.approved,result.reasons)
        self.assertAlmostEqual(result.notional,249.98/1.0015)
        self.assertLessEqual(result.estimated_stop_loss_usdc,5)
        PaperBroker(self.book,self.cfg).open(self.proposal,result,100,1000)
        self.assertAlmostEqual(self.book.cash,0)
        self.assertGreaterEqual(self.book.cash,0)
        self.assertGreater(self.book.positions[0].qty*100,249)

    def test_second_entry_uses_updated_balance_after_costs_and_cooldown(self):
        broker=PaperBroker(self.book,self.cfg)
        broker.open(self.proposal,self.approval(),100,1000)
        broker.close(self.book.positions[0],100,1100,'controlled_test')
        balance=self.book.cash
        self.assertLess(balance,250)
        next_ts=self.book.cooldown_until+1
        result=self.approval(snap=replace(self.snap,timestamp=next_ts),now=next_ts)
        self.assertTrue(result.approved,result.reasons)
        self.assertAlmostEqual(result.notional,(balance-.02)/1.0015)
        broker.open(self.proposal,result,100,next_ts)
        self.assertAlmostEqual(self.book.cash,0)

    def test_full_position_rejected_instead_of_downsized_for_wide_stop(self):
        result=self.approval(proposal=replace(self.proposal,stop_fraction=.02,take_fraction=.06))
        self.assertFalse(result.approved)
        self.assertEqual(result.reasons,('balance_size_exceeds_loss_budget',))
        self.assertEqual(result.notional,0)

    def test_remaining_daily_budget_blocks_entry_before_limit_is_reached(self):
        self.book.cash=246
        result=self.approval()
        self.assertFalse(result.approved)
        self.assertEqual(result.reasons,('balance_size_exceeds_loss_budget',))

    def test_exposure_limit_is_not_bypassed(self):
        result=self.approval(cfg=replace(self.cfg,max_position_fraction=.15))
        self.assertFalse(result.approved)
        self.assertEqual(result.reasons,('balance_size_exceeds_exposure_limit',))

    def test_liquidity_participation_limit_is_not_bypassed(self):
        result=self.approval(cfg=replace(self.cfg,max_pool_participation=.00001))
        self.assertFalse(result.approved)
        self.assertEqual(result.reasons,('balance_size_exceeds_liquidity_limit',))

    def test_invalid_sizing_profile_rejected(self):
        with self.assertRaises(ValueError):Config(sizing_mode='unlimited')

    def test_existing_risk_budget_fingerprint_is_unchanged(self):
        cfg=Config(initial_usdc=250)
        legacy=asdict(cfg);legacy.pop('sizing_mode')
        with tempfile.TemporaryDirectory() as tmp:
            service=Service(cfg,Path(tmp)/'legacy.sqlite')
            self.assertEqual(service.fingerprint,hashlib.sha256(canonical(legacy).encode()).hexdigest())


if __name__=='__main__':unittest.main()
