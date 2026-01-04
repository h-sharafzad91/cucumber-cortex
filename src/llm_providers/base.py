from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
import asyncio
import time


@dataclass
class LLMResponse:
    content: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)
    raw_response: Any = None
    latency_ms: float = 0.0


@dataclass
class LLMMessage:
    role: str
    content: str


class BaseLLMProvider(ABC):
    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        default_temperature: float = 0.0,
        default_max_tokens: int = 500,
        min_request_interval: float = 1.0,
        max_retries: int = 3,
    ):
        self.api_key = api_key
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self.min_request_interval = min_request_interval
        self.max_retries = max_retries
        self._last_request_time: float = 0.0
        self._initialized = False

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @abstractmethod
    async def _call_api(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def _initialize_client(self) -> None:
        pass

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self._initialize_client()
            self._initialized = True

    async def _wait_for_rate_limit(self) -> None:
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.min_request_interval:
            wait_time = self.min_request_interval - elapsed
            await asyncio.sleep(wait_time)
        self._last_request_time = time.time()

    async def _call_with_retry(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        self._ensure_initialized()

        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                await self._wait_for_rate_limit()

                start_time = time.time()
                response = await self._call_api(messages, model, temperature, max_tokens)
                response.latency_ms = (time.time() - start_time) * 1000

                return response

            except Exception as e:
                last_error = e
                wait_time = self._get_retry_wait_time(attempt, e)

                if attempt < self.max_retries - 1:
                    await asyncio.sleep(wait_time)
                    continue

        raise last_error or Exception("Unknown error during LLM call")

    def _get_retry_wait_time(self, attempt: int, error: Exception) -> float:
        error_str = str(error).lower()
        if "rate" in error_str or "limit" in error_str or "429" in error_str:
            return (attempt + 1) * 20
        return (attempt + 1) * 5

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if not self.is_available():
            raise ValueError(f"Provider {self.provider_name} is not configured")

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        return await self._call_with_retry(
            messages=messages,
            model=model or self.default_model or "",
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=max_tokens or self.default_max_tokens,
        )

    async def generate_raw(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        if not self.is_available():
            raise ValueError(f"Provider {self.provider_name} is not configured")

        llm_messages = [
            LLMMessage(role=m["role"], content=m["content"]) for m in messages
        ]

        return await self._call_with_retry(
            messages=llm_messages,
            model=model or self.default_model or "",
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=max_tokens or self.default_max_tokens,
        )
