import unittest
from alladin.coinbase import Coinbase
from alladin.models import Config, USDC_BY_CHAIN

USDC_BASE = USDC_BY_CHAIN['base']
WETH_BASE = '0x4200000000000000000000000000000000000006'
TAKER = '0x1111111111111111111111111111111111111111'

class FakeHTTP:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []
    def json(self, url, payload=None, headers=None, retry=True):
        self.calls.append(dict(url=url, payload=payload, headers=headers, retry=retry))
        return self.payload

def auth(method, host, path):
    return {'Authorization': 'Bearer test-jwt'}

class CoinbaseTests(unittest.TestCase):
    def test_base_config_uses_base_usdc(self):
        cfg = Config(chain='base')
        self.assertEqual(cfg.mint, USDC_BASE)
        self.assertEqual(Config(chain='ethereum').chain, 'ethereum')
        self.assertEqual(Config(chain='arbitrum').chain, 'arbitrum')

    def test_public_products_and_candles_need_no_key(self):
        http = FakeHTTP({'products': [{'product_id': 'ETH-USD', 'product_type': 'SPOT', 'base_currency': 'ETH', 'quote_currency': 'USD'}]})
        listed = Coinbase(http).products()
        self.assertEqual(listed['products'][0]['product_id'], 'ETH-USD')
        self.assertIn('/api/v3/brokerage/market/products', http.calls[0]['url'])
        http.payload = {'candles': [{'start': '100', 'open': '1', 'high': '2', 'low': '1', 'close': '2', 'volume': '3'}]}
        bars = Coinbase(http).candles('ETH-USD', 100, 1000, 900)
        self.assertEqual(bars['candles'][0]['close'], 2)

    def test_swap_quote_is_not_execution_and_rejects_secret(self):
        http = FakeHTTP({'toAmount': '1000', 'liquidityAvailable': True})
        quoted = Coinbase(http, auth).swap_quote('base', WETH_BASE, USDC_BASE, 10**15, TAKER)
        self.assertFalse(quoted['executed'])
        self.assertIn('network=base', http.calls[0]['url'])
        self.assertEqual(http.calls[0]['headers']['Authorization'], 'Bearer test-jwt')
        with self.assertRaises(ValueError):
            Coinbase(http, auth).swap_quote('solana', WETH_BASE, USDC_BASE, 1, TAKER)
        with self.assertRaises(ValueError):
            Coinbase(http, auth).create_order('ETH-USD', 'BUY', '10', 'order-0001', armed=False)

    def test_unknown_submit_is_not_retried_by_the_client(self):
        http = FakeHTTP({'success': True})
        result = Coinbase(http, auth).create_order('ETH-USD', 'BUY', '10', 'order-0001', armed=True)
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(len(http.calls), 1)
        with self.assertRaises(ValueError):
            Coinbase(http, auth).preview_order('ETH-USD', 'BUY', '10', 'has-private_key')

if __name__ == '__main__':
    unittest.main()
