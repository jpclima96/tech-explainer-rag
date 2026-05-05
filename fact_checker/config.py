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
    default_model: str = "claude-sonnet-4-6"
    max_claims_per_request: int = 20
    retriever_results_per_claim: int = 5
    retriever_timeout_seconds: float = 10.0
    log_level: str = "INFO"


settings = Settings()
