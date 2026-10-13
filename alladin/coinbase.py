"""Adaptadores Coinbase. Cotação não é fill. Segredo não entra no pedido do agente.

Fontes: Coinbase Developer Platform, outubro de 2026.
- AgentKit: https://docs.cdp.coinbase.com/agent-kit/welcome
- Trade API (swaps EVM): https://docs.cdp.coinbase.com/trade-api/welcome
- Advanced Trade: https://docs.cdp.coinbase.com/coinbase-business/advanced-trade-apis/rest-api
- JWT: https://docs.cdp.coinbase.com/get-started/authentication/jwt-authentication
"""
from urllib.parse import urlencode
from .models import EVM_CHAINS, evm_address
from .transport import DataError

BROKERAGE_HOST = 'api.coinbase.com'
CDP_HOST = 'api.cdp.coinbase.com'
SWAP_NETWORKS = {'ethereum', 'base', 'arbitrum', 'optimism', 'polygon'}
CANDLE_GRANULARITY = {60, 300, 900, 3600, 21600, 86400}
FORBIDDEN = {'private_key', 'secret', 'seed', 'keypair', 'mnemonic', 'api_key', 'api_key_secret'}

def _reject_secrets(args):
    if not isinstance(args, dict):
        raise ValueError('Pedido Coinbase inválido')
    names = {k.lower() for k in args}
    blob = ' '.join(str(v).lower() for v in args.values())
    if names & FORBIDDEN or any(word in blob for word in FORBIDDEN):
        raise ValueError('Pedido Coinbase não pode carregar segredo')

class Coinbase:
    """Leitura pública da corretora e operações autenticadas injetando o JWT por fora."""
    def __init__(self, http, authorize=None):
        self.http = http
        self.authorize = authorize

    def _headers(self, method, host, path):
        if self.authorize is None:
            raise DataError('Autenticação Coinbase ausente; a chave fica fora do agente')
        headers = self.authorize(method, host, path)
        if not isinstance(headers, dict) or 'Authorization' not in headers:
            raise DataError('JWT Coinbase ausente')
        if any(word in str(headers).lower() for word in ('private_key', 'api_key_secret')):
            raise DataError('Cabeçalho de autenticação expôs material de chave')
        return headers

    def products(self, product_type='SPOT', limit=50):
        if product_type not in {'SPOT', 'FUTURE'} or type(limit) is not int or not 1 <= limit <= 250:
            raise ValueError('Consulta de produtos inválida')
        query = urlencode(dict(product_type=product_type, limit=limit))
        url = f'https://{BROKERAGE_HOST}/api/v3/brokerage/market/products?{query}'
        data = self.http.json(url)
        products = data.get('products') if isinstance(data, dict) else None
        if not isinstance(products, list):
            raise DataError('Lista de produtos Coinbase inválida')
        return dict(venue='coinbase_advanced_trade', product_type=product_type,
                    products=[_product(p) for p in products[:limit]])

    def candles(self, product_id, start, end, granularity=900):
        if not isinstance(product_id, str) or not 1 <= len(product_id) <= 40 or granularity not in CANDLE_GRANULARITY:
            raise ValueError('Candle Coinbase inválido')
        if type(start) is not int or type(end) is not int or end <= start:
            raise ValueError('Janela de candles inválida')
        path = f'/api/v3/brokerage/market/products/{product_id}/candles'
        query = urlencode(dict(start=start, end=end, granularity=granularity))
        data = self.http.json(f'https://{BROKERAGE_HOST}{path}?{query}')
        rows = data.get('candles') if isinstance(data, dict) else None
        if not isinstance(rows, list):
            raise DataError('Candles Coinbase inválidos')
        return dict(venue='coinbase_advanced_trade', product_id=product_id, granularity=granularity,
                    candles=[_candle(row) for row in rows])

    def swap_quote(self, network, from_token, to_token, from_amount, taker):
        _reject_secrets(dict(network=network, from_token=from_token, to_token=to_token,
                             from_amount=from_amount, taker=taker))
        if network not in EVM_CHAINS:
            raise ValueError('Swap Coinbase deste plano aceita ethereum, base e arbitrum')
        evm_address(from_token)
        evm_address(to_token)
        evm_address(taker)
        if type(from_amount) is not int or from_amount <= 0:
            raise ValueError('from_amount deve ser inteiro na unidade mínima do token')
        path = '/platform/v2/evm/swaps/quote'
        query = urlencode(dict(network=network, fromToken=from_token, toToken=to_token,
                               fromAmount=from_amount, taker=taker))
        headers = self._headers('GET', CDP_HOST, path)
        data = self.http.json(f'https://{CDP_HOST}{path}?{query}', headers=headers, retry=False)
        if not isinstance(data, dict):
            raise DataError('Cotação de swap Coinbase inválida')
        if data.get('liquidityAvailable') is not False and not data.get('toAmount'):
            raise DataError('Cotação de swap Coinbase inválida')
        return dict(venue='coinbase_trade_api', network=network, executed=False, quote=data)

    def preview_order(self, product_id, side, quote_size, client_order_id):
        body = _spot_order(product_id, side, quote_size, client_order_id)
        path = '/api/v3/brokerage/orders/preview'
        headers = self._headers('POST', BROKERAGE_HOST, path)
        data = self.http.json(f'https://{BROKERAGE_HOST}{path}', body, headers=headers, retry=False)
        if not isinstance(data, dict):
            raise DataError('Preview de ordem Coinbase inválido')
        return dict(venue='coinbase_advanced_trade', executed=False, preview=data)

    def create_order(self, product_id, side, quote_size, client_order_id, armed):
        if armed is not True:
            raise ValueError('Ordem Coinbase exige live_arm; preview não envia ordem')
        body = _spot_order(product_id, side, quote_size, client_order_id)
        path = '/api/v3/brokerage/orders'
        headers = self._headers('POST', BROKERAGE_HOST, path)
        data = self.http.json(f'https://{BROKERAGE_HOST}{path}', body, headers=headers, retry=False)
        if not isinstance(data, dict) or not data.get('success', True):
            return dict(venue='coinbase_advanced_trade', status='rejected', response=data if isinstance(data, dict) else {})
        order_id = data.get('order_id') or data.get('success_response', {}).get('order_id')
        if not order_id:
            return dict(venue='coinbase_advanced_trade', status='unknown', response={'order_id': None})
        return dict(venue='coinbase_advanced_trade', status='submitted', order_id=order_id, retried=False)

