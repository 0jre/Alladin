"""Um comando, dois transportes. HTTP e MCP chamam a mesma função."""
import os
from .coinbase import Coinbase
from .connect import bearer, connect_request, connection_status
from .market import MarketVision
from .platforms import desks, platforms
from .transport import HTTP, DataError

READS = {
    'coinbase_products', 'coinbase_candles', 'coinbase_quote', 'coinbase_preview', 'coinbase_order',
    'market_radar', 'market_prices', 'coinbase_connect', 'coinbase_connection', 'desks', 'platforms',
}


def coinbase_auth(method, host, path):
    token = os.environ.get('COINBASE_JWT', '') or (bearer() or '')
    if not token:
        raise DataError('COINBASE_JWT ausente e a conta OAuth ainda não está conectada')
    return {'Authorization': 'Bearer ' + token}


def _read(service, name, args):
    book = Coinbase(HTTP(), authorize=coinbase_auth)
    if name == 'coinbase_products' and set(args) <= {'product_type', 'limit'}:
        return book.products(**args)
    if name == 'coinbase_candles' and {'product_id', 'start', 'end'} <= set(args) <= {'product_id', 'start', 'end', 'granularity'}:
        return book.candles(**args)
    if name == 'coinbase_quote' and set(args) == {'network', 'from_token', 'to_token', 'from_amount', 'taker'}:
        return book.swap_quote(**args)
    if name == 'coinbase_preview' and set(args) == {'product_id', 'side', 'quote_size', 'client_order_id'}:
        return book.preview_order(**args)
    if name == 'coinbase_order' and set(args) == {'product_id', 'side', 'quote_size', 'client_order_id'}:
        if service.cfg.execution != 'live' or service.cfg.live_arm is not True:
            raise ValueError('Ordem Coinbase exige execução live armada')
        return book.create_order(**args, armed=True)
    if name == 'market_radar' and set(args) <= {'sources', 'symbols', 'query', 'limit', 'chain'}:
        return MarketVision(HTTP()).radar(**args)
    if name == 'market_prices' and {'symbol'} <= set(args) <= {'symbol', 'sources', 'limit'}:
        return MarketVision(HTTP()).prices(**args)
    if name == 'coinbase_connect' and set(args) <= {'scopes', 'trade'}:
        return connect_request(**args)
    if name == 'coinbase_connection' and args == {}:
        return connection_status()
    if name == 'desks' and set(args) <= {'desk'}:
        return desks(**args)
    if name == 'platforms' and set(args) <= {'name'}:
        return platforms(**args)
    raise ValueError('Argumentos inválidos')


def execute(service, name, args, key):
    if not isinstance(name, str) or not isinstance(args, dict):
        raise ValueError('Comando inválido')
    request = {'command': name, 'args': args}
    if name in READS:
        with service.store.transaction() as db:
            return service.store.once(db, key, request, lambda: _read(service, name, args))
    return service.command(name, args, key)
