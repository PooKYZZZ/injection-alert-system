from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    app_env: str = "development"
    log_level: str = "INFO"
    model_path: str
    api_secret_key: str
    groq_api_key: str | None = None
    allowed_origins: list[str] = ["http://localhost:3000"]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache():
    """Clear the settings cache. Useful for testing."""
    get_settings.cache_clear()
