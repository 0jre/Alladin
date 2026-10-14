"""Regressões de robustez: equity multi-mint, gates de rede, conselho por mint,
estado legado, replay multi-mint e mint vigiado sem conselho."""
import io
import json
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from alladin.agents import Council
from alladin.engine import Service
from alladin.models import SOL, USDC, Candle, Config, Position, Portfolio, Proposal, Snapshot
from alladin.research import demo_feed
from alladin.risk import security_checks

BASE = 1_700_000_000


def bar(i, mint=SOL, price=100.0):
    ts = BASE + i * 900
    span = max(price * 0.005, 1e-6)
    return Candle(ts, price, price + span, price - span, price, 100000, mint=mint)


def snap(i, mint=SOL, price=100.0, **kw):
    ts = BASE + (i + 1) * 900
    base = dict(price=price, liquidity_usd=10_000_000, volume_24h_usd=50_000_000,
                account_checked=True, cluster_verified=True, oracle_price=price,
                oracle_timestamp=ts, expected_funding_hourly=.00001,
                perp_market_verified=True, source='TEST_HARDENING', top10_account_share=.2,
                sell_simulated=True, route_buy=True, route_sell=True, extensions_decoded=True)
    base.update(kw)
    return Snapshot(ts, mint=mint, **base)


class Fixed:
    mode = 'rules'
    client = type('Client', (), {'calls': 0})()

    def decide(self, f, s, book, cfg, now):
        return Proposal('LONG', 'spot', .8, .02, .06, 24, 'Test', 'trend_following', mint=s.mint), {'mode': 'test'}


def trend_features():
    return dict(ready=True, price=100, regime='trend', cvar95_bar=.01, atr=1,
                atr_fraction=.01, ema_gap=.01, higher_trend=.01, momentum_12=.03,
                rsi=60, efficiency=.5, volume_ratio=1, breakout_high=110, breakout_low=90)


