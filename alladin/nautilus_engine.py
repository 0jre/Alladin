"""Pinned Nautilus v2 cash-account execution from an approved Coinbase L2 snapshot.

The durable Alladin ledger is the capital authority. Each atomic paper fill
rebuilds a native engine from that account snapshot, preserving native risk and
execution checks. No model calls, network I/O or exchange credentials occur here.
"""
from decimal import Decimal
import threading

from .spot_policy import dec
from .spot_market import stamp

VERSION='1.231.0'
_LOCK=threading.Lock()


def execute(instrument,book,side,quantity,balances,fee_bps,client_order_id,limit_price=None):
    try:
        import nautilus_trader
        from nautilus_trader.core.nautilus_pyo3 import (BacktestEngine,BacktestEngineConfig,
            Strategy,StrategyConfig,CurrencyPair,Currency,InstrumentId,Symbol,Price,Quantity,
            Money,Venue,OmsType,AccountType,BookType,BookOrder,OrderBookDelta,OrderBookDeltas,
            BookAction,OrderSide,QuoteTick,TimeInForce,ClientOrderId,StrategyId,LoggerConfig,LogLevel)
    except ImportError:
        raise ValueError('NAUTILUS_UNAVAILABLE: install Alladin engine dependencies; execution fails closed') from None
    if nautilus_trader.__version__!=VERSION:
        raise ValueError('NAUTILUS_VERSION_MISMATCH: expected '+VERSION)
    with _LOCK:
        iid=InstrumentId.from_str(instrument['product_id']+'.COINBASE')
        base=Currency.from_str(instrument['base_currency_id'])
        quote=Currency.from_str(instrument['quote_currency_id'])
        price_step=dec(instrument.get('price_increment',instrument['quote_increment']))
        size_step=dec(instrument['base_increment'])
        price_precision=max(0,-price_step.normalize().as_tuple().exponent)
        size_precision=max(0,-size_step.normalize().as_tuple().exponent)
        def price(value):return Price.from_str(format(dec(value),f'.{price_precision}f'))
        def size(value):return Quantity.from_str(format(dec(value),f'.{size_precision}f'))
        ts=int(stamp(book['source_time'])*1_000_000_000)
        native=CurrencyPair(iid,Symbol(instrument['product_id']),base,quote,price_precision,size_precision,
            price(price_step),size(size_step),ts,ts,
            min_quantity=size(instrument['base_min_size']),max_quantity=size(instrument['base_max_size']),
            min_notional=Money(dec(instrument['quote_min_size']),quote),max_notional=Money(dec(instrument['quote_max_size']),quote),
            maker_fee=Decimal(0),taker_fee=dec(fee_bps)/10000)
        class ApprovedIntent(Strategy):
            def __init__(self):
                super().__init__(StrategyConfig(strategy_id=StrategyId.from_str('ALLADIN-001')))
                self.sent=False
                self.fills=[]
                self.rejections=[]
            def on_start(self):
                self.subscribe_quotes(iid)
            def on_quote(self,event):
                if self.sent:return
                self.sent=True
                fields=dict(instrument_id=iid,order_side=OrderSide.BUY if side=='BUY' else OrderSide.SELL,
                    quantity=size(quantity),time_in_force=TimeInForce.IOC,
                    client_order_id=ClientOrderId.from_str(client_order_id))
                order=(self.order_factory.limit(price=price(limit_price),**fields)
                       if limit_price is not None else self.order_factory.market(**fields))
                self.submit_order(order)
            def on_order_filled(self,event):
                self.fills.append(dict(quantity=str(event.last_qty),price=str(event.last_px),
                    commission=str(event.commission.as_decimal()) if event.commission else '0',
                    commission_currency=event.commission.currency.code if event.commission else quote.code,
                    trade_id=str(event.trade_id)))
            def on_order_rejected(self,event):self.rejections.append(str(event))
            def on_order_denied(self,event):self.rejections.append(str(event))
        engine=BacktestEngine(BacktestEngineConfig(bypass_logging=True,run_analysis=False,
            logging=LoggerConfig(stdout_level=LogLevel.ERROR,is_colored=False,bypass_logging=True)))
        try:
            cash=[Money(dec(amount),Currency.from_str(currency)) for currency,amount in balances.items() if dec(amount)>0]
            engine.add_venue(Venue.from_str('COINBASE'),OmsType.NETTING,AccountType.CASH,cash,
                book_type=BookType.L2_MBP,allow_cash_borrowing=False,liquidity_consumption=True)
            engine.add_instrument(native)
            deltas=[]
            sequence=0
            for name,order_side in [('bids',OrderSide.BUY),('asks',OrderSide.SELL)]:
                for row in book['pricebook'][name]:
                    sequence+=1
                    deltas.append(OrderBookDelta(iid,BookAction.ADD,BookOrder(order_side,
                        price(row['price']),size(row['size']),sequence),0,sequence,ts,ts))
            # End-of-snapshot flag ensures the native book is complete before
            # the subsequent quote invokes the approved-intent strategy.
            last=deltas[-1]
            deltas[-1]=OrderBookDelta(iid,BookAction.ADD,last.order,128,sequence,ts,ts)
            engine.add_data([OrderBookDeltas(iid,deltas),QuoteTick(iid,price(book['bid']),
                price(book['ask']),size(book['pricebook']['bids'][0]['size']),
                size(book['pricebook']['asks'][0]['size']),ts+1,ts+1)])
            strategy=ApprovedIntent()
            engine.add_strategy(strategy)
            engine.run()
            if not strategy.fills:
                raise ValueError('NAUTILUS_REJECTED: no native fill; '+(';'.join(strategy.rejections))[:300])
            qty=sum((dec(x['quantity']) for x in strategy.fills),Decimal(0))
            amount=sum((dec(x['quantity'])*dec(x['price']) for x in strategy.fills),Decimal(0))
            if any(x['commission_currency']!=quote.code for x in strategy.fills):
                raise ValueError('NAUTILUS_FEE_CURRENCY: unsupported commission currency; no ledger commit')
            return dict(quantity=str(qty),quote_notional=str(amount),vwap=str(amount/qty),
                fee=str(sum((dec(x['commission']) for x in strategy.fills),Decimal(0))),
                engine='nautilus_trader',engine_version=VERSION,native_fills=strategy.fills,
                unfilled=str(dec(quantity)-qty))
        finally:
            engine.dispose()
