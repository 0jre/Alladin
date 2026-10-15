"""Native-engine tests require the pinned Alladin engine extra."""
from dataclasses import replace
import importlib.util
import subprocess
from types import SimpleNamespace
from unittest.mock import patch
import unittest

import test_spot_portfolio as fixture
from alladin.spot_engine import SpotService
from alladin.spot_policy import dec,SpotPolicy
from alladin.nautilus_engine import execute
from alladin.execution_core import fill

AVAILABLE=importlib.util.find_spec('nautilus_trader') is not None


@unittest.skipUnless(AVAILABLE,'Install alladin[engine] to run native integration')
class NativeTests(fixture.SpotTests):
    def setUp(self):
        super().setUp()
        self.cfg=replace(self.cfg,execution_engine='nautilus')
        self.s=SpotService(self.cfg,self.tmp.name+'/native.sqlite',self.market,self.clock)

    def test_native_engine_is_the_source_of_execution_events(self):
        r=self.buy('DOGE-USDC')
        self.assertEqual(r['order']['engine'],'nautilus_trader')
        self.assertEqual(r['order']['engine_version'],'1.231.0')
        self.assertTrue(r['order']['native_fills'])
        r=self.call('close_position',dict(product_id='DOGE-USDC'))
        self.assertEqual(r['order']['engine'],'nautilus_trader')
        self.assertTrue(self.call('reconcile')['valid'])

    def test_native_cash_account_refuses_overspend(self):
        i=self.market.instrument('BTC-USDC')
        with self.assertRaisesRegex(ValueError,'NAUTILUS_REJECTED'):
            execute(i,self.market.book('BTC-USDC'),'BUY','1',{'USDC':'1'},'20','too-large')


class BoundaryTests(unittest.TestCase):
    def test_native_crash_and_timeout_never_fall_back(self):
        cfg=SpotPolicy()
        state={'balances':{'USDC':'250'},'positions':{}}
        with patch('alladin.execution_core.subprocess.run',return_value=SimpleNamespace(returncode=134)):
            with self.assertRaisesRegex(ValueError,'PROCESS_FAILED'):
                fill(cfg,state,{}, {},'BUY','1','id',{'vwap':'1'})
        with patch('alladin.execution_core.subprocess.run',side_effect=subprocess.TimeoutExpired('native',15)):
            with self.assertRaisesRegex(ValueError,'TIMEOUT'):
                fill(cfg,state,{}, {},'BUY','1','id',{'vwap':'1'})


if __name__=='__main__':unittest.main()
