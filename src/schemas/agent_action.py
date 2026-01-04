from enum import Enum
from pydantic import BaseModel, field_validator


class ActionType(str, Enum):
    BUY_MARKET = "BUY_MARKET"
    SELL_MARKET = "SELL_MARKET"
    HOLD = "HOLD"


class AgentAction(BaseModel):
    agent_id: str
    tick_id: str
    reasoning: str
    action: ActionType
    asset: str | None = None
    size_usd: float | None = None     
    size_asset: float | None = None    
    limit_price: float | None = None

    @field_validator("action", mode="before")
    @classmethod
    def validate_action(cls, v):
        if isinstance(v, str):
            v = v.upper()
            if v in ["BUY", "BUY_MARKET"]:
                return ActionType.BUY_MARKET
            if v in ["SELL", "SELL_MARKET"]:
                return ActionType.SELL_MARKET
            if v == "HOLD":
                return ActionType.HOLD
        return v

    @classmethod
    def hold(cls, agent_id: str, tick_id: str, reasoning: str = "Unable to parse action") -> "AgentAction":
        return cls(
            agent_id=agent_id,
            tick_id=tick_id,
            reasoning=reasoning,
            action=ActionType.HOLD,
        )