class StatusMarksTests(unittest.TestCase):
    def test_status_values_each_mint_at_its_own_mark(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        service = Service(Config(fee_bps=0, slippage_bps=0, fixed_cost_usdc=0),
                          Path(temp.name) / 'm.sqlite', council=Fixed())
        service.command('admit', {'snapshot': asdict(snap(0, USDC, 1))}, 'admit')
        service.command('watch', {'mint': USDC, 'arm': True}, 'watch')
        for i in range(82):
            service.command('ingest', {'candle': asdict(bar(i)), 'snapshot': asdict(snap(i))}, f's{i}')
            service.command('ingest', {'candle': asdict(bar(i, USDC, 1)), 'snapshot': asdict(snap(i, USDC, 1))}, f'u{i}')
        status = service.status()
        positions = {p['mint']: p for p in status['positions']}
        expected = status['cash_usdc'] + positions[SOL]['qty'] * 100 + positions[USDC]['qty'] * 1
        self.assertAlmostEqual(status['equity_usdc'], expected, places=6)
        self.assertEqual(status['series'][USDC]['bars_processed'], 82)
        self.assertEqual(status['series'][USDC]['last_price'], 1)
        self.assertIn('pending_book', status)


class SolanaOnlyTests(unittest.TestCase):
    def test_non_solana_config_and_snapshots_are_rejected(self):
        with self.assertRaises(ValueError):
            Config(chain='base')
        with self.assertRaises(ValueError):
            Snapshot(1000, chain='base', mint=USDC, price=1)

    def test_sol_only_snapshot_passes_generic_gates(self):
        cfg = Config()
        now = 100000
        healthy = Snapshot(now, price=1, liquidity_usd=10_000_000,
                           volume_24h_usd=50_000_000, account_checked=True,
                           cluster_verified=True)
        self.assertEqual(security_checks(healthy, cfg, now), [])


class CouncilMintTests(unittest.TestCase):
    def test_position_in_other_mint_does_not_flip_candidate(self):
        book = Portfolio(10000, 10000, 10000)
        book.positions = [Position('s', 'spot', 1, 10, 100, 98, 106, 0, 0, 99999, 'x', 0, mint=SOL)]
        s = snap(0, USDC, 1)
        p, audit = Council('rules').decide(trend_features(), s, book, Config(), BASE + 900)
        self.assertEqual(p.action, 'LONG')

    def test_opposite_position_same_mint_emits_close(self):
        book = Portfolio(10000, 10000, 10000)
        book.positions = [Position('u', 'perp', 1, 10, 1, .98, 1.06, 10, 0, 99999, 'x', 0, mint=USDC)]
        features = dict(trend_features(), ema_gap=-.01, higher_trend=-.01, momentum_12=-.03)
        p, audit = Council('rules').decide(features, snap(0, USDC, 1), book, Config(), BASE + 900)
        self.assertEqual(p.action, 'HOLD')


class LegacyStateTests(unittest.TestCase):
    def test_state_missing_newer_keys_still_loads(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        cfg = Config()
        service = Service(cfg, Path(temp.name) / 'old.sqlite',agent_mode='rules')
        book = Portfolio(10000, 10000, 10000)
        legacy = dict(config_hash=service.fingerprint, agent_mode='rules',
                      portfolio=book.serialize())
        with service.store.transaction() as db:
            service.store.save(db, legacy)
        status = service.status()
        self.assertEqual(status['equity_usdc'], 10000)
        self.assertEqual(status['bars_processed'], 0)
        b, s = next(demo_feed())
        result = service.command('ingest', {'candle': asdict(b), 'snapshot': asdict(s)}, 'one')
        self.assertEqual(result['result'], 'processed')


class ReplayMultiMintTests(unittest.TestCase):
    def feed(self, folder, n=5):
        path = Path(folder) / 'multi.jsonl'
        now = int(time.time()) - (n + 2) * 900
        lines = []
        for i in range(n):
            for mint, price in ((SOL, 100.0), (USDC, 1.0)):
                ts = now + i * 900
                candle = dict(timestamp=ts, open=price, high=price, low=price, close=price,
                              volume=100000.0, funding_rate=0.0, chain='solana', mint=mint)
                s = asdict(snap(0, mint, price))
                s.update(timestamp=ts + 900)
                lines.append(json.dumps({'candle': candle, 'snapshot': s}))
        path.write_text('\n'.join(lines) + '\n')
        return path

    def test_replay_arms_and_ingests_every_mint(self):
        from alladin.__main__ import main
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        feed = self.feed(temp.name)
        db = Path(temp.name) / 'replay.sqlite'
        out = Path(temp.name) / 'out'
        cfg_path = os.path.join(os.path.dirname(__file__), '..', 'config.json')
        argv = ['alladin', '--config', cfg_path, '--db', str(db),
                'replay', '--feed', str(feed), '--output', str(out)]
        captured = io.StringIO()
        with patch.object(sys, 'argv', argv), redirect_stdout(captured):
            self.assertEqual(main(), 0)
        summary = json.loads(captured.getvalue())
        self.assertEqual(summary['feed_records'], 10)
        service = Service(Config.load(cfg_path), db)
        status = service.status()
        self.assertEqual(status['bars_processed'], 5)
        self.assertEqual(status['series'][USDC]['bars_processed'], 5)


class WatchedOnlyTests(unittest.TestCase):
    def test_watched_mint_does_not_burn_council_calls(self):
        class Counting:
            mode = 'rules'
            client = type('Client', (), {'calls': 0})()

            def __init__(self):
                self.calls = 0

            def decide(self, f, s, book, cfg, now):
                self.calls += 1
                return Proposal(mint=s.mint), {'mode': 'count'}

        council = Counting()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        service = Service(Config(), Path(temp.name) / 'w.sqlite', council=council)
        service.command('admit', {'snapshot': asdict(snap(0, USDC, 1))}, 'admit')
        service.command('watch', {'mint': USDC}, 'watch')
        for i in range(81):
            service.command('ingest', {'candle': asdict(bar(i, USDC, 1)), 'snapshot': asdict(snap(i, USDC, 1))}, f'u{i}')
        self.assertEqual(council.calls, 0)
        last = service.store.audit(1)[0]['payload']
        self.assertEqual(last['decision']['council']['gate'], 'watched_only')


class EvaluateWarmupTests(unittest.TestCase):
    def test_evaluate_without_ready_features_uses_snapshot_price(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        service = Service(Config(), Path(temp.name) / 'e.sqlite')
        service.command('ingest', {'candle': asdict(bar(0)), 'snapshot': asdict(snap(0))}, 'one')
        result = service.command('evaluate', {'proposal': asdict(
            Proposal('LONG', 'spot', .8, .02, .06, 24, 'cedo', 'sim'))}, 'ev')
        self.assertFalse(result['approval']['approved'])
        self.assertIn('warmup_or_shock', result['approval']['reasons'])


if __name__ == '__main__':
    unittest.main()
