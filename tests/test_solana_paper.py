import tempfile
import time
import unittest
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from alladin.engine import Service
from alladin.models import Candle, Config, Proposal, Snapshot, SOL, TOKEN_PROGRAM, MAINNET_GENESIS
from alladin.providers import CoinbaseMarket, SolanaRPC
from alladin.risk import security_checks
from alladin.transport import DataError


class ProviderTests(unittest.TestCase):
    def test_native_sol_rpc_skips_irrelevant_holder_concentration_calls(self):
        class RPC(SolanaRPC):
            def __init__(self):
                self.methods=[]
            def call(self,method,params=None):
                self.methods.append(method)
                if method=='getGenesisHash':return MAINNET_GENESIS
                if method=='getAccountInfo':
                    return {'value':{'owner':TOKEN_PROGRAM,'data':{'parsed':{'type':'mint','info':{
                        'isInitialized':True,'mintAuthority':None,'freezeAuthority':None}}}},
                        'context':{'slot':123}}
                raise AssertionError(f'unexpected RPC call: {method}')
        rpc=RPC()
        result=rpc.inspect(SOL)
        self.assertEqual(rpc.methods,['getGenesisHash','getAccountInfo'])
        self.assertIsNone(result['top10_account_share'])
        self.assertEqual(result['slot'],123)

    def test_coinbase_product_is_fixed_to_usdc_quoted_sol(self):
        with self.assertRaises(ValueError):
            CoinbaseMarket(product_id='SOL-USD')

    def test_coinbase_filters_open_bar_and_rejects_gaps(self):
        now=1800000000
        class Http:
            def json(self,*args,**kwargs):
                return {'candles':[
                    {'start':now-180,'open':100,'high':102,'low':99,'close':101,'volume':20},
                    {'start':now-120,'open':101,'high':103,'low':100,'close':102,'volume':22},
                    {'start':now-60,'open':102,'high':104,'low':101,'close':103,'volume':24},
                    {'start':now,'open':103,'high':105,'low':102,'close':104,'volume':26},
                ]}
        bars=CoinbaseMarket(Http()).candles(SOL,count=80,aggregate=60,now=now)
        self.assertEqual([b.timestamp for b in bars],[now-180,now-120,now-60])
        self.assertEqual(bars[0].volume,2020)
        class Gap(Http):
            def json(self,*args,**kwargs):
                return {'candles':[
                    {'start':now-180,'open':100,'high':102,'low':99,'close':101,'volume':20},
                    {'start':now-60,'open':102,'high':104,'low':101,'close':103,'volume':24},
                ]}
        with self.assertRaises(DataError):
            CoinbaseMarket(Gap()).candles(SOL,count=80,aggregate=60,now=now)

    def test_coinbase_market_uses_public_book_depth_and_taker_imbalance(self):
        class Http:
            def json(self,url,**kwargs):
                if '/product_book?' in url:
                    return {'pricebook':{'bids':[{'price':'149.9','size':'10'}],
                                         'asks':[{'price':'150.1','size':'10'}]}}
                return {'trades':[{'price':'150','size':'2','side':'SELL'},
                                  {'price':'150','size':'1','side':'BUY'}]}
        now=int(time.time())
        start=now-86400
        candles=[Candle(start+i*900,150,151,149,150,10) for i in range(97)]
        with patch('alladin.providers.time.time',return_value=now):
            data=CoinbaseMarket(Http()).market(SOL,candles=candles,timeframe_seconds=900)
        self.assertEqual(data['price'],150)
        self.assertAlmostEqual(data['buy_sell_imbalance'],1/3)
        self.assertEqual(data['liquidity_usd'],3000)
        self.assertEqual(data['volume_24h_usd'],970)
        self.assertEqual(data['source'],'coinbase_advanced_sol_spot')

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
        market=dict(price=100,liquidity_usd=10_000_000,volume_24h_usd=50_000_000,
                    buy_sell_imbalance=0,source='coinbase_advanced_sol_spot')
        class FixedCouncil:
            mode='rules'
            def decide(self,*args):
                return Proposal('LONG','spot',.8,.02,.06,24,'test candidate','trend_following'),{'mode':'fixture'}
        svc=Service(Config(initial_usdc=250,timeframe_seconds=60,allowed_markets=('spot',)),
                    Path(self.temp.name)/'paper.sqlite',council=FixedCouncil())
        class FakeCoinbase:
            calls=0
            def __init__(self,*args):pass
            def candles(self,*args,**kwargs):
                type(self).calls+=1
                return bars[:80] if type(self).calls==1 else bars
            def market(self,*args,**kwargs):return market
        snap=Snapshot(timestamp=now,mint=SOL,price=100,liquidity_usd=10_000_000,
                      volume_24h_usd=50_000_000,account_checked=True,cluster_verified=True,
                      source='coinbase_advanced_sol_spot')
        with patch('alladin.engine.CoinbaseMarket',return_value=FakeCoinbase(bars,market)), \
             patch('alladin.engine.collect',return_value=snap), patch('alladin.engine.time.time',return_value=now):
            warm=svc.command('paper_tick',{},'warmup')
            self.assertEqual(warm['result'],'warmed_up')
            self.assertEqual(svc.status()['closed_trades'],0)
            self.assertEqual(svc.status()['positions'],[])
            tick=svc.command('paper_tick',{},'bar-1')
        self.assertEqual(tick['result'],'processed')
        self.assertTrue(any(event['event']=='OPEN' for event in tick['events']))
        self.assertEqual(tick['decision']['market_data']['source'],'coinbase_advanced_sol_spot')
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
        market=dict(price=100,liquidity_usd=10_000_000,volume_24h_usd=50_000_000,
                    buy_sell_imbalance=0,source='coinbase_advanced_sol_spot')
        class FakeCoinbase(Sequence):
            def market(self,*args,**kwargs):return market
        with patch('alladin.engine.CoinbaseMarket',FakeCoinbase), \
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
