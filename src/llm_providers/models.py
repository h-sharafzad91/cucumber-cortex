from enum import Enum
from dataclasses import dataclass


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    XAI = "xai"


@dataclass
class LLMModel:
    id: str
    provider: LLMProvider
    name: str
    description: str
    max_tokens: int
    supports_system_prompt: bool = True
    supports_streaming: bool = True
    is_recommended: bool = False


OPENAI_MODELS = {
    "gpt-4o": LLMModel(
        id="gpt-4o",
        provider=LLMProvider.OPENAI,
        name="GPT-4o",
        description="Most capable OpenAI model, great for complex reasoning",
        max_tokens=4096,
        is_recommended=False,
    ),
    "gpt-4o-mini": LLMModel(
        id="gpt-4o-mini",
        provider=LLMProvider.OPENAI,
        name="GPT-4o Mini",
        description="Fast and cost-effective, good balance of speed and quality",
        max_tokens=4096,
        is_recommended=True,
    ),
    "gpt-4-turbo": LLMModel(
        id="gpt-4-turbo",
        provider=LLMProvider.OPENAI,
        name="GPT-4 Turbo",
        description="High capability with faster response times",
        max_tokens=4096,
    ),
    "gpt-3.5-turbo": LLMModel(
        id="gpt-3.5-turbo",
        provider=LLMProvider.OPENAI,
        name="GPT-3.5 Turbo",
        description="Fast and economical for simpler tasks",
        max_tokens=4096,
    ),
}

ANTHROPIC_MODELS = {
    "claude-sonnet-4-20250514": LLMModel(
        id="claude-sonnet-4-20250514",
        provider=LLMProvider.ANTHROPIC,
        name="Claude Sonnet 4",
        description="Latest Claude model, excellent for complex analysis",
        max_tokens=8192,
        is_recommended=True,
    ),
    "claude-3-5-sonnet-20241022": LLMModel(
        id="claude-3-5-sonnet-20241022",
        provider=LLMProvider.ANTHROPIC,
        name="Claude 3.5 Sonnet",
        description="Best balance of intelligence and speed",
        max_tokens=8192,
    ),
    "claude-3-5-haiku-20241022": LLMModel(
        id="claude-3-5-haiku-20241022",
        provider=LLMProvider.ANTHROPIC,
        name="Claude 3.5 Haiku",
        description="Fastest Claude model, great for quick decisions",
        max_tokens=8192,
    ),
    "claude-3-opus-20240229": LLMModel(
        id="claude-3-opus-20240229",
        provider=LLMProvider.ANTHROPIC,
        name="Claude 3 Opus",
        description="Most powerful Claude model for deep analysis",
        max_tokens=4096,
    ),
}

GOOGLE_MODELS = {
    "gemini-2.0-flash": LLMModel(
        id="gemini-2.0-flash",
        provider=LLMProvider.GOOGLE,
        name="Gemini 2.0 Flash",
        description="Latest Gemini with multimodal capabilities",
        max_tokens=8192,
        is_recommended=True,
    ),
    "gemini-1.5-pro": LLMModel(
        id="gemini-1.5-pro",
        provider=LLMProvider.GOOGLE,
        name="Gemini 1.5 Pro",
        description="High capability with long context window",
        max_tokens=8192,
    ),
    "gemini-1.5-flash": LLMModel(
        id="gemini-1.5-flash",
        provider=LLMProvider.GOOGLE,
        name="Gemini 1.5 Flash",
        description="Fast and efficient for quick responses",
        max_tokens=8192,
    ),
}

XAI_MODELS = {
    "grok-3": LLMModel(
        id="grok-3",
        provider=LLMProvider.XAI,
        name="Grok 3",
        description="Latest Grok model with advanced reasoning",
        max_tokens=131072,
        is_recommended=True,
    ),
    "grok-3-fast": LLMModel(
        id="grok-3-fast",
        provider=LLMProvider.XAI,
        name="Grok 3 Fast",
        description="Optimized for speed while maintaining quality",
        max_tokens=131072,
    ),
    "grok-2": LLMModel(
        id="grok-2",
        provider=LLMProvider.XAI,
        name="Grok 2",
        description="Powerful model with real-time knowledge",
        max_tokens=131072,
    ),
    "grok-2-mini": LLMModel(
        id="grok-2-mini",
        provider=LLMProvider.XAI,
        name="Grok 2 Mini",
        description="Compact and fast version of Grok 2",
        max_tokens=131072,
    ),
}

AVAILABLE_MODELS: dict[str, LLMModel] = {
    **OPENAI_MODELS,
    **ANTHROPIC_MODELS,
    **GOOGLE_MODELS,
    **XAI_MODELS,
}

DEFAULT_MODELS = {
    LLMProvider.OPENAI: "gpt-4o-mini",
    LLMProvider.ANTHROPIC: "claude-sonnet-4-20250514",
    LLMProvider.GOOGLE: "gemini-2.0-flash",
    LLMProvider.XAI: "grok-3",
}

RECOMMENDED_MODELS = [
    model_id for model_id, model in AVAILABLE_MODELS.items() if model.is_recommended
]


def get_provider_for_model(model_id: str) -> LLMProvider:
    if model_id in AVAILABLE_MODELS:
        return AVAILABLE_MODELS[model_id].provider

    model_lower = model_id.lower()
    if "gpt" in model_lower or "o1" in model_lower:
        return LLMProvider.OPENAI
    elif "claude" in model_lower:
        return LLMProvider.ANTHROPIC
    elif "gemini" in model_lower:
        return LLMProvider.GOOGLE
    elif "grok" in model_lower:
        return LLMProvider.XAI
    return LLMProvider.OPENAI


def get_models_by_provider(provider: LLMProvider) -> dict[str, LLMModel]:
    return {
        model_id: model
        for model_id, model in AVAILABLE_MODELS.items()
        if model.provider == provider
    }


def get_model_info(model_id: str) -> LLMModel | None:
    return AVAILABLE_MODELS.get(model_id)
