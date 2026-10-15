"""Synthetic fixtures exercise accounting and risk, never demonstrate alpha."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal as D
import json
from pathlib import Path
import tempfile
import threading
import unittest

from alladin.spot_engine import SpotService
from alladin.spot_policy import SpotPolicy, dec
from alladin.spot_market import walk
from alladin.transport import DataError


class Market:
    def __init__(self,clock):
        self.clock=clock
        self.prices={'BTC-USDC':'60000','DOGE-USDC':'.12','SHIB-USDC':'.00002',
                     'ETH-EUR':'3000','EUR-USDC':'1.10'}
        self.base={'BTC-USDC':'BTC','DOGE-USDC':'DOGE','SHIB-USDC':'SHIB','ETH-EUR':'ETH','EUR-USDC':'EUR'}
        self.quotes={k:('EUR' if k=='ETH-EUR' else 'USDC') for k in self.prices}
        self.depth={}
        self.error=False
        self.stale=False
        self.kind={}

    def instrument(self,pid):
        return dict(product_id=pid,product_type=self.kind.get(pid,'SPOT'),status='online',
            base_currency_id=self.base[pid],quote_currency_id=self.quotes[pid],base_increment='0.00000001',
            quote_increment='0.00000001',price_increment='0.000000000001',
            base_min_size='0.00000001',base_max_size='1000000000000',quote_min_size='.01',quote_max_size='10000000',
            price=self.prices[pid],price_percentage_change_24h='5',volume_24h='1000000000000000')

    def catalog(self,refresh=False):
        return dict(products=[self.instrument(pid) for pid in self.prices],catalog_sha256='fixture',observed_at=self.clock())

    def book(self,pid):
        if self.error:raise DataError('fixture transport outage')
        price=dec(self.prices[pid]);bid=price*D('.9999');ask=price*D('1.0001')
        t=self.clock()-(100 if self.stale else 0)
        timestamp=datetime.fromtimestamp(t,timezone.utc).isoformat()
        levels=dict(product_id=pid,time=timestamp,bids=[dict(price=str(bid),size=self.depth.get(pid,'1000000000000'))],
                    asks=[dict(price=str(ask),size=self.depth.get(pid,'1000000000000'))])
        return dict(product_id=pid,source_time=timestamp,bid=str(bid),ask=str(ask),pricebook=levels)

    def observation(self,pid,timeframe=300):
        p=float(self.prices[pid])
        return dict(product_id=pid,instrument=self.instrument(pid),book=self.book(pid),last_closed_at=self.clock(),
            volume_24h_quote='1000000000000',spread_bps='2',features=dict(atr=p*.02,ema_gap=.01,momentum_12=.02,
                rsi=60,regime='trend',volume_ratio=1.5,efficiency=.6,atr_fraction=.02,returns=[.0001*i for i in range(64)]))


class SpotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.now=1792017000
        self.clock=lambda:self.now
        self.market=Market(self.clock)
        self.cfg=SpotPolicy(initial_balances={'USDC':'1000'},execution_engine='reference')
        self.s=SpotService(self.cfg,Path(self.tmp.name)/'a.sqlite',self.market,self.clock)
        self.n=0

    def call(self,name,args=None,key=None):
        self.n+=1
        return self.s.command(name,args or {},key or 'k'+str(self.n))

    def propose(self,pid='DOGE-USDC',**extra):
        price=dec(self.market.prices[pid])
        thesis=self.call('log_thesis',dict(product_id=pid,agent_id='session',strategy='trend',
            thesis='Fixture trend evidence',invalidation='Fixture stop',horizon_seconds=300))['thesis']
        args=dict(thesis_id=thesis['id'],stop_price=str(price*D('.98')),
            take_profit_price=str(price*D('1.08')),risk_fraction='.005')
        args.update(extra)
        return self.call('propose_trade',args)['proposal']

    def buy(self,pid='DOGE-USDC'):
        p=self.propose(pid)
        return self.call('commit_trade',dict(proposal_id=p['id']))

    def test_multiple_tokens_share_one_balance_and_correct_net_pnl(self):
        self.buy('DOGE-USDC');self.buy('SHIB-USDC')
        self.assertEqual(len(self.s.status()['positions']),2)
        remaining=dec(self.s.status()['balances']['USDC'])
        self.assertGreater(remaining,0)
        self.assertLess(remaining,1000)
        self.market.prices['DOGE-USDC']='.13'
        sold=self.call('close_position',dict(product_id='DOGE-USDC'))
        self.assertGreater(dec(sold['order']['realized_pnl']),0)
        self.assertEqual(len(self.s.status()['positions']),1)
        self.assertTrue(self.s.store.verify_audit()['valid'])
        for e in self.s.store.audit():
            if 'postings' in e['payload']:
                totals={}
                for p in e['payload']['postings']:totals[p['currency']]=totals.get(p['currency'],D(0))+dec(p['amount'])
                self.assertFalse(any(totals.values()))

    def test_idempotent_commit_survives_new_key_and_restart(self):
        p=self.propose()
        a=self.call('commit_trade',dict(proposal_id=p['id']),key='once')
        b=self.call('commit_trade',dict(proposal_id=p['id']),key='once')
        self.assertEqual(a,b)
        self.s=SpotService(self.cfg,self.s.store.path,self.market,self.clock)
        c=self.call('commit_trade',dict(proposal_id=p['id']))
        self.assertEqual(c['result'],'already_committed')
        self.assertEqual(len(self.s._state()['fills']),1)
        with self.assertRaises(ValueError):self.call('commit_trade',dict(proposal_id='different'),key='once')

    def test_expiry_drift_and_stale_data_never_fill(self):
        p=self.propose();self.now+=31
        with self.assertRaisesRegex(ValueError,'EXPIRED'):self.call('commit_trade',dict(proposal_id=p['id']))
        p=self.propose();self.market.prices['DOGE-USDC']='.125'
        with self.assertRaisesRegex(ValueError,'PRICE_MOVED'):self.call('commit_trade',dict(proposal_id=p['id']))
        self.market.stale=True
        with self.assertRaises(DataError):self.propose('BTC-USDC')
        self.assertEqual(self.s.status()['positions'],[])

    def test_outage_retry_same_request_is_safe(self):
        p=self.propose();self.market.error=True
        args=dict(proposal_id=p['id'])
        with self.assertRaises(DataError):self.call('commit_trade',args,key='retry')
        self.market.error=False
        self.assertEqual(self.call('commit_trade',args,key='retry')['result'],'filled')
        self.assertEqual(len(self.s._state()['fills']),1)

    def test_halt_blocks_entry_but_allows_risk_reduction(self):
        self.buy();p=self.propose('BTC-USDC')
        self.call('halt_trading')
        with self.assertRaises(ValueError):self.call('commit_trade',dict(proposal_id=p['id']))
        self.call('close_position',dict(product_id='DOGE-USDC'))
        self.assertEqual(self.s.status()['positions'],[])
        self.assertTrue(self.s.status()['halted'])

    def test_protection_time_exit_and_stale_exit(self):
        self.buy()
        self.market.stale=True
        with self.assertRaises(DataError):self.call('close_position',dict(product_id='DOGE-USDC'))
        self.market.stale=False
        self.now+=301
        result=self.call('paper_tick')
        self.assertEqual(result['events'][0]['order']['reason'],'time_exit')
        self.assertEqual(self.s.status()['positions'],[])

    def test_observed_stop_uses_current_bid_not_historical_stop(self):
        self.buy();self.market.prices['DOGE-USDC']='.10'
        r=self.call('paper_tick')
        self.assertEqual(r['events'][0]['order']['reason'],'observed_stop')
        self.assertLess(dec(r['events'][0]['order']['price']),D('.11'))
        self.assertTrue(self.s.status()['halted'])  # actual gap loss exceeds daily floor

    def test_stop_cannot_loosen(self):
        self.buy()
        with self.assertRaisesRegex(ValueError,'RISK_INCREASE'):
            self.call('set_protection',dict(product_id='DOGE-USDC',stop_price='.10'))
        self.call('set_protection',dict(product_id='DOGE-USDC',stop_price='.119'))
        self.assertEqual(dec(self.s.status()['positions'][0]['stop_price']),D('.119'))

    def test_shared_revision_invalidates_parallel_proposals(self):
        a=self.propose('DOGE-USDC');b=self.propose('BTC-USDC')
        self.call('commit_trade',dict(proposal_id=a['id']))
        with self.assertRaisesRegex(ValueError,'INVALIDATED'):self.call('commit_trade',dict(proposal_id=b['id']))
        self.assertEqual(len(self.s.status()['positions']),1)

    def test_dry_run_cannot_mutate_cash_positions_or_audit(self):
        p=self.propose();before=self.s._state();audit=self.s.store.verify_audit()
        r=self.call('commit_trade',dict(proposal_id=p['id'],dry_run=True))
        self.assertEqual(r['result'],'dry_run')
        self.assertEqual(self.s._state(),before)
        self.assertEqual(self.s.store.verify_audit(),audit)

    def test_strict_fields_and_no_nan_or_unknown_types(self):
        for value in ('NaN','Infinity',True,'-1'):
            with self.assertRaises(ValueError):self.propose(risk_fraction=value)
        self.market.kind['DOGE-USDC']='FUTURE'
        with self.assertRaisesRegex(ValueError,'PRODUCT_BLOCKED'):self.propose()
        with self.assertRaises(ValueError):self.call('halt_trading',dict(ignore_risk=True))

    def test_partial_depth_reject_or_explicit_accept(self):
        self.market.depth['DOGE-USDC']='10'
        with self.assertRaisesRegex(ValueError,'INSUFFICIENT_DEPTH'):self.propose()
        p=self.propose(partial_fill_policy='ACCEPT')
        self.call('commit_trade',dict(proposal_id=p['id']))
        self.assertEqual(dec(self.s.status()['positions'][0]['quantity']),10)
        self.market.depth['DOGE-USDC']='4'
        r=self.call('close_position',dict(product_id='DOGE-USDC'))
        self.assertEqual(r['result'],'partially_closed')
        self.assertEqual(dec(self.s.status()['positions'][0]['quantity']),6)

    def test_scan_includes_memecoins_without_token_allowlist(self):
        r=self.call('scan_opportunities',dict(product_ids=['DOGE-USDC','SHIB-USDC'],limit=2))
        self.assertEqual({x['product_id'] for x in r['candidates']},{'DOGE-USDC','SHIB-USDC'})
        self.assertTrue(all(x['eligible_for_proposal'] for x in r['candidates']))
        self.assertFalse(r['automatic_execution'])

    def test_non_reporting_quote_is_not_assumed_equal(self):
        cfg=replace(self.cfg,initial_balances={'EUR':'1000'})
        self.s=SpotService(cfg,Path(self.tmp.name)/'eur.sqlite',self.market,self.clock)
        self.buy('ETH-EUR')
        status=self.s.status()
        self.assertEqual(set(status['balances']),{'EUR'})
        self.assertGreater(dec(status['equity_reporting']),1090)
        self.assertLess(dec(status['equity_reporting']),1100)

    def test_unfunded_quote_cannot_spend_usdc_as_eur(self):
        with self.assertRaises(ValueError):self.propose('ETH-EUR')
        self.assertEqual(self.s.status()['balances'],{'USDC':'1000'})

    def test_concurrent_commit_does_not_duplicate_fill(self):
        p=self.propose();results=[]
        def run(i):
            try:results.append(self.s.command('commit_trade',dict(proposal_id=p['id']),'thread'+str(i)))
            except ValueError as e:results.append(str(e))
        threads=[threading.Thread(target=run,args=(i,)) for i in range(2)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(len(self.s._state()['fills']),1)
        self.assertTrue(self.s.store.verify_audit()['valid'])

    def test_internal_reconciliation_detects_tampering_and_blocks_new_entries(self):
        self.buy()
        self.assertTrue(self.call('reconcile')['valid'])
        with self.s.store.transaction() as db:
            s=self.s._load(db);s['balances']['USDC']='9999';self.s.store.save(db,s)
        self.assertFalse(self.call('reconcile')['valid'])
        with self.assertRaisesRegex(ValueError,'RECONCILIATION_DRIFT'):self.propose('BTC-USDC')

    def test_migration_preserves_cash_loss_baselines_and_archive(self):
        from alladin.models import Config
        from alladin.engine import Service
        path=Path(self.tmp.name)/'legacy.sqlite'
        cfg=Config(initial_usdc=250,risk_per_trade=.02,max_open_risk=.02)
        legacy=Service(cfg,path)
        with legacy.store.transaction() as db:
            state=legacy._load(db)
            state['portfolio'].update(cash=247.43,initial=250,peak=250,day='2026-10-14',day_start_equity=250,fees_paid=2.57,total_closed=3)
            legacy.store.save(db,state);legacy.store.event(db,self.now,'fixture',{'source':'synthetic_test'})
        before=legacy.store.verify_audit()
        upgraded=SpotService.migrate(SpotPolicy(),path,cfg,clock=self.clock)
        s=upgraded._state()
        self.assertEqual(dec(s['balances']['USDC']),D('247.43'))
        self.assertEqual(dec(s['day_start_equity']),250)
        self.assertEqual(dec(s['peak']),250)
        self.assertEqual(s['legacy_closed_count'],3)
        self.assertEqual(s['legacy_snapshot'],state)
        self.assertTrue(upgraded.store.verify_audit()['valid'])
        self.assertTrue(upgraded.command('reconcile',{},'read')['valid'])
        self.assertGreater(upgraded.store.verify_audit()['count'],before['count'])
        with self.assertRaisesRegex(ValueError,'migrated'):legacy.status()

    def test_mcp_resources_prompts_and_real_http_roundtrip(self):
        from alladin.mcp_server import handle
        from alladin.server import build_server
        from alladin.client import BackendClient
        listed=handle(self.s,dict(jsonrpc='2.0',method='tools/list'))['tools']
        self.assertIn('commit_trade',{x['name'] for x in listed})
        self.assertNotIn('submit_decision',{x['name'] for x in listed})
        resource=handle(self.s,dict(jsonrpc='2.0',method='resources/read',params={'uri':'portfolio://current'}))
        self.assertEqual(json.loads(resource['contents'][0]['text'])['execution'],'paper')
        prompt=handle(self.s,dict(jsonrpc='2.0',method='prompts/get',params={'name':'pre_trade_checklist'}))
        self.assertIn('multi-token',prompt['messages'][0]['content']['text'])
        token='unit-test-token-'+('x'*40)
        server=build_server(self.s,port=0,token=token)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            client=BackendClient('http://127.0.0.1:'+str(server.server_port),token)
            result=client.command('scan_opportunities',{'limit':2,'product_ids':['DOGE-USDC','SHIB-USDC']},'http-scan')
            self.assertEqual(result['scanned'],2)
            self.assertEqual(client.status()['backend'],'portfolio')
            self.assertEqual(client._request('/v1/contract')['version'],'0.7')
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
