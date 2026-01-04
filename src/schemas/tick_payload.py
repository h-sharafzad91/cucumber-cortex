from pydantic import BaseModel


class Candle(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: str


class PriceData(BaseModel):
    price: float
    source: str


class Candles(BaseModel):
    m1: list[Candle] = []
    m5: list[Candle] = []
    h1: list[Candle] = []


class MarketData(BaseModel):
    ETH_USDC: PriceData
    candles: dict[str, Candles] = {}


class Position(BaseModel):
    asset: str
    size: float
    entry_price: float
    current_price: float | None = None
    unrealized_pnl: float | None = None


class Portfolio(BaseModel):
    balance_usd: float
    positions: list[Position] = []


class Constraints(BaseModel):
    max_usd_order: float
    allowed_assets: list[str]


class TickPayload(BaseModel):
    tick_id: str
    round_id: str
    agent_id: str
    tick_number: int
    timestamp: str
    market: MarketData
    portfolio: Portfolio
    constraints: Constraints
