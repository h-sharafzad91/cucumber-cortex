from pydantic import BaseModel, model_validator
from typing import Any


class Candle(BaseModel):
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: str


class PricePoint(BaseModel):
    price: float
    timestamp: str


class PriceData(BaseModel):
    price: float
    source: str
    price_history: list[PricePoint] = []


class Candles(BaseModel):
    m1: list[Candle] = []
    m5: list[Candle] = []
    h1: list[Candle] = []


class MarketData(BaseModel):
    """Market data with dynamic trading pair support.

    The price data is stored in a field named after the trading pair (e.g., BTC_USDT, ETH_USDC).
    Use get_price_data() to access it dynamically.
    """
    candles: dict[str, Candles] = {}
    trading_pair: str | None = None

    # Allow extra fields for dynamic trading pair keys (e.g., BTC_USDT, AVAX_USDT)
    model_config = {"extra": "allow"}

    def get_price_data(self) -> PriceData | None:
        """Get the price data for the trading pair."""
        if self.trading_pair:
            pair_key = self.trading_pair.replace("/", "_")
            data = getattr(self, pair_key, None)
            if data and isinstance(data, dict):
                return PriceData(**data)
        # Fallback: look for any PriceData-like field
        for key, value in self.__dict__.items():
            if key not in ("candles", "trading_pair") and isinstance(value, dict) and "price" in value:
                return PriceData(**value)
        return None

    def get_current_price(self) -> float:
        """Get the current price from the market data."""
        price_data = self.get_price_data()
        return price_data.price if price_data else 0.0

    @model_validator(mode="before")
    @classmethod
    def parse_price_data(cls, data: Any) -> Any:
        """Parse dynamic price data fields."""
        if isinstance(data, dict):
            # Convert any price data dicts to proper format
            for key, value in list(data.items()):
                if key not in ("candles", "trading_pair") and isinstance(value, dict) and "price" in value:
                    # Ensure price_history is properly formatted
                    if "price_history" in value and value["price_history"]:
                        value["price_history"] = [
                            PricePoint(**p) if isinstance(p, dict) else p
                            for p in value["price_history"]
                        ]
        return data


class Position(BaseModel):
    asset: str
    size: float
    entry_price: float
    current_price: float | None = None
    unrealized_pnl: float | None = None
    direction: str | None = None


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
