"""Product-specific Coinbase spot observations and executable book estimates."""
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from types import SimpleNamespace
import math
import time
from urllib.parse import quote

from .features import features
from .instruments import CoinbaseInstruments, product_id
from .spot_policy import dec
from .transport import DataError

GRANULARITIES = {60:'ONE_MINUTE',300:'FIVE_MINUTE',900:'FIFTEEN_MINUTE',3600:'ONE_HOUR'}


def stamp(value):
    if not isinstance(value, str):
        raise DataError('Coinbase source timestamp is missing')
    try:
        parsed = datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.timestamp()
    except (ValueError, OverflowError):
        raise DataError('Coinbase source timestamp is invalid') from None


def fresh(book, now, age=30):
    timestamp = stamp(book.get('source_time'))
    if not -5 <= now - timestamp <= age:
        raise DataError('STALE_BOOK: refresh Coinbase book; no fill applied', code='stale_book')


def entry_blocks(instrument):
    blocks = []
    if instrument.get('product_type') != 'SPOT':
        blocks.append('product_type_requires_different_adapter')
    if str(instrument.get('product_venue','')).upper() == 'DERIBIT':
        blocks.append('venue_requires_different_adapter')
    if instrument.get('status','').lower() not in ('online','tradable','active'):
        blocks.append('product_not_online')
    for flag in ('is_disabled','trading_disabled','cancel_only','view_only','auction_mode','limit_only','post_only'):
        if instrument.get(flag) is True:
            blocks.append(flag)
    for key in ('base_currency_id','quote_currency_id'):
        if not isinstance(instrument.get(key),str) or not instrument[key]:
            blocks.append('missing_' + key)
    return blocks


def walk(book, side, quantity, fee_bps, slippage_bps, collar_bps, limit_price=None):
    """Immediate-or-cancel simulation from an observed L2 snapshot.

No optimistic maker fills. Caller decides whether partial liquidity is accepted.
"""
    quantity = dec(quantity, 'quantity', Decimal('0.00000000000000000001'))
    levels = book['pricebook']['asks' if side == 'BUY' else 'bids']
    levels = sorted([(dec(x['price'],'price',Decimal('1e-25')),dec(x['size'],'size',0)) for x in levels],
                    reverse=side == 'SELL')
    best = levels[0][0]
    remaining, value, filled = quantity, Decimal(0), Decimal(0)
    collar = dec(collar_bps)/10000
    for price, size in levels:
        if abs(price/best-1) > collar:
            break
        if limit_price is not None and ((side == 'BUY' and price > limit_price) or (side == 'SELL' and price < limit_price)):
            break
        amount = min(size, remaining)
        value += amount * price
        filled += amount
        remaining -= amount
        if remaining == 0:
            break
    if not filled:
        raise ValueError('NO_LIQUIDITY: no executable size inside price collar')
    vwap = value/filled
    slippage = abs(vwap/best-1)*10000
    if slippage > dec(slippage_bps):
        raise ValueError('SLIPPAGE_LIMIT: requested size exceeds permitted book impact')
    return dict(quantity=str(filled), unfilled=str(remaining), vwap=str(vwap),
                quote_notional=str(value), fee=str(value*dec(fee_bps)/10000),
                slippage_bps=str(slippage), best_price=str(best))


class SpotMarket:
    def __init__(self, source=None, clock=time.time):
        self.source = source or CoinbaseInstruments(clock=clock,ttl=300,page_size=500,collection_seconds=90)
        self.clock = clock
        self._bars = {}

    def catalog(self, refresh=False):
        return self.source.catalog(refresh)

    def instrument(self, pid):
        return self.source.instrument(product_id(pid))

    def book(self, pid):
        book = self.source.book(pid)
        fresh(book,self.clock())
        return book

    def candles(self, pid, timeframe=300, count=120):
        pid = product_id(pid)
        if timeframe not in GRANULARITIES or type(count) is not int or not 80 <= count <= 300:
            raise ValueError('Candles require supported timeframe and count between 80 and 300')
        end = int(self.clock())//timeframe*timeframe
        key = (pid,timeframe,count,end)
        if key in self._bars:
            return self._bars[key]
        data = self.source._get('products/'+quote(pid,safe='')+'/candles',
                dict(start=end-(count+2)*timeframe,end=end,granularity=GRANULARITIES[timeframe],limit=count+2))
        rows = data.get('candles')
        if not isinstance(rows,list):
            raise DataError('Invalid Coinbase candle response')
        bars = {}
        try:
            for row in rows:
                ts = int(row['start'])
                if ts % timeframe:
                    raise ValueError('misaligned candle')
                if ts+timeframe > self.clock():
                    continue
                values = {name:float(dec(row[name],name,Decimal('1e-25'))) for name in ('open','high','low','close')}
                volume = float(dec(row['volume'],'volume',0))*values['close']
                if not all(math.isfinite(x) for x in (*values.values(),volume)):
                    raise ValueError('nonfinite candle')
                if not values['low'] <= min(values['open'],values['close']) <= max(values['open'],values['close']) <= values['high']:
                    raise ValueError('invalid OHLC')
                bar = SimpleNamespace(timestamp=ts,volume=volume,**values)
                if ts in bars and vars(bars[ts]) != vars(bar):
                    raise ValueError('conflicting candle')
                bars[ts] = bar
        except (KeyError,TypeError,ValueError,OverflowError):
            raise DataError('Invalid Coinbase closed candle') from None
        result = sorted(bars.values(),key=lambda x:x.timestamp)[-count:]
        # An old gap need not invalidate a sufficiently long current suffix.
        # Do not synthesize missing bars or treat irregular rows as uniform time.
        for index in range(len(result)-1,0,-1):
            if result[index].timestamp-result[index-1].timestamp != timeframe:
                result=result[index:]
                break
        if len(result)<80:
            raise DataError('CANDLE_GAP: insufficient contiguous closed Coinbase candles',code='candle_gap')
        if result[-1].timestamp+timeframe != end:
            raise DataError('STALE_CANDLES: latest completed candle is missing')
        self._bars = {k:v for k,v in self._bars.items() if k[-1] >= end-timeframe}
        self._bars[key] = result
        return result

    def observation(self, pid, timeframe=300):
        instrument = self.instrument(pid)
        effective=timeframe
        for candidate in [x for x in GRANULARITIES if x>=timeframe]:
            try:
                bars=self.candles(pid,candidate)
                effective=candidate
                break
            except DataError as exc:
                if exc.code!='candle_gap' or candidate==3600:
                    raise
        f = features(bars)
        book = self.book(pid)  # slow metadata/candles first, fresh book last
        if self.clock()-(bars[-1].timestamp+effective) > effective:
            raise DataError('STALE_CANDLES: context expired during collection')
        bid,ask = dec(book['bid']),dec(book['ask'])
        f['returns'] = [math.log(b.close/a.close) for a,b in zip(bars,bars[1:])][-64:]
        return dict(product_id=pid,instrument=instrument,book=book,features=f,
                    last_closed_at=bars[-1].timestamp+effective,timeframe_seconds=effective,
                    spread_bps=str((ask-bid)/((ask+bid)/2)*10000),
                    volume_24h_quote=str(dec(instrument.get('volume_24h','0'),'volume_24h',0)*dec(instrument.get('price',book['bid']),'price',0)))
