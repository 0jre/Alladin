"""Visão de mercado somente leitura. Nenhuma destas fontes envia ordem.

A execução continua na Coinbase. Binance, OKX, CoinGecko, CoinMarketCap,
DexScreener e GMGN alimentam ranking, classificação, sinais, rastreador e alpha.
Copy trading aqui é observação: o Alladin não replica ordem nessas contas.
"""
import json
import os
from urllib.parse import urlencode
from .transport import DataError

SOURCES = ('binance', 'okx', 'coingecko', 'coinmarketcap', 'dexscreener', 'gmgn')
GMGN_CHAINS = {'sol', 'eth', 'base', 'bsc'}
_QUOTES = ('USDT', 'USDC', 'USD', 'BUSD')
_FORBIDDEN = ('private_key', 'secret', 'seed', 'mnemonic', 'api_key')


def _reject(values):
    blob = ' '.join(str(v).lower() for v in values)
    if any(word in blob for word in _FORBIDDEN):
        raise ValueError('Consulta de mercado não pode carregar segredo')


def _num(value):
    if value is None or value == '':
        return None
    number = float(value)
    if number != number or number in (float('inf'), float('-inf')):
        raise ValueError('Número de mercado inválido')
    return number


def base_asset(symbol):
    text = str(symbol or '').upper().replace('-', '').replace('_', '').replace('/', '')
    for quote in _QUOTES:
        if text.endswith(quote) and len(text) > len(quote):
            return text[:-len(quote)]
    return text


def tier_of(quote):
    cap = quote.get('market_cap')
    volume = quote.get('volume_24h') or 0
    if cap is not None:
        if cap >= 10_000_000_000:
            return 'mega'
        if cap >= 1_000_000_000:
            return 'large'
        if cap >= 100_000_000:
            return 'mid'
        if cap >= 10_000_000:
            return 'small'
        return 'micro'
    if volume >= 100_000_000:
        return 'volume_high'
    if volume >= 10_000_000:
        return 'volume_mid'
    return 'volume_low'


def signal_of(quote):
    change = quote.get('change_24h_pct')
    if change is None:
        return 'sem_variacao'
    if change >= 8:
        return 'impulso'
    if change <= -8:
        return 'queda'
    if change >= 3:
        return 'firme'
    if change <= -3:
        return 'fraco'
    return 'neutro'


def _quote(source, symbol, price, change=None, volume=None, market_cap=None, liquidity=None, chain=None):
    if not symbol or price is None or price <= 0:
        return None
    return {
        'source': source,
        'symbol': str(symbol).upper(),
        'base': base_asset(symbol),
        'price': price,
        'change_24h_pct': change,
        'volume_24h': volume,
        'market_cap': market_cap,
        'liquidity': liquidity,
        'chain': chain,
    }


def build_views(quotes, limit):
    rows = [q for q in quotes if q]
    rows.sort(key=lambda q: (-(q.get('volume_24h') or 0), q['source'], q['symbol']))
    ranking = []
    classification = []
    signals = []
    for index, quote in enumerate(rows[:limit], start=1):
        label = signal_of(quote)
        rank = dict(quote, rank=index, tier=tier_of(quote), signal=label, executed=False)
        ranking.append(rank)
        classification.append({
            'rank': index, 'base': quote['base'], 'source': quote['source'],
            'tier': rank['tier'], 'market_cap': quote.get('market_cap'),
            'volume_24h': quote.get('volume_24h')})
        signals.append({
            'base': quote['base'], 'source': quote['source'], 'signal': label,
            'change_24h_pct': quote.get('change_24h_pct'), 'price': quote['price']})
    grouped = {}
    for quote in rows:
        grouped.setdefault(quote['base'], []).append(quote)
    tracker = []
    for base, items in grouped.items():
        prices = [item['price'] for item in items]
        low, high = min(prices), max(prices)
        dispersion = (high - low) / low if low > 0 and len(prices) > 1 else 0.0
        tracker.append({
            'base': base,
            'sources': sorted({item['source'] for item in items}),
            'prices': {item['source']: item['price'] for item in items},
            'dispersion': dispersion,
        })
    tracker.sort(key=lambda item: (-len(item['sources']), -item['dispersion'], item['base']))
    alpha = []
    for item in tracker:
        if len(item['sources']) < 2:
            continue
        related = [q for q in rows if q['base'] == item['base']]
        best = max(related, key=lambda q: q.get('change_24h_pct') or -10**9)
        if signal_of(best) not in {'impulso', 'firme'}:
            continue
        alpha.append({
            'base': item['base'],
            'sources': item['sources'],
            'signal': signal_of(best),
            'change_24h_pct': best.get('change_24h_pct'),
            'execution': 'coinbase',
            'executed': False,
        })
    return {
        'execution': 'coinbase',
        'observation_only': True,
        'ranking': ranking,
        'classification': classification,
        'signals': signals,
        'tracker': tracker[:limit],
        'alpha': alpha[:limit],
        'copy_trading': {
            'mode': 'observacao',
            'note': 'Candidatos públicos. Nenhuma ordem sai da Binance, OKX, GMGN ou DEX. A operação, se armada, sai só pela Coinbase.',
            'candidates': alpha[:limit],
        },
    }


