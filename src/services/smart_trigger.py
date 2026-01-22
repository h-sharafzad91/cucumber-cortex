from typing import Optional
from ..schemas import TickPayload


class SmartTrigger:
    def __init__(
        self,
        min_ticks_between_calls: int = 3,
        price_threshold: float = 0.015,
        max_ticks_without_call: int = 15,
    ):
        self.min_ticks_between_calls = min_ticks_between_calls
        self.price_threshold = price_threshold
        self.max_ticks_without_call = max_ticks_without_call

        self.last_call_tick: Optional[int] = None
        self.last_price: Optional[float] = None
        self.ticks_since_last_call = 0

    def should_call_llm(self, tick: TickPayload) -> tuple[bool, str]:
        current_price = tick.market.get_current_price()
        current_tick = tick.tick_number if hasattr(tick, 'tick_number') else 0

        if self.last_call_tick is None:
            self.last_call_tick = current_tick
            self.last_price = current_price
            return True, "First decision - initializing"

        self.ticks_since_last_call = current_tick - self.last_call_tick

        if self.ticks_since_last_call < self.min_ticks_between_calls:
            return False, f"Only {self.ticks_since_last_call} ticks since last call (min: {self.min_ticks_between_calls})"

        if self.ticks_since_last_call >= self.max_ticks_without_call:
            self.last_call_tick = current_tick
            self.last_price = current_price
            return True, f"Force call after {self.ticks_since_last_call} ticks without LLM"

        if self.last_price:
            price_change = abs(current_price - self.last_price) / self.last_price

            if price_change >= self.price_threshold:
                self.last_call_tick = current_tick
                self.last_price = current_price
                return True, f"Significant price move: {price_change:.2%} (threshold: {self.price_threshold:.2%})"

        if tick.portfolio.positions:
            for position in tick.portfolio.positions:
                if position.size > 0:
                    if (position.unrealized_pnl is not None and
                        position.entry_price is not None and
                        position.entry_price > 0):

                        pnl_pct = position.unrealized_pnl / (position.entry_price * position.size)

                        if pnl_pct > 0.05 or pnl_pct < -0.03:
                            self.last_call_tick = current_tick
                            self.last_price = current_price
                            return True, f"Position PnL at threshold: {pnl_pct:.2%}"

        return False, "Market quiet - no significant changes"

    def reset(self):
        self.last_call_tick = None
        self.last_price = None
        self.ticks_since_last_call = 0
