from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    port: int = 8000

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    google_api_key: str | None = None
    xai_api_key: str | None = None

    default_llm_model: str = "gpt-4o-mini"
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.0
    openai_max_tokens: int = 500

    redis_url: str = "redis://localhost:6379"
    cerebellum_url: str = "http://localhost:3001"
    database_url: str | None = None
    supabase_url: str | None = None
    supabase_anon_key: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
