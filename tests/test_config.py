import pytest
from web_app.config import Settings, get_settings, reset_settings_cache
from pydantic_settings import BaseSettings
from pydantic import ValidationError
import os


@pytest.fixture(autouse=True)
def clear_settings_cache():
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
    # Clear all required env vars and bypass .env file loading
    for var in ["DATABASE_URL", "APP_ENV", "LOG_LEVEL", "MODEL_PATH", "API_SECRET_KEY"]:
        monkeypatch.delenv(var, raising=False)

    # Directly instantiate Settings with env_file=False to bypass .env file completely
    # Using env_file=False (not None) ensures Pydantic doesn't load from any .env file
    # This ensures we only test environment variables, not .env file values
    with pytest.raises(ValidationError):
        Settings(env_file=False)
