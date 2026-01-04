from typing import TYPE_CHECKING

from .base import BaseLLMProvider
from .models import LLMProvider, get_provider_for_model

if TYPE_CHECKING:
    from .openai_provider import OpenAIProvider
    from .anthropic_provider import AnthropicProvider
    from .google_provider import GoogleProvider
    from .xai_provider import XAIProvider


class LLMProviderFactory:
    def __init__(
        self,
        openai_api_key: str | None = None,
        anthropic_api_key: str | None = None,
        google_api_key: str | None = None,
        xai_api_key: str | None = None,
        default_temperature: float = 0.0,
        default_max_tokens: int = 500,
    ):
        self._openai_api_key = openai_api_key
        self._anthropic_api_key = anthropic_api_key
        self._google_api_key = google_api_key
        self._xai_api_key = xai_api_key
        self._default_temperature = default_temperature
        self._default_max_tokens = default_max_tokens

        self._providers: dict[LLMProvider, BaseLLMProvider] = {}

    def get_provider(self, provider: LLMProvider) -> BaseLLMProvider:
        if provider in self._providers:
            return self._providers[provider]

        instance = self._create_provider(provider)
        self._providers[provider] = instance
        return instance

    def get_provider_for_model(self, model: str) -> BaseLLMProvider:
        provider_type = get_provider_for_model(model)
        return self.get_provider(provider_type)

    def _create_provider(self, provider: LLMProvider) -> BaseLLMProvider:
        if provider == LLMProvider.OPENAI:
            return self._create_openai_provider()
        elif provider == LLMProvider.ANTHROPIC:
            return self._create_anthropic_provider()
        elif provider == LLMProvider.GOOGLE:
            return self._create_google_provider()
        elif provider == LLMProvider.XAI:
            return self._create_xai_provider()
        else:
            raise ValueError(f"Unknown provider: {provider}")

    def _create_openai_provider(self) -> "OpenAIProvider":
        from .openai_provider import OpenAIProvider

        if not self._openai_api_key:
            raise ValueError("OpenAI API key not configured")

        return OpenAIProvider(
            api_key=self._openai_api_key,
            default_temperature=self._default_temperature,
            default_max_tokens=self._default_max_tokens,
        )

    def _create_anthropic_provider(self) -> "AnthropicProvider":
        from .anthropic_provider import AnthropicProvider

        if not self._anthropic_api_key:
            raise ValueError("Anthropic API key not configured")

        return AnthropicProvider(
            api_key=self._anthropic_api_key,
            default_temperature=self._default_temperature,
            default_max_tokens=self._default_max_tokens,
        )

    def _create_google_provider(self) -> "GoogleProvider":
        from .google_provider import GoogleProvider

        if not self._google_api_key:
            raise ValueError("Google API key not configured")

        return GoogleProvider(
            api_key=self._google_api_key,
            default_temperature=self._default_temperature,
            default_max_tokens=self._default_max_tokens,
        )

    def _create_xai_provider(self) -> "XAIProvider":
        from .xai_provider import XAIProvider

        if not self._xai_api_key:
            raise ValueError("xAI API key not configured")

        return XAIProvider(
            api_key=self._xai_api_key,
            default_temperature=self._default_temperature,
            default_max_tokens=self._default_max_tokens,
        )

    def is_provider_available(self, provider: LLMProvider) -> bool:
        api_keys = {
            LLMProvider.OPENAI: self._openai_api_key,
            LLMProvider.ANTHROPIC: self._anthropic_api_key,
            LLMProvider.GOOGLE: self._google_api_key,
            LLMProvider.XAI: self._xai_api_key,
        }
        return bool(api_keys.get(provider))

    def get_available_providers(self) -> list[LLMProvider]:
        return [p for p in LLMProvider if self.is_provider_available(p)]

    def clear_cache(self) -> None:
        self._providers.clear()
