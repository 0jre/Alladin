import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path

from alladin.agents import DECISION_SCHEMA
from alladin.engine import Service
from alladin.models import SOL, USDC, TOKEN_2022, Candle, Config, Proposal, Snapshot
from alladin.universe import classify_snapshot, decode_mint_account
from alladin.validation import assert_causal_feed

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
                perp_market_verified=True, source='TEST_FIXTURE', top10_account_share=.2,
                sell_simulated=True, route_buy=True, route_sell=True, extensions_decoded=True)
    base.update(kw)
    return Snapshot(ts, mint=mint, **base)

class Fixed:
    mode = 'rules'
    client = type('Client', (), {'calls': 0})()
    def decide(self, f, s, book, cfg, now):
        return Proposal('LONG', 'spot', .8, .02, .06, 24, 'Test', 'trend_following', mint=s.mint), {'mode': 'test'}

class PlanTests(unittest.TestCase):
    def test_token2022_dangerous_extension_is_not_eligible(self):
        data = bytearray(82)
        data[44], data[45] = 6, 1
        data.extend(bytes(83))
        data.append(1)
        data.extend((9, 0, 0, 0))  # NonTransferable, length 0
        decoded = decode_mint_account(bytes(data))
        self.assertIn('non_transferable', decoded['extensions'])
        s = snap(0, USDC, token_program=TOKEN_2022, extensions=decoded['extensions'], extensions_decoded=True)
        inst = classify_snapshot(s, Config())
        self.assertEqual(inst['status'], 'classified')
        self.assertIn('dangerous_token2022_extension', inst['reasons'])
        with self.assertRaises(ValueError):
            decode_mint_account(bytes(data) + bytes((99, 0, 0, 0)))

    def test_funnel_isolates_mints_and_blocks_lookahead(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        service = Service(Config(), Path(temp.name) / 'u.sqlite', council=Fixed())
        b, s = bar(0), snap(0)
        service.command('ingest', {'candle': asdict(b), 'snapshot': asdict(s)}, 'sol0')
        admitted = service.command('admit', {'snapshot': asdict(snap(0, USDC, price=1))}, 'admit')
        self.assertEqual(admitted['status'], 'eligible')
        with self.assertRaises(ValueError):
            service.command('ingest', {'candle': asdict(bar(0, USDC, 1)), 'snapshot': asdict(snap(0, USDC, 1))}, 'early')
        service.command('watch', {'mint': USDC, 'arm': True}, 'watch')
        other = service.command('ingest', {'candle': asdict(bar(0, USDC, 1)), 'snapshot': asdict(snap(0, USDC, 1))}, 'usdc0')
        self.assertEqual(other['result'], 'processed')
        nxt = service.command('ingest', {'candle': asdict(bar(1)), 'snapshot': asdict(snap(1))}, 'sol1')
        self.assertEqual(nxt['result'], 'processed')
        with self.assertRaises(ValueError):
            service.command('ingest', {'candle': asdict(bar(2)), 'snapshot': asdict(replace(snap(2), available_at=BASE + 3 * 900 + 1))}, 'future')
        self.assertEqual(service.status()['bars_processed'], 2)

    def test_two_spot_positions_keep_separate_stops(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        service = Service(Config(fee_bps=0, slippage_bps=0, fixed_cost_usdc=0), Path(temp.name) / 'm.sqlite', council=Fixed())
        service.command('admit', {'snapshot': asdict(snap(0, USDC, 1))}, 'admit')
        service.command('watch', {'mint': USDC, 'arm': True}, 'watch')
        for i in range(81):
            service.command('ingest', {'candle': asdict(bar(i)), 'snapshot': asdict(snap(i))}, f's{i}')
            service.command('ingest', {'candle': asdict(bar(i, USDC, 1)), 'snapshot': asdict(snap(i, USDC, 1))}, f'u{i}')
        positions = service.status()['positions']
        self.assertEqual({p['mint'] for p in positions}, {SOL, USDC})
        sol = next(p for p in positions if p['mint'] == SOL)
        usdc = next(p for p in positions if p['mint'] == USDC)
        service.command('ingest', {'candle': asdict(bar(81, price=1)), 'snapshot': asdict(snap(81, price=1))}, 'gap')
        # A SOL bar priced at 1 is a gap stop for SOL only.
        left = service.status()['positions']
        self.assertTrue(all(p['mint'] == USDC for p in left))
        self.assertNotEqual(sol['stop'], usdc['stop'])

    def test_shadow_execution_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            Config(execution='shadow')

    def test_external_execution_is_not_an_alladin_mode(self):
        with self.assertRaises(ValueError):
            Config(execution='live')

    def test_manager_schema_has_no_notional(self):
        self.assertNotIn('notional', DECISION_SCHEMA['properties'])

    def test_causal_feed_rejects_future_snapshot(self):
        rows = [(bar(0), snap(0)), (bar(1), snap(1))]
        self.assertEqual(assert_causal_feed(rows, 900), [SOL])
        with self.assertRaises(ValueError):
            assert_causal_feed([(bar(0), replace(snap(0), available_at=BASE + 900 + 5))], 900)

if __name__ == '__main__':
    unittest.main()
