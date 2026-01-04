from enum import Enum
from pydantic import BaseModel


class RiskTolerance(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class TradingStrategy(str, Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    CUSTOM = "custom"


class TradingStyle(str, Enum):
    PAPER_HANDS = "paper_hands"
    NORMAL = "normal"
    DEGEN = "degen"


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    XAI = "xai"


AVAILABLE_MODELS_BY_PROVIDER = {
    LLMProvider.OPENAI: [
        {"id": "gpt-4o-mini", "name": "GPT-4o Mini", "recommended": True},
        {"id": "gpt-4o", "name": "GPT-4o", "recommended": False},
        {"id": "gpt-4-turbo", "name": "GPT-4 Turbo", "recommended": False},
    ],
    LLMProvider.ANTHROPIC: [
        {"id": "claude-sonnet-4-20250514", "name": "Claude Sonnet 4", "recommended": True},
        {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "recommended": False},
        {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku", "recommended": False},
    ],
    LLMProvider.GOOGLE: [
        {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash", "recommended": True},
        {"id": "gemini-1.5-pro", "name": "Gemini 1.5 Pro", "recommended": False},
        {"id": "gemini-1.5-flash", "name": "Gemini 1.5 Flash", "recommended": False},
    ],
    LLMProvider.XAI: [
        {"id": "grok-3", "name": "Grok 3", "recommended": True},
        {"id": "grok-3-fast", "name": "Grok 3 Fast", "recommended": False},
        {"id": "grok-2", "name": "Grok 2", "recommended": False},
    ],
}


class PersonaConfig(BaseModel):
    strategy: TradingStrategy = TradingStrategy.MOMENTUM
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    trading_style: TradingStyle = TradingStyle.NORMAL
    goal: str | None = None
    description: str | None = None
    leverage: float = 1.0
    stop_loss_percent: float = 5.0
    stop_loss_position_close_percent: float = 100.0
    take_profit_percent: float = 10.0
    take_profit_position_close_percent: float = 50.0


class WorkerConfig(BaseModel):
    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 500


class AgentConfig(BaseModel):
    id: str
    name: str
    persona_config: PersonaConfig
    worker_config: WorkerConfig
