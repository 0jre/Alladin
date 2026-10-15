"""Strict MCP schemas for the portfolio backend; reusable HTTP command inventory."""


def specifications():
    string={'type':'string'}
    boolean={'type':'boolean'}
    decimal={'type':'string','description':'Finite decimal string; fractions are 0..1, not percentages.'}
    pid={'type':'string','description':'Canonical Coinbase product_id; never a blockchain mint.'}
    return [
        ('list_products','List all Coinbase catalog types with actual adapter support; paginate results.',{}, {'quote_currency':string,'limit':{'type':'integer'},'offset':{'type':'integer'},'refresh':boolean}),
        ('scan_opportunities','Rank a bounded, diverse subset of active Coinbase spot tokens, including memecoins when listed. Advisory scenarios, never profit probabilities.',{}, {'limit':{'type':'integer'},'product_ids':{'type':'array','items':string}}),
        *[(name,description,{}, {}) for name,description in [
            ('get_session_brief','Read mode, balances, positions, limits, valuation age and halt state.'),
            ('get_portfolio','Read shared cash authority and per-currency realized PnL; do not equate currencies.'),
            ('get_positions','Read open spot positions and backend paper protection.'),
            ('get_risk_budget','Read policy, current budget and valuation age; stale values never authorize entry.'),
            ('get_system_status','Read halt, cooldown and valuation freshness.'),
            ('get_fills','Read the most recent 100 simulated fills.'),
            ('get_trade_journal','Read recent fills with linked theses.'),
            ('get_performance','Read observed paper performance; no return guarantee.'),
            ('get_open_orders','IOC simulator has no resting orders; unfilled remainder is cancelled.'),
            ('get_fee_tier','Configured paper taker fee assumption; not a verified private account fee tier.')]],
        ('reconcile','Verify internal cash/inventory projections against balanced journal postings. No exchange account is connected.',{},{}),
        *[(name,description,{'product_id':pid},{}) for name,description in [
            ('get_market_snapshot','Read product metadata, closed-bar features and fresh L2 book.'),
            ('get_orderbook','Read validated public L2 book with source time.'),
            ('get_candles','Read contiguous closed Coinbase candles; no synthetic gap filling.')]],
        ('get_order','Read an actual simulated order by ID.',{'order_id':string},{}),
        ('estimate_execution','Estimate current buy VWAP, partial depth and configured fee from a quote budget. Does not approve a trade.',{'product_id':pid,'quote_budget':decimal},{}),
        ('get_microstructure','Read visible L2 imbalance and depth. Does not invent unavailable taker flow.',{'product_id':pid},{}),
        ('log_thesis','Record thesis and explicit invalidation before proposing a trade.',
            {'product_id':pid,'agent_id':string,'strategy':string,'thesis':string,'invalidation':string,'horizon_seconds':{'type':'integer'}},
            {'dry_run':boolean,'purpose':{'type':'string','enum':['strategy','execution_validation']}}),
        ('propose_trade','Calculate server-side size, walk book, check shared risk and return an expiring proposal. No fill.',
            {'thesis_id':string,'stop_price':decimal,'take_profit_price':decimal,'risk_fraction':decimal},
            {'order_type':{'type':'string','enum':['MARKET_IOC','LIMIT_IOC']},'limit_price':decimal,
             'partial_fill_policy':{'type':'string','enum':['ACCEPT','REJECT']},'trailing_fraction':decimal,'dry_run':boolean}),
        ('commit_trade','Commit a valid proposal exactly once. Rechecks current data, account authority and risk; paper only.',{'proposal_id':string},{'dry_run':boolean}),
        ('close_position','Reduce or close a spot position at observed bids. Allowed during halt. Partial depth can leave exposure.',{'product_id':pid},{'fraction':decimal,'dry_run':boolean}),
        ('set_protection','Tighten paper stop or trailing protection. Requires a running worker; no native exchange order.',{'product_id':pid},{'stop_price':decimal,'take_profit_price':decimal,'trailing_fraction':decimal,'dry_run':boolean}),
        ('halt_trading','Cancel uncommitted proposals and block entries. Closing remains available; does not flatten.',{},{'dry_run':boolean}),
        ('cancel_order','Cancel an uncommitted proposal; does not reverse a fill.',{'proposal_id':string},{'dry_run':boolean}),
        ('cancel_all','Cancel all uncommitted proposals; does not close positions.',{},{'dry_run':boolean}),
    ]


def contract():
    return dict(version='0.7',execution='paper',backend='portfolio',product_scope='coinbase_spot',
        interfaces=['authenticated_http','mcp_stdio','cli'],
        commands={name:dict(required=list(required),optional=list(optional),description=description)
                  for name,description,required,optional in specifications()},
        worker_command='paper_tick',flow=['scan_opportunities','log_thesis','propose_trade','commit_trade','paper_tick','close_position'],
        unsupported=['live_orders','resting_limit_orders','native_exchange_protection','derivative_execution','oauth_streamable_http'],
        notes=['Full catalog visible; executable spot instruments selected by metadata, not a token allowlist.',
               'Public catalog does not verify account/regional eligibility.',
               'External sessions provide reasoning. No embedded model or AI keys.',
               'Configured fees are assumptions. IOC fills use visible book; queue and latency are not reproduced.'])
