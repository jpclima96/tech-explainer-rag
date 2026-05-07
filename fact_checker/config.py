from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    anthropic_api_key: str = "placeholder"
    tavily_api_key: str = "placeholder"
    default_model: str = "claude-opus-4-7"
    max_claims: int = 20
    results_per_claim: int = 5
    retriever_timeout_seconds: float = 10.0
    concurrency_limit: int = 5


settings = Settings()