class MarketVision:
    def __init__(self, http):
        self.http = http

    def prices(self, symbol, sources=None, limit=20):
        _reject([symbol])
        if not isinstance(symbol, str) or not 2 <= len(symbol) <= 32:
            raise ValueError('Símbolo inválido')
        view = self.radar(sources=sources, symbols=[symbol], query=base_asset(symbol), limit=limit)
        view['symbol'] = symbol.upper()
        return view

    def radar(self, sources=None, symbols=None, query=None, limit=20, chain='sol'):
        chosen = self._sources(sources)
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError('Limite de mercado: 1–50')
        if chain not in GMGN_CHAINS:
            raise ValueError('Rede GMGN inválida')
        symbols = self._symbols(symbols)
        if query is not None:
            _reject([query])
            if not isinstance(query, str) or not 1 <= len(query) <= 32:
                raise ValueError('Consulta de mercado inválida')
        rows, errors = [], {}
        for source in chosen:
            try:
                rows.extend(self._fetch(source, symbols, query, limit, chain))
            except (DataError, ValueError, KeyError, TypeError) as exc:
                errors[source] = str(exc)[:160]
        view = build_views(rows, limit)
        view['sources'] = list(chosen)
        view['errors'] = errors
        return view

    def _sources(self, sources):
        if sources is None:
            return SOURCES
        if not isinstance(sources, list) or not sources or len(sources) > len(SOURCES):
            raise ValueError('Fontes inválidas')
        if any(source not in SOURCES for source in sources):
            raise ValueError('Fonte de mercado desconhecida')
        return tuple(dict.fromkeys(sources))

    def _symbols(self, symbols):
        if symbols is None:
            return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        if not isinstance(symbols, list) or not 1 <= len(symbols) <= 20:
            raise ValueError('Lista de símbolos: 1–20')
        clean = []
        for symbol in symbols:
            if not isinstance(symbol, str) or not symbol.isalnum() or not 5 <= len(symbol) <= 20:
                raise ValueError('Símbolo de corretora inválido')
            clean.append(symbol.upper())
        _reject(clean)
        return clean

    def _fetch(self, source, symbols, query, limit, chain):
        if source == 'binance':
            return self._binance(symbols)
        if source == 'okx':
            return self._okx(limit)
        if source == 'coingecko':
            return self._coingecko(limit)
        if source == 'coinmarketcap':
            return self._cmc(limit)
        if source == 'dexscreener':
            return self._dex(query or base_asset(symbols[0]), limit)
        return self._gmgn(chain, limit)

    def _binance(self, symbols):
        query = urlencode({'symbols': json.dumps(symbols, separators=(',', ':')), 'type': 'FULL'})
        data = self.http.json('https://api.binance.com/api/v3/ticker/24hr?' + query)
        if not isinstance(data, list):
            raise DataError('Ticker Binance inválido')
        rows = []
        for item in data:
            if not isinstance(item, dict):
                continue
            rows.append(_quote('binance', item.get('symbol'), _num(item.get('lastPrice')),
                               _num(item.get('priceChangePercent')), _num(item.get('quoteVolume'))))
        return [row for row in rows if row]

    def _okx(self, limit):
        data = self.http.json('https://www.okx.com/api/v5/market/tickers?' + urlencode({'instType': 'SPOT'}))
        items = data.get('data') if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise DataError('Ticker OKX inválido')
        rows = []
        for item in items:
            if not isinstance(item, dict) or not str(item.get('instId', '')).endswith('-USDT'):
                continue
            last, opened = _num(item.get('last')), _num(item.get('open24h'))
            change = ((last - opened) / opened * 100) if last and opened else None
            rows.append(_quote('okx', item.get('instId'), last, change, _num(item.get('volCcy24h'))))
            if len(rows) >= limit:
                break
        return [row for row in rows if row]

    def _coingecko(self, limit):
        query = urlencode({'vs_currency': 'usd', 'order': 'volume_desc', 'per_page': limit,
                           'page': 1, 'price_change_percentage': '24h'})
        headers = {}
        key = os.environ.get('COINGECKO_API_KEY', '')
        if key:
            headers['x-cg-demo-api-key'] = key
        data = self.http.json('https://api.coingecko.com/api/v3/coins/markets?' + query, headers=headers or None)
        if not isinstance(data, list):
            raise DataError('Mercado CoinGecko inválido')
        rows = []
        for item in data:
            if not isinstance(item, dict):
                continue
            rows.append(_quote('coingecko', item.get('symbol'), _num(item.get('current_price')),
                               _num(item.get('price_change_percentage_24h')),
                               _num(item.get('total_volume')), _num(item.get('market_cap'))))
        return [row for row in rows if row]

    def _cmc(self, limit):
        key = os.environ.get('CMC_API_KEY', '')
        if not key:
            raise DataError('CMC_API_KEY ausente')
        query = urlencode({'start': 1, 'limit': limit, 'convert': 'USD'})
        data = self.http.json(
            'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest?' + query,
            headers={'X-CMC_PRO_API_KEY': key})
        items = data.get('data') if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise DataError('Listagem CoinMarketCap inválida')
        rows = []
        for item in items:
            usd = ((item or {}).get('quote') or {}).get('USD') or {}
            rows.append(_quote('coinmarketcap', item.get('symbol'), _num(usd.get('price')),
                               _num(usd.get('percent_change_24h')), _num(usd.get('volume_24h')),
                               _num(usd.get('market_cap'))))
        return [row for row in rows if row]

    def _dex(self, query, limit):
        data = self.http.json('https://api.dexscreener.com/latest/dex/search?' + urlencode({'q': query}))
        pairs = data.get('pairs') if isinstance(data, dict) else None
        if not isinstance(pairs, list):
            raise DataError('Pares DexScreener inválidos')
        rows = []
        for pair in pairs[:limit]:
            if not isinstance(pair, dict):
                continue
            base = (pair.get('baseToken') or {}).get('symbol')
            volume = (pair.get('volume') or {}).get('h24')
            change = (pair.get('priceChange') or {}).get('h24')
            liquidity = (pair.get('liquidity') or {}).get('usd')
            rows.append(_quote('dexscreener', base, _num(pair.get('priceUsd')), _num(change),
                               _num(volume), liquidity=_num(liquidity), chain=pair.get('chainId')))
        return [row for row in rows if row]

    def _gmgn(self, chain, limit):
        query = urlencode({'orderby': 'volume', 'direction': 'desc', 'limit': limit})
        data = self.http.json(f'https://gmgn.ai/defi/quotation/v1/rank/{chain}/swaps/24h?{query}')
        items = _gmgn_rows(data)
        rows = []
        for item in items[:limit]:
            token = item.get('token') if isinstance(item.get('token'), dict) else item
            symbol = token.get('symbol') or item.get('symbol')
            price = _num(token.get('price') if token.get('price') is not None else item.get('price'))
            volume = _num(item.get('volume') if item.get('volume') is not None else item.get('volume_24h'))
            change = _num(item.get('price_change_percent') if item.get('price_change_percent') is not None
                          else item.get('change'))
            liquidity = _num(item.get('liquidity'))
            rows.append(_quote('gmgn', symbol, price, change, volume, liquidity=liquidity, chain=chain))
        if not rows:
            raise DataError('Ranking GMGN sem preços utilizáveis')
        return rows


def _gmgn_rows(data):
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if not isinstance(data, dict):
        raise DataError('Ranking GMGN inválido')
    body = data.get('data', data)
    if isinstance(body, list):
        return [row for row in body if isinstance(row, dict)]
    if isinstance(body, dict):
        for key in ('rank', 'swaps', 'tokens', 'list'):
            if isinstance(body.get(key), list):
                return [row for row in body[key] if isinstance(row, dict)]
    raise DataError('Ranking GMGN inválido')
