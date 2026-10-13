import tempfile
import time
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from alladin.engine import Service
from alladin.models import Candle, Config, Proposal, Snapshot, SOL
from alladin.providers import DexScreener, GeckoTerminal
from alladin.risk import security_checks
from alladin.transport import DataError


class ProviderTests(unittest.TestCase):
    def test_dexscreener_filters_chain_and_exact_usdc_pool(self):
        class Http:
            def json(self, *args, **kwargs):
                return [
                    dict(chainId='ethereum', pairAddress='E'*32, baseToken={'address': SOL},
                         quoteToken={'address':'wrong'}, priceNative='1', liquidity={'usd': 99999999}),
                    dict(chainId='solana', pairAddress='S'*32, baseToken={'address': SOL},
                         quoteToken={'address':'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'},
                         priceNative='150', liquidity={'usd': 1000000}, volume={'h24':5000000}),
                ]
        data = DexScreener(Http()).market(SOL)
        self.assertEqual(data['price'],150)
        self.assertEqual(data['source'],'dexscreener_solana_pool_usdc')

    def test_gecko_filters_open_bar_and_rejects_gaps(self):
        now=1800000000
        class Http:
            def json(self,*args,**kwargs):
                return {'data':{'attributes':{'ohlcv_list':[
                    [now-180,100,102,99,101,2000],
                    [now-120,101,103,100,102,2200],
                    [now-60,102,104,101,103,2400],
                    [now,103,105,102,104,2600],
                ]}}}
        bars=GeckoTerminal(Http()).candles('S'*32,count=80,aggregate=1,now=now)
        self.assertEqual([b.timestamp for b in bars],[now-180,now-120,now-60])
        class Gap(Http):
            def json(self,*args,**kwargs):
                return {'data':{'attributes':{'ohlcv_list':[
                    [now-180,100,102,99,101,2000],[now-60,102,104,101,103,2400]
                ]}}}
        with self.assertRaises(DataError):
            GeckoTerminal(Gap()).candles('S'*32,count=80,aggregate=1,now=now)

    def test_perp_not_approved_without_verified_market(self):
        cfg=Config(allowed_markets=('spot',))
        snap=Snapshot(timestamp=1000,price=100,liquidity_usd=10_000_000,
                      volume_24h_usd=50_000_000,account_checked=True,cluster_verified=True)
        self.assertTrue(security_checks(snap,cfg,1000)==[])


class LivePaperTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_warmup_uses_real_feed_and_current_tick_papers_at_live_mark(self):
        now=int(time.time())
        now=(now//60)*60+5
        first=(now//60)*60-81*60
        bars=[Candle(first+i*60,100,101,99,100,10000) for i in range(81)]
        market=dict(pool='P'*32)
        class FixedCouncil:
            mode='rules'
            def decide(self,*args):
                return Proposal('LONG','spot',.8,.02,.06,24,'test candidate','trend_following'),{'mode':'fixture'}
        svc=Service(Config(initial_usdc=250,timeframe_seconds=60,allowed_markets=('spot',)),
                    Path(self.temp.name)/'paper.sqlite',council=FixedCouncil())
        class Dex:
            def market(self,mint):return market
        class Gecko:
            def candles(self,*args,**kwargs):return bars[:80] if len(calls)==0 else bars
        calls=[]
        snap=Snapshot(timestamp=now,mint=SOL,price=100,liquidity_usd=10_000_000,
                      volume_24h_usd=50_000_000,account_checked=True,cluster_verified=True,
                      source='dexscreener_solana_pool_usdc')
        with patch('alladin.engine.DexScreener',Dex), patch('alladin.engine.GeckoTerminal',Gecko), \
             patch('alladin.engine.collect',return_value=snap), patch('alladin.engine.time.time',return_value=now):
            warm=svc.command('paper_tick',{},'warmup')
            self.assertEqual(warm['result'],'warmed_up')
            self.assertEqual(svc.status()['closed_trades'],0)
            self.assertEqual(svc.status()['positions'],[])
            calls.append(1)
            tick=svc.command('paper_tick',{},'bar-1')
        self.assertEqual(tick['result'],'processed')
        self.assertTrue(any(event['event']=='OPEN' for event in tick['events']))
        self.assertEqual(tick['decision']['market_data']['source'],'dexscreener_solana_pool_usdc')
        self.assertFalse(any('signature' in event for event in tick['events']))

    def test_paper_tick_rejects_perp_configuration_before_collection(self):
        with self.assertRaises(ValueError):
            Config(allowed_markets=('spot','perp'))

    def test_gap_without_open_position_rewarms_without_retroactive_fills(self):
        now=int(time.time())
        now=(now//60)*60+5
        first=(now//60)*60-90*60
        bars=[Candle(first+i*60,100+i*.01,101+i*.01,99+i*.01,100+i*.01,10000) for i in range(90)]
        svc=Service(Config(initial_usdc=20,timeframe_seconds=60),Path(self.temp.name)/'gap.sqlite')
        class Sequence:
            calls=0
            def candles(self,*args,**kwargs):
                type(self).calls+=1
                return bars[:80] if type(self).calls==1 else bars
        class Dex:
            def market(self,mint):return dict(pool='P'*32)
        with patch('alladin.engine.DexScreener',Dex), patch('alladin.engine.GeckoTerminal',Sequence), \
             patch('alladin.engine.time.time',return_value=now):
            warmed=svc.command('paper_tick',{},'warm-gap')
            self.assertEqual(warmed['result'],'warmed_up')
            result=svc.command('paper_tick',{},'gap-resync')
        self.assertEqual(result['result'],'resynchronized')
        self.assertEqual(svc.status()['positions'],[])
        self.assertEqual(svc.status()['cash_usdc'],20)
        self.assertEqual(svc.store.audit(1)[0]['kind'],'resync_warmup')


if __name__=='__main__':
    unittest.main()
