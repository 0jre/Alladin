import io
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from alladin.transport import HTTP,DataError,deadline
from alladin.demo import run_demo
from alladin.engine import Service
from alladin.models import Config


class DeadlineTests(unittest.TestCase):
    def test_slow_dns_or_stream_cannot_overrun_and_late_response_is_discarded(self):
        release=threading.Event();finished=threading.Event()
        def open_request(*args,**kwargs):
            release.wait(2);finished.set();return io.BytesIO(b'{"late":true}')
        with patch('alladin.transport.urllib.request.build_opener') as opener:
            opener.return_value.open.side_effect=open_request
            begin=time.monotonic()
            try:
                with self.assertRaises(DataError):HTTP(timeout=.05,retries=2).json('https://example.test')
                self.assertLess(time.monotonic()-begin,.5)
            finally:
                release.set();self.assertTrue(finished.wait(1))

    def test_nested_calls_share_total_budget(self):
        def open_request(*args,**kwargs):
            time.sleep(.04);return io.BytesIO(b'{"ok":true}')
        with patch('alladin.transport.urllib.request.build_opener') as opener:
            opener.return_value.open.side_effect=open_request
            with deadline(.065):
                self.assertEqual(HTTP(timeout=1).json('https://example.test'),{'ok':True})
                with self.assertRaises(DataError):HTTP(timeout=1).json('https://example.test')
        time.sleep(.05)  # allow the intentionally late read-only fixture to release its slot

    def test_retry_after_must_fit_remaining_budget(self):
        import urllib.error
        def open_request(*args,**kwargs):
            raise urllib.error.HTTPError('https://example.test',429,'fixture',{'Retry-After':'10'},io.BytesIO())
        with patch('alladin.transport.urllib.request.build_opener') as opener:
            opener.return_value.open.side_effect=open_request
            with self.assertRaises(DataError):HTTP(timeout=.1,retries=2).json('https://example.test')
            self.assertEqual(opener.return_value.open.call_count,1)

    def test_demo_waiting_state_does_not_fail_on_missing_initial_snapshot(self):
        from types import SimpleNamespace
        class Store:
            def verify_audit(self):return {'valid':True}
            def connect(self):return self
            def __enter__(self):return self
            def __exit__(self,*args):pass
        class Fake:
            council=SimpleNamespace(mode='external');store=Store()
            def status(self):return {'equity_usdc':250}
            def performance(self):return {}
            def _load(self,db):return {}
            def command(self,name,args,key):
                return {'result':'waiting_for_closed_bar'} if name=='paper_tick' else {'result':'abstained'}
        with tempfile.TemporaryDirectory() as tmp:
            report=run_demo(Fake(),.02,.01,tmp)
            self.assertTrue(report['observations'])
            self.assertTrue(all('error' not in x for x in report['observations']))

    def test_collection_deadline_blocks_commit_and_late_response_cannot_mutate_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            service=Service(Config(),Path(tmp)/'session.sqlite')
            release=threading.Event()
            def open_request(*args,**kwargs):
                release.wait(1);return io.BytesIO(b'{}')
            def collect(args):
                HTTP(timeout=1).json('https://example.test')
                raise AssertionError('late transport must not reach command application')
            with patch('alladin.transport.urllib.request.build_opener') as opener,patch.object(service,'_collect_paper_data',side_effect=collect):
                opener.return_value.open.side_effect=open_request
                try:
                    with deadline(.04):
                        with self.assertRaises(DataError):service.command('paper_tick',{},'deadline')
                finally:release.set()
            self.assertEqual(service.status()['bars_processed'],0)
            self.assertEqual(service.store.verify_audit()['count'],0)

    def test_saturated_read_slots_are_bounded(self):
        with patch('alladin.transport._IO_SLOTS',threading.BoundedSemaphore(0)):
            with self.assertRaises(DataError):HTTP(timeout=.02).json('https://example.test')


class CandleCacheTests(unittest.TestCase):
    def test_closed_candles_reused_only_until_next_bar(self):
        from alladin.providers import CoinbaseMarket
        provider=CoinbaseMarket()
        def payload(ts):
            return {'candles':[{'start':str(ts),'open':'100','high':'101','low':'99','close':'100','volume':'100'}]}
        with patch.object(provider,'_get',side_effect=[payload(60),payload(120)]) as get:
            rows=provider.candles(count=1,aggregate=60,now=125)
            rows.clear()
            self.assertEqual(len(provider.candles(count=1,aggregate=60,now=179)),1)
            self.assertEqual(get.call_count,1)
            self.assertEqual(provider.candles(count=1,aggregate=60,now=180)[0].timestamp,120)
            self.assertEqual(get.call_count,2)

    def test_missing_latest_closed_bar_is_not_cached(self):
        from alladin.providers import CoinbaseMarket
        provider=CoinbaseMarket()
        payload={'candles':[{'start':'60','open':'100','high':'101','low':'99','close':'100','volume':'100'}]}
        with patch.object(provider,'_get',return_value=payload) as get:
            provider.candles(count=1,aggregate=60,now=180)
            provider.candles(count=1,aggregate=60,now=180)
            self.assertEqual(get.call_count,2)
