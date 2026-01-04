from anthropic import AsyncAnthropic, RateLimitError, APIError, APIConnectionError

from .base import BaseLLMProvider, LLMResponse, LLMMessage
from .models import LLMProvider, DEFAULT_MODELS


class AnthropicProvider(BaseLLMProvider):
    def __init__(
        self,
        api_key: str | None = None,
        default_model: str | None = None,
        default_temperature: float = 0.0,
        default_max_tokens: int = 500,
        min_request_interval: float = 0.5,
        max_retries: int = 3,
    ):
        super().__init__(
            api_key=api_key,
            default_model=default_model or DEFAULT_MODELS[LLMProvider.ANTHROPIC],
            default_temperature=default_temperature,
            default_max_tokens=default_max_tokens,
            min_request_interval=min_request_interval,
            max_retries=max_retries,
        )
        self._client: AsyncAnthropic | None = None

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _initialize_client(self) -> None:
        if not self.api_key:
            raise ValueError("Anthropic API key is required")

        self._client = AsyncAnthropic(api_key=self.api_key)

    async def _call_api(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        if self._client is None:
            raise RuntimeError("Anthropic client not initialized")

        system_prompt = ""
        user_messages = []

        for msg in messages:
            if msg.role == "system":
                system_prompt = msg.content
            else:
                user_messages.append({"role": msg.role, "content": msg.content})

        if not user_messages:
            user_messages = [{"role": "user", "content": ""}]

        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else None,
                messages=user_messages,
            )

            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }

            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                usage=usage,
                raw_response=response,
            )

        except RateLimitError as e:
            raise Exception(f"Anthropic rate limit exceeded: {e}")
        except APIConnectionError as e:
            raise Exception(f"Anthropic connection error: {e}")
        except APIError as e:
            raise Exception(f"Anthropic API error: {e}")

    def _get_retry_wait_time(self, attempt: int, error: Exception) -> float:
        if isinstance(error, RateLimitError):
            return (attempt + 1) * 20
        return (attempt + 1) * 5
