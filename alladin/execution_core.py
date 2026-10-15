"""Fail-closed native engine boundary. Native crashes cannot kill the gateway."""
from decimal import Decimal
import json
import subprocess
import sys
from .spot_policy import dec
from .storage import canonical


def fill(cfg,state,instrument,book,side,quantity,client_order_id,estimate,limit_price=None):
    if cfg.execution_engine=='reference':
        return dict(estimate,engine='reference_l2',engine_version='1')
    balances=dict(state['balances'])
    for position in state['positions'].values():
        c=position['base_currency']
        balances[c]=str(dec(balances.get(c,0))+dec(position['quantity']))
    request=dict(instrument=instrument,book=book,side=side,quantity=str(quantity),balances=balances,
                 fee_bps=cfg.taker_fee_bps,client_order_id=client_order_id,
                 limit_price=None if limit_price is None else str(limit_price))
    try:
        process=subprocess.run([sys.executable,'-m','alladin.nautilus_worker'],input=canonical(request),
            text=True,capture_output=True,timeout=15,check=False)
    except subprocess.TimeoutExpired:
        raise ValueError('NAUTILUS_TIMEOUT: native paper process terminated; ledger unchanged') from None
    if process.returncode:
        raise ValueError('NAUTILUS_PROCESS_FAILED: isolated native process failed; ledger unchanged')
    lines=[line.removeprefix('ALLADIN_NAUTILUS_RESULT ') for line in process.stdout.splitlines()
           if line.startswith('ALLADIN_NAUTILUS_RESULT ')]
    if len(lines)!=1:
        raise ValueError('NAUTILUS_PROTOCOL_ERROR: no unique native result')
    response=json.loads(lines[0])
    if not response.get('ok'):
        raise ValueError('NAUTILUS_EXECUTION_FAILED: '+response.get('message','native rejection'))
    result=response['result']
    qty=dec(result['quantity'],'native quantity',Decimal('1e-25'),dec(quantity))
    actual=dec(result['vwap'],'native price',Decimal('1e-25'))
    expected=dec(estimate['vwap'])
    # Native matching must agree with the already approved visible book.
    # Different precision/currency semantics are incidents, never silent fills.
    if abs(actual/expected-1)*10000>Decimal('.01'):
        raise ValueError('NAUTILUS_FILL_DIVERGENCE: native matching differs from approved L2')
    if qty!=dec(quantity):
        raise ValueError('NAUTILUS_SIZE_DIVERGENCE: reprepare from actual visible liquidity')
    return result
