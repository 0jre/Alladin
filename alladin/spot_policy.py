"""Versioned multi-instrument paper policy. No model or exchange credentials."""
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
import hashlib
import json
from .storage import canonical


def dec(value, name='number', minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise ValueError(name + ': finite decimal required')
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError(name + ': finite decimal required') from None
    if not result.is_finite() or (minimum is not None and result < minimum) or (maximum is not None and result > maximum):
        raise ValueError(name + ': outside permitted range')
    if len(result.as_tuple().digits) > 40 or abs(result.as_tuple().exponent) > 30:
        raise ValueError(name + ': excessive precision')
    return result


def text(value, name, maximum=2000):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
        raise ValueError(name + ': nonempty text required')
    return value


@dataclass(frozen=True)
class SpotPolicy:
    backend: str = 'portfolio'
    execution: str = 'paper'
    execution_engine: str = 'nautilus'
    chain: str = 'coinbase'  # compatibility for health metadata, not a blockchain
    reporting_currency: str = 'USDC'
    initial_balances: dict = field(default_factory=lambda: {'USDC': '250'})
    timeframe_seconds: int = 300
    max_snapshot_age_seconds: int = 30
    proposal_ttl_seconds: int = 30
    max_positions: int = 5
    max_orders_per_minute: int = 6
    max_orders_per_day: int = 60
    max_scan_products: int = 8
    risk_per_trade: str = '0.005'
    max_open_risk: str = '0.02'
    max_position_fraction: str = '0.25'
    max_gross_fraction: str = '0.80'
    max_agent_fraction: str = '0.80'
    max_strategy_fraction: str = '0.50'
    max_correlated_fraction: str = '0.50'
    correlation_threshold: str = '0.80'
    max_daily_loss: str = '0.02'
    max_drawdown: str = '0.06'
    max_spread_bps: str = '40'
    max_slippage_bps: str = '30'
    price_collar_bps: str = '50'
    max_quote_drift_bps: str = '30'
    min_volume_24h: str = '1000000'
    max_participation: str = '0.0005'
    min_reward_risk: str = '1.5'
    taker_fee_bps: str = '20'
    max_consecutive_losses: int = 3
    cooldown_seconds: int = 300

    def __post_init__(self):
        if self.backend != 'portfolio' or self.execution != 'paper' or self.chain != 'coinbase':
            raise ValueError('Portfolio backend supports Coinbase paper execution only')
        if self.execution_engine not in ('nautilus','reference'):
            raise ValueError('Unknown execution engine; no implicit fallback')
        for value in (self.reporting_currency, *self.initial_balances):
            if not isinstance(value, str) or not value.isalnum() or len(value) > 20:
                raise ValueError('Invalid currency identifier')
        if not self.initial_balances or not any(dec(v, 'initial balance', 0) > 0 for v in self.initial_balances.values()):
            raise ValueError('At least one positive initial balance is required')
        for name in ('risk_per_trade','max_open_risk','max_position_fraction','max_gross_fraction',
                     'max_agent_fraction','max_strategy_fraction','max_correlated_fraction',
                     'correlation_threshold','max_daily_loss','max_drawdown','max_participation'):
            dec(getattr(self, name), name, Decimal('0.000001'), 1)
        for name in ('max_spread_bps','max_slippage_bps','price_collar_bps','max_quote_drift_bps','taker_fee_bps'):
            dec(getattr(self, name), name, 0, 1000)
        dec(self.min_reward_risk, 'min_reward_risk', 1, 10)
        dec(self.min_volume_24h, 'min_volume_24h', 0)
        for name, low, high in [('proposal_ttl_seconds',5,120),('max_positions',1,20),
                                ('max_orders_per_minute',1,100),('max_orders_per_day',1,1000),
                                ('max_scan_products',1,30),('max_snapshot_age_seconds',1,30),
                                ('max_consecutive_losses',1,20),('cooldown_seconds',0,86400)]:
            if type(getattr(self, name)) is not int or not low <= getattr(self,name) <= high:
                raise ValueError(name + ': invalid integer')
        if self.timeframe_seconds not in (60,300,900,3600):
            raise ValueError('Unsupported candle timeframe')

    @property
    def fingerprint(self):
        return hashlib.sha256(canonical(asdict(self)).encode()).hexdigest()

    @classmethod
    def load(cls, path):
        with open(path) as source:
            return cls(**json.load(source))
