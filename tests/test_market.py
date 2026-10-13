import json
import os
import unittest
from urllib.parse import parse_qs, urlsplit

from alladin.connect import bearer, complete, connect_request, connection_status, reset_session
from alladin.market import MarketVision, build_views
from alladin.platforms import desks, platforms


class FakeHTTP:
    def __init__(self):
        self.urls = []
        self.form_url = None
    def json(self, url, payload=None, headers=None, retry=True):
        self.urls.append(url)
        if 'api.binance.com' in url:
            return [{'symbol': 'BTCUSDT', 'lastPrice': '100', 'priceChangePercent': '6', 'quoteVolume': '5000000'}]
        if 'okx.com' in url:
            return {'data': [{'instId': 'BTC-USDT', 'last': '101', 'open24h': '95', 'volCcy24h': '4000000'},
                             {'instId': 'ETH-USDT', 'last': '10', 'open24h': '10', 'volCcy24h': '1'}]}
        if 'coingecko' in url:
            return [{'symbol': 'btc', 'current_price': 102, 'price_change_percentage_24h': 4,
                     'total_volume': 9000000, 'market_cap': 2_000_000_000_000}]
        if 'coinmarketcap' in url:
            return {'data': [{'symbol': 'BTC', 'quote': {'USD': {
                'price': 103, 'percent_change_24h': 1, 'volume_24h': 100, 'market_cap': 50}}}]}
        if 'dexscreener' in url:
            return {'pairs': [{'chainId': 'solana', 'priceUsd': '1.2', 'baseToken': {'symbol': 'BONK'},
                               'volume': {'h24': 20000}, 'priceChange': {'h24': 9}, 'liquidity': {'usd': 80000}}]}
        if 'gmgn.ai' in url:
            return {'data': {'rank': [{'symbol': 'WIF', 'price': '2.5', 'volume': 30000, 'price_change_percent': 11}]}}
        raise AssertionError(url)
    def form(self, url, fields, headers=None, retry=False):
        self.form_url = url
        self.fields = fields
        return {'access_token': 'session-token-value', 'refresh_token': 'hidden'}


class MarketTests(unittest.TestCase):
    def test_views_rank_classify_and_keep_alpha_observational(self):
        view = build_views([
            {'source': 'binance', 'symbol': 'BTCUSDT', 'base': 'BTC', 'price': 100,
             'change_24h_pct': 6, 'volume_24h': 50, 'market_cap': 2_000_000_000_000, 'liquidity': None, 'chain': None},
            {'source': 'okx', 'symbol': 'BTC-USDT', 'base': 'BTC', 'price': 110,
             'change_24h_pct': 4, 'volume_24h': 40, 'market_cap': None, 'liquidity': None, 'chain': None},
        ], limit=10)
        self.assertEqual(view['ranking'][0]['tier'], 'mega')
        self.assertEqual(view['signals'][0]['signal'], 'firme')
        self.assertEqual(view['tracker'][0]['base'], 'BTC')
        self.assertGreater(view['tracker'][0]['dispersion'], 0)
        self.assertEqual(view['alpha'][0]['execution'], 'coinbase')
        self.assertFalse(view['alpha'][0]['executed'])
        self.assertEqual(view['copy_trading']['mode'], 'observacao')

    def test_radar_reads_every_public_source_and_skips_a_failure(self):
        http = FakeHTTP()
        os.environ['CMC_API_KEY'] = 'cmc-test'
        try:
            view = MarketVision(http).radar(limit=5, query='BONK')
        finally:
            os.environ.pop('CMC_API_KEY', None)
        self.assertEqual(view['errors'], {})
        self.assertIn('gmgn', {row['source'] for row in view['ranking']})
        self.assertTrue(any('dexscreener.com' in url for url in http.urls))
        self.assertNotIn('cmc-test', json.dumps(view))
        broken = FakeHTTP()
        broken.json = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('x'))
        # MarketVision catches DataError and ValueError, not RuntimeError. Use DataError path.
        from alladin.transport import DataError
        broken.json = lambda *args, **kwargs: (_ for _ in ()).throw(DataError('fonte fora'))
        partial = MarketVision(broken).radar(sources=['binance'], symbols=['BTCUSDT'], limit=1)
        self.assertEqual(partial['ranking'], [])
        self.assertIn('binance', partial['errors'])

    def test_secret_in_query_is_rejected(self):
        with self.assertRaises(ValueError):
            MarketVision(FakeHTTP()).radar(sources=['dexscreener'], query='has-private_key', limit=1)

    def test_connect_link_is_an_action_request_without_the_secret(self):
        reset_session()
        os.environ['COINBASE_OAUTH_CLIENT_ID'] = 'abc12345'
        os.environ['COINBASE_OAUTH_REDIRECT_URI'] = 'http://127.0.0.1:8080/oauth/coinbase/callback'
        os.environ.pop('COINBASE_OAUTH_ALLOW_TRADE', None)
        try:
            with self.assertRaises(ValueError):
                connect_request(trade=True)
            action = connect_request()
            parsed = urlsplit(action['url'])
            query = parse_qs(parsed.query)
            self.assertEqual(action['type'], 'action_request')
            self.assertEqual(action['label'], 'Connect account')
            self.assertEqual(parsed.netloc, 'login.coinbase.com')
            self.assertEqual(query['client_id'], ['abc12345'])
            self.assertNotIn('client_secret', query)
            self.assertNotIn('code_verifier', query)
            self.assertEqual(query['code_challenge_method'], ['S256'])
            self.assertIn('chatgpt', action['platforms'])
            self.assertIn('claude_work', action['platforms'])
            blob = json.dumps(action)
            self.assertNotIn('client_secret', blob)
        finally:
            reset_session()
            os.environ.pop('COINBASE_OAUTH_CLIENT_ID', None)
            os.environ.pop('COINBASE_OAUTH_REDIRECT_URI', None)

    def test_token_exchange_stays_out_of_the_status(self):
        reset_session()
        os.environ['COINBASE_OAUTH_CLIENT_ID'] = 'abc12345'
        os.environ['COINBASE_OAUTH_CLIENT_SECRET'] = 'super-secret-value'
        os.environ['COINBASE_OAUTH_REDIRECT_URI'] = 'http://127.0.0.1:8080/oauth/coinbase/callback'
        http = FakeHTTP()
        try:
            action = connect_request()
            result = complete('auth-code', action['state'], http)
            status = connection_status()
            self.assertTrue(result['connected'])
            self.assertNotIn('token', status)
            self.assertNotIn('super-secret-value', json.dumps(status))
            self.assertNotIn('session-token-value', json.dumps(result))
            self.assertEqual(http.form_url, 'https://login.coinbase.com/oauth2/token')
            self.assertEqual(bearer(), 'session-token-value')
            with self.assertRaises(ValueError):
                complete('auth-code', action['state'], http)
        finally:
            reset_session()
            os.environ.pop('COINBASE_OAUTH_CLIENT_ID', None)
            os.environ.pop('COINBASE_OAUTH_CLIENT_SECRET', None)
            os.environ.pop('COINBASE_OAUTH_REDIRECT_URI', None)

    def test_platforms_cover_work_and_sandbox_chats(self):
        catalog = platforms()
        self.assertEqual(set(catalog['platforms']),
                         {'cursor', 'chatgpt', 'chatgpt_work', 'claude', 'claude_work', 'sandbox', 'mcp'})
        self.assertIn('action_request', platforms('sandbox')['rules'][2])
        self.assertEqual(desks('copy')['id'], 'copy')
        self.assertIn('coinbase_order', desks('copy')['task'])


if __name__ == '__main__':
    unittest.main()
