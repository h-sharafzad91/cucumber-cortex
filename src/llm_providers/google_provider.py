import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from google.api_core import exceptions as google_exceptions

from .base import BaseLLMProvider, LLMResponse, LLMMessage
from .models import LLMProvider, DEFAULT_MODELS


class GoogleProvider(BaseLLMProvider):
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
            default_model=default_model or DEFAULT_MODELS[LLMProvider.GOOGLE],
            default_temperature=default_temperature,
            default_max_tokens=default_max_tokens,
            min_request_interval=min_request_interval,
            max_retries=max_retries,
        )
        self._configured = False

    @property
    def provider_name(self) -> str:
        return "google"

    def is_available(self) -> bool:
        return bool(self.api_key)

    def _initialize_client(self) -> None:
        if not self.api_key:
            raise ValueError("Google API key is required")

        genai.configure(api_key=self.api_key)
        self._configured = True

    async def _call_api(
        self,
        messages: list[LLMMessage],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        if not self._configured:
            raise RuntimeError("Google client not initialized")

        gemini_model = genai.GenerativeModel(
            model_name=model,
            system_instruction=self._extract_system_prompt(messages),
        )

        contents = self._build_contents(messages)
        generation_config = GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

        try:
            response = await gemini_model.generate_content_async(
                contents=contents,
                generation_config=generation_config,
            )

            content = response.text if response.text else ""
            usage = {}
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = {
                    "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                    "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
                }

            return LLMResponse(
                content=content,
                model=model,
                provider=self.provider_name,
                usage=usage,
                raw_response=response,
            )

        except google_exceptions.ResourceExhausted as e:
            raise Exception(f"Google rate limit exceeded: {e}")
        except google_exceptions.GoogleAPIError as e:
            raise Exception(f"Google API error: {e}")

    def _extract_system_prompt(self, messages: list[LLMMessage]) -> str | None:
        for msg in messages:
            if msg.role == "system":
                return msg.content
        return None

    def _build_contents(self, messages: list[LLMMessage]) -> list[dict]:
        contents = []

        for msg in messages:
            if msg.role == "system":
                continue

            role = "user" if msg.role == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg.content}],
            })

        return contents

    def _get_retry_wait_time(self, attempt: int, error: Exception) -> float:
        if isinstance(error, google_exceptions.ResourceExhausted):
            return (attempt + 1) * 30
        return (attempt + 1) * 5
