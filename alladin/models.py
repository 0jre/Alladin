from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import math
import re

SOL = 'So11111111111111111111111111111111111111112'
USDC = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
TOKEN_PROGRAM = 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'
MAINNET_GENESIS = '5eykt4UsFv8P8NJdTREpY1vzqKqZKvdpKuc147dw2N9d'

def finite(x, name, minimum=None, maximum=None):
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
        raise ValueError(f'{name}: número finito obrigatório')
    if minimum is not None and x < minimum or maximum is not None and x > maximum:
        raise ValueError(f'{name}: fora do intervalo permitido')
    return x

def pubkey(value):
    # Validate base58 decoded length, not just the printable length.
    alphabet = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
    if not isinstance(value, str) or not 32 <= len(value) <= 44:
        raise ValueError('Pubkey Solana inválida')
    n = 0
    for c in value:
        if c not in alphabet:
            raise ValueError('Pubkey Solana inválida')
        n = n * 58 + alphabet.index(c)
    zeros = len(value) - len(value.lstrip('1'))
    length = zeros + (n.bit_length() + 7) // 8
    if length != 32:
        raise ValueError('Pubkey deve decodificar para 32 bytes')
    return value

def utc_timestamp(value):
    d = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('Timestamp precisa de timezone')
    return int(d.timestamp())

@dataclass(frozen=True)
class Candle:
    timestamp: int  # opening time, UTC Unix seconds
    open: float
    high: float
    low: float
    close: float
    volume: float  # quote volume in USDC, for this bar only
    funding_rate: float = 0.0  # realized rate applying once during this bar
    chain: str = 'solana'
    mint: str = SOL
    def __post_init__(self):
        if self.chain != 'solana':
            raise ValueError('Somente Solana é permitida')
        pubkey(self.mint)
        finite(self.timestamp, 'timestamp', 0)
        if not isinstance(self.timestamp, int):
            raise ValueError('timestamp deve ser inteiro')
        for name in ['open', 'high', 'low', 'close']:
            finite(getattr(self, name), name, 1e-12)
        finite(self.volume, 'volume', 0)
        finite(self.funding_rate, 'funding_rate', -.1, .1)
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close) or self.low > self.high:
            raise ValueError('OHLC inconsistente')

@dataclass(frozen=True)
class Snapshot:
    timestamp: int  # observed-at; no historical lookahead
    mint: str = SOL
    chain: str = 'solana'
    price: float = 0.0
    liquidity_usd: float = 0.0
    volume_24h_usd: float = 0.0
    buy_sell_imbalance: float = 0.0
    mint_authority: str | None = None
    freeze_authority: str | None = None
    top10_account_share: float | None = None
    token_program: str = TOKEN_PROGRAM
    account_checked: bool = False
    cluster_verified: bool = False
    oracle_price: float | None = None
    oracle_timestamp: int | None = None
    expected_funding_hourly: float | None = None
    perp_market_verified: bool = False
    source: str = 'unknown'
    slot: int | None = None
    warnings: tuple = ()
    def __post_init__(self):
        if self.chain != 'solana':
            raise ValueError('Snapshot fora da Solana')
        pubkey(self.mint)
        finite(self.timestamp, 'snapshot.timestamp', 0)
        if type(self.timestamp) is not int:
            raise ValueError('snapshot.timestamp deve ser inteiro')
        for name in ['account_checked','cluster_verified','perp_market_verified']:
            if type(getattr(self,name)) is not bool:
                raise ValueError(f'{name}: booleano obrigatório')
        if self.oracle_timestamp is not None and (type(self.oracle_timestamp) is not int or self.oracle_timestamp < 0):
            raise ValueError('oracle_timestamp inválido')
        for name in ['mint_authority','freeze_authority']:
            if getattr(self,name) is not None:
                pubkey(getattr(self,name))
        if not isinstance(self.source,str) or len(self.source)>200:
            raise ValueError('source inválida')
        if not isinstance(self.warnings,(tuple,list)) or len(self.warnings)>30 or any(not isinstance(w,str) or len(w)>1000 for w in self.warnings):
            raise ValueError('warnings inválido')
        finite(self.price, 'snapshot.price', 1e-12)
        finite(self.liquidity_usd, 'liquidity', 0)
        finite(self.volume_24h_usd, 'volume_24h', 0)
        finite(self.buy_sell_imbalance, 'imbalance', -1, 1)
        if self.top10_account_share is not None:
            finite(self.top10_account_share, 'concentration', 0, 1)
        if self.oracle_price is not None:
            finite(self.oracle_price, 'oracle_price', 1e-12)
        if self.expected_funding_hourly is not None:
            finite(self.expected_funding_hourly, 'funding', -.1, .1)

