"""Coinbase instrument discovery independent of blockchain addresses.

Catalog visibility is not account eligibility or execution support. Unknown
product types remain visible; they must never fall through to spot accounting.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_DOWN
import hashlib
import re
import threading
import time
from urllib.parse import quote, urlencode

from .storage import canonical
from .transport import HTTP, HTTP_TOTAL_SECONDS, DataError, deadline


def product_id(value):
    # Coinbase also uses canonical UUIDs for some instruments. Do not split an
    # identifier into presumed base/quote currencies or require a Solana mint.
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}', value):
        raise ValueError('Invalid Coinbase product_id')
    return value


def positive(value, field):
    if isinstance(value, bool):
        raise ValueError(field + ' must be positive and finite')
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(field + ' must be positive and finite') from None
    if not number.is_finite() or number <= 0:
        raise ValueError(field + ' must be positive and finite')
    return number


def size_order(instrument, base_size):
    """Round down to an actual lot multiple, not to decimal places.

This is size validation, not execution approval. Contract units, session rules,
cash, margin and account eligibility require the matching execution adapter.
"""
    size = positive(base_size, 'base_size')
    step = positive(instrument.get('base_increment'), 'base_increment')
    minimum = positive(instrument.get('base_min_size'), 'base_min_size')
    maximum = positive(instrument.get('base_max_size'), 'base_max_size')
    size = (size / step).to_integral_value(rounding=ROUND_DOWN) * step
    if not minimum <= size <= maximum:
        raise ValueError('Rounded size is outside Coinbase product limits')
    return format(size, 'f')


def capabilities(instrument):
    """Report implemented capabilities; never equate listed with tradable."""
    kind = instrument.get('product_type', 'UNKNOWN_PRODUCT_TYPE')
    pid = instrument['product_id']
    reasons = []
    for flag in ('is_disabled', 'trading_disabled', 'cancel_only', 'view_only', 'auction_mode'):
        if instrument.get(flag) is True:
            reasons.append(flag)
    if instrument.get('limit_only') is True or instrument.get('post_only') is True:
        reasons.append('market_orders_disabled')
    # Existing accounts retain their original, explicitly scoped executor.
    # Discovery is deliberately broader than that executor. A future adapter
    # must remove this reason only after its accounting and risk path exist.
    legacy = kind == 'SPOT' and pid == 'SOL-USDC'
    if not legacy:
        reasons.append('execution_adapter_not_implemented')
    return dict(catalog=True, market_data='endpoint_dependent',
                paper_execution=legacy and not reasons, live_execution=False,
                account_eligibility='unknown_public_catalog_is_not_entitlement',
                execution_blocks=reasons)


class CoinbaseInstruments:
    BASE = 'https://api.coinbase.com/api/v3/brokerage/market'

    def __init__(self, http=None, ttl=60, clock=time.time):
        self.http = http or HTTP(timeout=HTTP_TOTAL_SECONDS, retries=2)
        self.clock = clock
        self.ttl = positive(ttl, 'catalog_ttl_seconds')
        self._cache = None
        self._lock = threading.Lock()

    def _get(self, path, params=None):
        url = self.BASE + '/' + path
        if params:
            url += '?' + urlencode(params)
        try:
            data = self.http.json(url, headers={'Cache-Control': 'no-cache'})
        except DataError as exc:
            raise exc.at_source('coinbase_instruments') from None
        if not isinstance(data, dict):
            raise DataError('Invalid Coinbase instrument response')
        return data

    @staticmethod
    def _instrument(row):
        if not isinstance(row, dict):
            raise DataError('Invalid Coinbase instrument record')
        try:
            product_id(row.get('product_id'))
            canonical(row)  # refuse nonfinite values before hashing/persistence
        except (ValueError, TypeError):
            raise DataError('Invalid Coinbase instrument record') from None
        result = deepcopy(row)
        result['alladin_capabilities'] = capabilities(row)
        return result

    def catalog(self, refresh=False):
        if type(refresh) is not bool:
            raise ValueError('refresh must be boolean')
        with self._lock:
            now = self.clock()
            if not refresh and self._cache and 0 <= now - self._cache['observed_at'] < self.ttl:
                return deepcopy(self._cache)
            # Explicit get_all_products: omission silently returns SPOT only.
            # Never replace a complete cache with partial pages after a failure.
            with deadline(45):
                products, seen_cursors = {}, set()
                params = {'get_all_products': 'true', 'limit': 100}
                for page_number in range(200):
                    data = self._get('products', params)
                    rows = data.get('products')
                    if not isinstance(rows, list):
                        raise DataError('Coinbase catalog products must be a list')
                    added = 0
                    for row in rows:
                        instrument = self._instrument(row)
                        pid = instrument['product_id']
                        if pid not in products:
                            added += 1
                        products[pid] = instrument
                    pagination = data.get('pagination')
                    if pagination is not None:
                        if not isinstance(pagination, dict) or type(pagination.get('has_next')) is not bool:
                            raise DataError('Invalid Coinbase catalog pagination')
                        if not pagination['has_next']:
                            break
                        cursor = pagination.get('next_cursor')
                        if not isinstance(cursor, str) or not cursor or cursor in seen_cursors or not added:
                            raise DataError('Coinbase catalog pagination did not advance')
                        seen_cursors.add(cursor)
                        params.pop('offset', None)
                        params['cursor'] = cursor
                    elif len(rows) < params['limit']:
                        break
                    else:
                        # Compatibility with the documented offset API. An
                        # ignored offset must fail, not claim completeness.
                        if not added:
                            raise DataError('Coinbase ignored catalog pagination')
                        params['offset'] = (page_number + 1) * params['limit']
                else:
                    raise DataError('Coinbase catalog page bound exceeded; incomplete catalog rejected')
            ordered = [products[pid] for pid in sorted(products)]
            types = {}
            for row in ordered:
                kind = row.get('product_type', 'UNKNOWN_PRODUCT_TYPE')
                if not isinstance(kind, str):
                    raise DataError('Invalid Coinbase product type')
                types[kind] = types.get(kind, 0) + 1
            result = dict(source='coinbase_public_catalog', observed_at=self.clock(),
                          scope='all_returned_product_types_including_expired',
                          account_eligibility_verified=False, count=len(ordered),
                          product_types=types, products=ordered,
                          catalog_sha256=hashlib.sha256(canonical(ordered).encode()).hexdigest())
            self._cache = result
            return deepcopy(result)

    def instrument(self, pid):
        pid = product_id(pid)
        with deadline(HTTP_TOTAL_SECONDS):
            return self._instrument(self._get('products/' + quote(pid, safe='')))

    def book(self, pid):
        pid = product_id(pid)
        with deadline(HTTP_TOTAL_SECONDS):
            data = self._get('product_book', {'product_id': pid, 'limit': 50})
        book = data.get('pricebook')
        if not isinstance(book, dict) or book.get('product_id') != pid:
            raise DataError('Coinbase book product does not match requested product')
        levels = {}
        for side in ('bids', 'asks'):
            rows = book.get(side)
            if not isinstance(rows, list) or not rows:
                raise DataError('Coinbase book is empty')
            try:
                levels[side] = [(positive(x['price'], 'price'), positive(x['size'], 'size')) for x in rows]
            except (KeyError, TypeError, ValueError):
                raise DataError('Coinbase book has invalid levels') from None
        bid = max(price for price, size in levels['bids'])
        ask = min(price for price, size in levels['asks'])
        if bid >= ask:
            raise DataError('Coinbase book is crossed or locked')
        # Preserve source time. This response is research data, not a fresh-mark
        # execution authorization; the adapter must validate age at commit.
        return dict(source='coinbase_public_book', product_id=pid,
                    received_at=self.clock(), source_time=book.get('time'),
                    bid=str(bid), ask=str(ask), pricebook=deepcopy(book),
                    execution_authorized=False)

    def command(self, name, args):
        if not isinstance(args, dict):
            raise ValueError('args must be an object')
        if name == 'catalog' and set(args) <= {'refresh'}:
            return self.catalog(args.get('refresh', False))
        if name in {'instrument', 'instrument_book'} and set(args) == {'product_id'}:
            return self.instrument(args['product_id']) if name == 'instrument' else self.book(args['product_id'])
        raise ValueError('Invalid instrument command arguments')
