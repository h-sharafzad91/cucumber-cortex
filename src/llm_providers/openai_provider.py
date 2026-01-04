from openai import AsyncOpenAI, RateLimitError, APIError, APIConnectionError

from .base import BaseLLMProvider, LLMResponse, LLMMessage
from .models import LLMProvider, DEFAULT_MODELS


class OpenAIProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        default_temperature: float = 0.0,
        default_max_tokens: int = 500,
        min_request_interval: float = 0.5,
        max_retries: int = 3,
        organization: str | None = None,
    ):
        super().__init__(
            api_key=api_key,
            default_model=default_model or DEFAULT_MODELS[LLMProvider.OPENAI],
            default_temperature=default_temperature,
            default_max_tokens=default_max_tokens,
            min_request_interval=min_request_interval,
            max_retries=max_retries,
        )
        self.organization = organization
        self._client: AsyncOpenAI | None = None

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _initialize_client(self) -> None:
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self._client = AsyncOpenAI(
            api_key=self.api_key,
            organization=self.organization,
        )

    async def _call_api(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        if self._client is None:
            raise RuntimeError("OpenAI client not initialized")

        openai_messages = [
            {"role": msg.role, "content": msg.content} for msg in messages
        ]

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            content = response.choices[0].message.content or ""

            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                usage=usage,
                raw_response=response,
            )

        except RateLimitError as e:
            raise Exception(f"OpenAI rate limit exceeded: {e}")
        except APIConnectionError as e:
            raise Exception(f"OpenAI connection error: {e}")
        except APIError as e:
            raise Exception(f"OpenAI API error: {e}")

    def _get_retry_wait_time(self, attempt: int, error: Exception) -> float:
        if isinstance(error, RateLimitError):
            return (attempt + 1) * 25
        return (attempt + 1) * 5