@dataclass(frozen=True)
class Proposal:
    action: str = 'HOLD'
    market: str = 'spot'
    confidence: float = 0.0  # score, NOT calibrated probability
    stop_fraction: float = .02
    take_fraction: float = .04
    horizon_bars: int = 24
    thesis: str = 'No proposal'
    strategy: str = 'abstain'
    def __post_init__(self):
        if self.action not in {'LONG', 'SHORT', 'HOLD', 'CLOSE'} or self.market not in {'spot', 'perp'}:
            raise ValueError('Ação/mercado inválido')
        finite(self.confidence, 'confidence', 0, 1)
        finite(self.stop_fraction, 'stop', .005, .10)
        finite(self.take_fraction, 'take', .005, .30)
        if type(self.horizon_bars) is not int or not 1 <= self.horizon_bars <= 96:
            raise ValueError('horizon_bars inválido')
        if not isinstance(self.thesis, str) or len(self.thesis) > 2000:
            raise ValueError('thesis inválida')
        if not isinstance(self.strategy, str) or len(self.strategy) > 100:
            raise ValueError('strategy inválida')

@dataclass
class Position:
    id: str
    market: str
    side: int
    qty: float
    entry: float
    stop: float
    take: float
    margin: float
    opened_at: int
    expires_at: int
    strategy: str
    entry_cost: float
    funding_paid: float = 0.0
    best_close: float = 0.0

@dataclass
class Portfolio:
    cash: float
    initial: float
    peak: float
    day: str = ''
    day_start_equity: float = 0.0
    halted: bool = False
    halt_reason: str = ''
    cooldown_until: int = 0
    positions: list = field(default_factory=list)
    closed: list = field(default_factory=list)
    fees_paid: float = 0.0
    total_closed: int = 0
    def equity(self, price):
        return self.cash + sum(p.qty * price if p.market == 'spot' else
                               p.margin + p.side*p.qty*(price-p.entry) for p in self.positions)
    def gross(self, price):
        return sum(p.qty*price for p in self.positions)
    def net(self, price):
        return sum(p.side*p.qty*price for p in self.positions)
    def serialize(self):
        return asdict(self)
    @classmethod
    def restore(cls, d):
        d = dict(d)
        d['positions'] = [Position(**p) for p in d['positions']]
        return cls(**d)

@dataclass(frozen=True)
class Config:
    chain: str = 'solana'
    execution: str = 'paper'
    mint: str = SOL
    timeframe_seconds: int = 900
    initial_usdc: float = 10000
    warmup_bars: int = 80
    risk_per_trade: float = .003
    max_position_fraction: float = .15
    max_gross_fraction: float = .30
    max_net_fraction: float = .20
    max_open_risk: float = .01
    max_daily_loss: float = .02
    max_drawdown: float = .06
    min_liquidity_usd: float = 1000000
    min_volume_24h_usd: float = 1000000
    max_pool_participation: float = .0005
    max_top10_account_share: float = .50
    max_snapshot_age_seconds: int = 1800
    max_oracle_age_seconds: int = 120
    max_oracle_deviation: float = .01
    min_confidence: float = .65
    min_reward_risk: float = 1.8
    fee_bps: float = 10
    slippage_bps: float = 5
    fixed_cost_usdc: float = .02
    max_leverage: float = 2
    maintenance_fraction: float = .05
    max_entry_gap_fraction: float = .01
    max_historical_cvar: float = .04
    cooldown_bars: int = 4
    trailing_atr_multiple: float = 2.5
    allowed_markets: tuple = ('spot', 'perp')
    def __post_init__(self):
        if self.chain != 'solana' or self.execution != 'paper':
            raise ValueError('Este projeto aceita exclusivamente Solana e execução paper')
        pubkey(self.mint)
        if self.mint != SOL:
            raise ValueError('v0.2 suporta negociação SOL/USDC; outros mints apenas leitura via inspect')
        for name in ['risk_per_trade', 'max_position_fraction', 'max_gross_fraction', 'max_net_fraction',
                     'max_open_risk', 'max_daily_loss', 'max_drawdown', 'max_pool_participation',
                     'max_top10_account_share', 'max_oracle_deviation', 'min_confidence',
                     'max_entry_gap_fraction', 'max_historical_cvar', 'maintenance_fraction']:
            finite(getattr(self, name), name, .000001, 1)
        for name in ['initial_usdc', 'min_liquidity_usd', 'min_volume_24h_usd', 'min_reward_risk',
                     'trailing_atr_multiple']:
            finite(getattr(self, name), name, .000001)
        for name in ['fee_bps', 'slippage_bps', 'fixed_cost_usdc']:
            finite(getattr(self, name), name, 0)
        finite(self.max_leverage, 'max_leverage', 1, 3)
        for name in ['timeframe_seconds', 'max_snapshot_age_seconds', 'max_oracle_age_seconds',
                     'warmup_bars', 'cooldown_bars']:
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f'{name}: inteiro positivo obrigatório')
        if self.warmup_bars < 80:
            raise ValueError('warmup mínimo: 80 barras')
        if not self.allowed_markets or set(self.allowed_markets) - {'spot', 'perp'}:
            raise ValueError('allowed_markets inválido')
    @classmethod
    def load(cls, path):
        import json
        from pathlib import Path
        d = json.loads(Path(path).read_text())
        if 'allowed_markets' in d:
            d['allowed_markets'] = tuple(d['allowed_markets'])
        return cls(**d)
