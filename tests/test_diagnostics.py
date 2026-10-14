import io
import json
import socket
import tempfile
import threading
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from alladin.transport import HTTP,DataError
from alladin.diagnostics import diagnose
from alladin.models import Config
from alladin.risk import profile_feasibility
from alladin.mcp_server import handle
from alladin.engine import Service


class DiagnosticsTests(unittest.TestCase):
    def test_actual_proxy_timeout_reports_tunnel_phase_without_credentials(self):
        release=threading.Event()
        class Proxy(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_CONNECT(self):release.wait(1)
        proxy=ThreadingHTTPServer(('127.0.0.1',0),Proxy)
        worker=threading.Thread(target=proxy.serve_forever,daemon=True);worker.start()
        try:
            with patch('urllib.request.getproxies',return_value={'https':'http://127.0.0.1:'+str(proxy.server_port)}),patch('urllib.request.proxy_bypass',return_value=False):
                with self.assertRaises(DataError) as error:HTTP(timeout=.05,retries=0).json('https://example.invalid/private?key=do-not-log')
            self.assertEqual(error.exception.stage,'proxy_tunnel')
            self.assertNotIn('do-not-log',json.dumps(error.exception.details()))
            self.assertNotIn('private',str(error.exception))
        finally:release.set();proxy.shutdown();proxy.server_close();worker.join()

    def test_dns_failure_is_typed_and_does_not_expose_proxy_secrets(self):
        error=urllib.request.URLError(socket.gaierror(-3,'secret proxy hostname'))
        with patch('alladin.transport.urllib.request.build_opener') as opener:
            opener.return_value.open.side_effect=error
            with self.assertRaises(DataError) as caught:HTTP(timeout=.1,retries=0).json('https://example.invalid')
        self.assertEqual(caught.exception.code,'dns_failure')
        self.assertNotIn('secret',str(caught.exception))

    def test_doctor_identifies_source_and_does_not_mutate_ledger(self):
        cfg=Config(initial_usdc=250)
        with tempfile.TemporaryDirectory() as tmp:
            service=Service(cfg,Path(tmp)/'session.sqlite')
            before=service.status()
            with patch('alladin.transport.HTTP.json',side_effect=DataError('timeout',code='deadline_exceeded',stage='proxy_tunnel')):
                result=service.diagnostics()
                mcp=handle(service,{'jsonrpc':'2.0','method':'tools/call','params':{'name':'alladin_diagnostics','arguments':{}}})
            self.assertFalse(result['ready'])
            self.assertEqual(result['checks']['coinbase_market']['error']['source'],'coinbase_candles')
            self.assertEqual(result['checks']['solana_mainnet']['error']['source'],'solana_getGenesisHash')
            self.assertFalse(mcp['isError'])
            self.assertEqual(service.status(),before)
            self.assertEqual(service.store.verify_audit()['count'],0)

    def test_default_balance_profile_incompatibility_is_reported_not_bypassed(self):
        cfg=Config.load(Path(__file__).resolve().parents[1]/'config.json')
        result=profile_feasibility(cfg)
        self.assertFalse(result['baseline_can_fit'])
        self.assertLess(result['strategies']['trend_following']['best_net_reward_risk'],cfg.min_reward_risk)
        self.assertEqual(cfg.risk_per_trade,.02)
        self.assertEqual(cfg.sizing_mode,'available_balance')

    def test_feasibility_is_only_a_necessary_condition(self):
        self.assertFalse(profile_feasibility(Config())['checked'])
        from dataclasses import replace
        cfg=Config.load(Path(__file__).resolve().parents[1]/'config.json')
        # A fixture with no modeled costs tests the formula, not a runtime profile change.
        result=profile_feasibility(replace(cfg,fee_bps=0,slippage_bps=0,fixed_cost_usdc=0))
        self.assertTrue(result['baseline_can_fit'])
