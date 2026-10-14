import unittest
import tempfile
import json
from urllib.parse import parse_qs, urlsplit

from alladin.instruments import CoinbaseInstruments, capabilities, size_order
from alladin.transport import DataError


def row(pid, kind='SPOT', **fields):
    return dict(product_id=pid, product_type=kind, base_increment='0.05',
                base_min_size='0.1', base_max_size='100', **fields)


class HTTP:
    def __init__(self, *pages):
        self.pages = list(pages)
        self.calls = []

    def json(self, url, headers=None):
        self.calls.append(url)
        result = self.pages.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class InstrumentsTest(unittest.TestCase):
    def test_all_types_paginated_without_sol_filter(self):
        http = HTTP(dict(products=[row('BTC-USD'), row('ETH-EUR')],
                         pagination=dict(has_next=True, next_cursor='abc')),
                    dict(products=[row('OIL-FUT', 'FUTURE'), row('canonical-id', 'EQUITY'),
                                   row('OPTIONS', 'OPTION_GROUP'), row('FUTURES', 'FUTURE_GROUP'),
                                   row('NEW', 'NEW_PRODUCT_TYPE')], pagination=dict(has_next=False)))
        source = CoinbaseInstruments(http)
        result = source.catalog()
        self.assertEqual(result['count'], 7)
        self.assertIn('NEW_PRODUCT_TYPE', result['product_types'])
        self.assertEqual(parse_qs(urlsplit(http.calls[0]).query)['get_all_products'], ['true'])
        self.assertEqual(parse_qs(urlsplit(http.calls[1]).query)['cursor'], ['abc'])
        self.assertFalse(result['account_eligibility_verified'])
        result['products'].clear()
        self.assertEqual(source.catalog()['count'], 7)
        self.assertEqual(len(http.calls), 2)

    def test_failed_refresh_does_not_replace_complete_cache(self):
        http = HTTP(dict(products=[row('BTC-USD')]), DataError('unavailable'))
        source = CoinbaseInstruments(http)
        first = source.catalog()
        with self.assertRaises(DataError):
            source.catalog(refresh=True)
        self.assertEqual(source.catalog(), first)

    def test_repeated_cursor_and_ignored_offset_rejected(self):
        page = dict(products=[row('BTC-USD')], pagination=dict(has_next=True, next_cursor='abc'))
        with self.assertRaises(DataError):
            CoinbaseInstruments(HTTP(page, page)).catalog()
        page = dict(products=[row(f'P{i}') for i in range(100)])
        with self.assertRaises(DataError):
            CoinbaseInstruments(HTTP(page, page)).catalog()

    def test_offset_paging_and_duplicate_identity(self):
        first = dict(products=[row(f'P{i}') for i in range(100)])
        http = HTTP(first, dict(products=[row('P99'), row('P100')]))
        result = CoinbaseInstruments(http).catalog()
        self.assertEqual(result['count'], 101)
        self.assertEqual(parse_qs(urlsplit(http.calls[1]).query)['offset'], ['100'])

    def test_unknown_and_non_sol_are_visible_but_not_falsely_executable(self):
        for kind in ('SPOT', 'FUTURE', 'EQUITY', 'OPTION_GROUP', 'NEW'):
            result = capabilities(row('BTC-USD', kind))
            self.assertFalse(result['paper_execution'])
            self.assertIn('execution_adapter_not_implemented', result['execution_blocks'])
        self.assertTrue(capabilities(row('SOL-USDC'))['paper_execution'])
        self.assertFalse(capabilities(row('SOL-USDC', trading_disabled=True))['paper_execution'])

    def test_lot_multiple_not_decimal_precision(self):
        self.assertEqual(size_order(row('ETH-BTC'), '1.079'), '1.05')
        for value in ('NaN', 'Infinity', '0.04', '-1', True):
            with self.assertRaises(ValueError):
                size_order(row('ETH-BTC'), value)

    def test_book_identity_cross_and_invalid_levels(self):
        for book in (dict(product_id='ETH-USD', bids=[], asks=[]),
                     dict(product_id='BTC-USD', bids=[dict(price='11', size='1')], asks=[dict(price='10', size='1')]),
                     dict(product_id='BTC-USD', bids=[dict(price='NaN', size='1')], asks=[dict(price='10', size='1')])):
            with self.assertRaises(DataError):
                CoinbaseInstruments(HTTP(dict(pricebook=book))).book('BTC-USD')
        book = dict(product_id='ETH-BTC', time='source-time', bids=[dict(price='0.04', size='1')],
                    asks=[dict(price='0.05', size='1')])
        result = CoinbaseInstruments(HTTP(dict(pricebook=book))).book('ETH-BTC')
        self.assertEqual(result['source_time'], 'source-time')
        self.assertFalse(result['execution_authorized'])

    def test_identifier_injection_and_strict_arguments(self):
        source = CoinbaseInstruments(HTTP())
        for pid in ('../BTC-USD', 'BTC-USD?x=1', '', 2):
            with self.assertRaises(ValueError):
                source.instrument(pid)
        for args in ({'refresh': 'true'}, {'unknown': True}):
            with self.assertRaises(ValueError):
                source.command('catalog', args)

    def test_malformed_catalog_never_claims_completeness(self):
        for response in ({}, dict(products=[{}]), dict(products=[], pagination={}),
                         dict(products=[], pagination=dict(has_next=True, next_cursor='next'))):
            with self.assertRaises(DataError):
                CoinbaseInstruments(HTTP(response)).catalog()

    def test_service_and_mcp_discovery_do_not_create_an_account_or_fill(self):
        from alladin.engine import Service
        from alladin.models import Config
        from alladin.mcp_server import handle
        with tempfile.TemporaryDirectory() as root:
            service = Service(Config(), root + '/session.sqlite')
            service.instruments = CoinbaseInstruments(HTTP(dict(products=[row('BTC-USD')]),
                                                          row('ETH-EUR')))
            result = service.command('catalog', {}, 'catalog-key')
            self.assertEqual(result['products'][0]['product_id'], 'BTC-USD')
            message = dict(jsonrpc='2.0', method='tools/call', params=dict(
                name='instrument', arguments=dict(product_id='ETH-EUR')))
            response = handle(service, message)
            self.assertFalse(response['isError'])
            self.assertEqual(json.loads(response['content'][0]['text'])['product_id'], 'ETH-EUR')
            with service.store.connect() as db:
                self.assertIsNone(service.store.load(db))
            self.assertEqual(service.store.audit(), [])


if __name__ == '__main__':
    unittest.main()
