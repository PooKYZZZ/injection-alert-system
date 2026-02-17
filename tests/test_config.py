import pytest
from web_app.config import Settings, get_settings, reset_settings_cache
from pydantic_settings import BaseSettings
from pydantic import ValidationError
import os


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear settings cache before each test."""
    reset_settings_cache()
    yield


def test_settings_loads_from_env(monkeypatch):
    """Test that settings correctly loads from environment variables"""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MODEL_PATH", "test_model.py")
    monkeypatch.setenv("API_SECRET_KEY", "test-secret-key")

    settings = get_settings()

    assert settings.database_url == "postgresql://test:test@localhost:5432/test_db"
    assert settings.app_env == "testing"
    assert settings.log_level == "DEBUG"


def test_settings_validation_error_on_missing_env(monkeypatch):
    """Test that settings raises error when required env vars are missing"""
    # Clear all required env vars
    for var in ["DATABASE_URL", "APP_ENV", "LOG_LEVEL", "MODEL_PATH", "API_SECRET_KEY"]:
        monkeypatch.delenv(var, raising=False)

    with pytest.raises(ValidationError):
        get_settings()
