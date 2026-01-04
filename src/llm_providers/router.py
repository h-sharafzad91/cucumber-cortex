from datetime import datetime
from typing import Any

from .base import LLMResponse
from .factory import LLMProviderFactory
from .models import (
    LLMProvider,
    AVAILABLE_MODELS,
    get_provider_for_model,
    get_model_info,
)


class LLMRouter:
    def __init__(
        self,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        google_api_key: str | None = None,
        xai_api_key: str | None = None,
        default_model: str = "gpt-4o-mini",
        default_temperature: float = 0.0,
        default_max_tokens: int = 500,
    ):
        self._factory = LLMProviderFactory(
            openai_api_key=openai_api_key,
            anthropic_api_key=anthropic_api_key,
            google_api_key=google_api_key,
            xai_api_key=xai_api_key,
            default_temperature=default_temperature,
            default_max_tokens=default_max_tokens,
        )
        self._default_model = default_model
        self._default_temperature = default_temperature
        self._default_max_tokens = default_max_tokens

    def _log_token_usage(self, response: LLMResponse, model: str) -> None:
        usage = response.usage
        if usage:
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", 0)
            print(f"[{datetime.now().isoformat()}] [LLM] {response.provider.upper()} | {model} | in:{input_tokens} out:{output_tokens} total:{total_tokens} | {response.latency_ms:.0f}ms")

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
    ) -> str:
        selected_model = model or self._default_model
        provider = self._factory.get_provider_for_model(selected_model)

        response = await provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=selected_model,
        )

        self._log_token_usage(response, selected_model)
        return response.content

    async def generate_with_config(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        selected_model = model or self._default_model
        provider = self._factory.get_provider_for_model(selected_model)

        response = await provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=selected_model,
            temperature=temperature if temperature is not None else self._default_temperature,
            max_tokens=max_tokens or self._default_max_tokens,
        )

        self._log_token_usage(response, selected_model)
        return response.content

    async def generate_with_response(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        selected_model = model or self._default_model
        provider = self._factory.get_provider_for_model(selected_model)

        response = await provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=selected_model,
            temperature=temperature if temperature is not None else self._default_temperature,
            max_tokens=max_tokens or self._default_max_tokens,
        )

        self._log_token_usage(response, selected_model)
        return response

    def is_model_available(self, model: str) -> bool:
        provider_type = get_provider_for_model(model)
        return self._factory.is_provider_available(provider_type)

    def get_available_models(self) -> dict[str, Any]:
        available_providers = self._factory.get_available_providers()
        return {
            model_id: model
            for model_id, model in AVAILABLE_MODELS.items()
            if model.provider in available_providers
        }

    def get_available_providers(self) -> list[LLMProvider]:
        return self._factory.get_available_providers()

    def get_model_info(self, model: str) -> dict | None:
        info = get_model_info(model)
        if info:
            return {
                "id": info.id,
                "provider": info.provider.value,
                "name": info.name,
                "description": info.description,
                "max_tokens": info.max_tokens,
                "is_recommended": info.is_recommended,
            }
        return None


def create_router_from_settings() -> LLMRouter:
    try:
        from ..config import settings

        return LLMRouter(
            openai_api_key=getattr(settings, "openai_api_key", None),
            anthropic_api_key=getattr(settings, "anthropic_api_key", None),
            google_api_key=getattr(settings, "google_api_key", None),
            xai_api_key=getattr(settings, "xai_api_key", None),
            default_model=getattr(settings, "default_llm_model", "gpt-4o-mini"),
            default_temperature=getattr(settings, "openai_temperature", 0.0),
            default_max_tokens=getattr(settings, "openai_max_tokens", 500),
        )
    except Exception:
        return LLMRouter()


_llm_router: LLMRouter | None = None


def get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = create_router_from_settings()
    return _llm_router


class _LLMRouterProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_llm_router(), name)


llm_router = _LLMRouterProxy()
