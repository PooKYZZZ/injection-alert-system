from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def __init__(self, **values):
        legacy_env_file = values.pop("env_file", None)
        if legacy_env_file is False and "_env_file" not in values:
            values["_env_file"] = None
        super().__init__(**values)

    database_url: str
    app_env: str = "development"
    log_level: str = "INFO"
    model_path: str
    model_registry_path: str = ""
    api_secret_key: str
    groq_api_key: str | None = None
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    is_development: bool = False
    confidence_low_threshold: float = 0.50
    confidence_high_threshold: float = 0.80
    stale_processing_timeout_seconds: int = 30
    max_seq_len: int = 128
    # dev-time default — source from artifact metadata in production
    temperature: float = 0.596868
    # dev-time default — source from artifact metadata in production
    label_names: list[str] = Field(
        default_factory=lambda: [
            "Code Injection",
            "Normal",
            "Other Attacks",
            "SQL Injection",
        ]
    )
    # dev-time default — source from artifact metadata in production
    model_version: str = "distilbert_v3_907k_cleaned_20260312_133755"

    @model_validator(mode="after")
    def apply_environment_defaults(self) -> "Settings":
        if "is_development" not in self.model_fields_set:
            self.is_development = self.app_env == "development"
        return self

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