def _product(row):
    if not isinstance(row, dict) or not row.get('product_id'):
        raise DataError('Produto Coinbase inválido')
    return dict(product_id=row['product_id'],
                product_type=row.get('product_type', 'SPOT'),
                status=row.get('status'),
                base=row.get('base_currency_id') or row.get('base_currency'),
                quote=row.get('quote_currency_id') or row.get('quote_currency'))

def _candle(row):
    if not isinstance(row, dict):
        raise DataError('Candle Coinbase inválido')
    try:
        return dict(start=int(row['start']), open=float(row['open']), high=float(row['high']),
                    low=float(row['low']), close=float(row['close']), volume=float(row['volume']))
    except (KeyError, TypeError, ValueError):
        raise DataError('Candle Coinbase inválido') from None

def _spot_order(product_id, side, quote_size, client_order_id):
    body = dict(product_id=product_id, side=side, quote_size=quote_size, client_order_id=client_order_id)
    _reject_secrets(body)
    if not isinstance(product_id, str) or '-' not in product_id or side not in {'BUY', 'SELL'}:
        raise ValueError('Ordem spot Coinbase inválida')
    if not isinstance(quote_size, str) or not quote_size or quote_size.startswith('-'):
        raise ValueError('quote_size deve ser string positiva')
    if not isinstance(client_order_id, str) or not 8 <= len(client_order_id) <= 64:
        raise ValueError('client_order_id inválido')
    return dict(client_order_id=client_order_id, product_id=product_id, side=side,
                order_configuration={'market_market_ioc': {'quote_size': quote_size}})
