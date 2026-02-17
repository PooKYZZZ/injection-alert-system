from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    app_env: str = "development"
    log_level: str = "INFO"
    model_path: str
    api_secret_key: str

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache():
    """Clear the settings cache. Useful for testing."""
    get_settings.cache_clear()
