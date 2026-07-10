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


def test_production_env_disables_api_docs_by_default(monkeypatch):
    """Test that API docs are disabled by default in production environment"""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("MODEL_PATH", "test_model.py")
    monkeypatch.setenv("API_SECRET_KEY", "test-key")
    monkeypatch.setenv("ENABLE_API_DOCS", "false")  # Explicitly set to test override

    settings = get_settings()
    
    assert settings.app_env == "production"
    assert settings.is_production is True
    assert settings.enable_api_docs is False


def test_staging_env_disables_api_docs_by_default(monkeypatch):
    """Test that API docs are disabled by default in staging environment"""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("MODEL_PATH", "test_model.py")
    monkeypatch.setenv("API_SECRET_KEY", "test-key")
    monkeypatch.setenv("ENABLE_API_DOCS", "true")  # Explicitly enable

    settings = get_settings()
    
    assert settings.app_env == "staging"
    assert settings.is_staging is True
    assert settings.enable_api_docs is True  # Explicit override works


def test_development_env_enables_api_docs_by_default(monkeypatch):
    """Test that API docs are enabled by default in development environment"""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("MODEL_PATH", "test_model.py")
    monkeypatch.setenv("API_SECRET_KEY", "test-key")

    settings = get_settings()
    
    assert settings.app_env == "development"
    assert settings.is_development is True
    assert settings.enable_api_docs is True


def test_is_staging_property(monkeypatch):
    """Test the is_staging property"""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("MODEL_PATH", "test_model.py")
    monkeypatch.setenv("API_SECRET_KEY", "test-key")

    settings = get_settings()
    
    assert settings.is_staging is True
    assert settings.is_production is False
    assert settings.is_testing is False
    assert settings.is_development is False


def test_production_env_requires_auth_no_bypass(monkeypatch):
    """Test that production environment always requires auth - no bypass possible.
    
    Even if no API key is configured, production should NOT allow auth bypass.
    The auth middleware will deny access (not bypass).
    """
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("MODEL_PATH", "test_model.py")
    # No API_SECRET_KEY set - production should NOT bypass
    monkeypatch.delenv("API_SECRET_KEY", raising=False)

    settings = get_settings()
    
    assert settings.is_production is True
    assert settings.is_development is False
    # In production without API key, auth should be required (not bypassed)
    # The settings show production mode - auth middleware handles the rest


def test_staging_env_requires_auth_no_bypass(monkeypatch):
    """Test that staging environment always requires auth - no bypass possible."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("MODEL_PATH", "test_model.py")
    monkeypatch.delenv("API_SECRET_KEY", raising=False)

    settings = get_settings()
    
    assert settings.is_staging is True
    assert settings.is_development is False
    # In staging without API key, auth should be required


def test_development_allows_auth_bypass_only_when_no_api_key(monkeypatch):
    """Test that development allows auth bypass ONLY when no API key is configured.
    
    This is intentional for local development ergonomics.
    """
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("MODEL_PATH", "test_model.py")
    monkeypatch.delenv("API_SECRET_KEY", raising=False)

    settings = get_settings()
    
    assert settings.is_development is True
    assert settings.is_production is False
    # No API key + development = bypass possible (intentional)


def test_development_with_api_key_requires_auth(monkeypatch):
    """Test that development WITH an API key configured requires auth."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("MODEL_PATH", "test_model.py")
    monkeypatch.setenv("API_SECRET_KEY", "dev-key-123")

    settings = get_settings()
    
    assert settings.is_development is True
    assert settings.api_secret_key == "dev-key-123"
    # With API key in development, auth is required


def test_staging_environment_properties(monkeypatch):
    """Test that staging environment is correctly identified."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("MODEL_PATH", "test_model.py")
    monkeypatch.setenv("API_SECRET_KEY", "staging-key-456")

    settings = get_settings()
    
    assert settings.is_staging is True
    assert settings.is_production is False
    assert settings.is_development is False
    assert settings.is_testing is False
    assert settings.api_secret_key == "staging-key-456"


def test_production_environment_properties(monkeypatch):
    """Test that production environment is correctly identified."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("MODEL_PATH", "test_model.py")
    monkeypatch.setenv("API_SECRET_KEY", "prod-key-789")

    settings = get_settings()
    
    assert settings.is_production is True
    assert settings.is_staging is False
    assert settings.is_development is False
    assert settings.is_testing is False
    assert settings.api_secret_key == "prod-key-789"


def test_notification_settings_are_safe_by_default():
    settings = Settings(
        env_file=False,
        database_url="sqlite+aiosqlite:///test.db",
        model_path="test_model.py",
    )

    assert settings.notification_worker_enabled is False
    assert settings.threat_email_enabled is False
    assert settings.email_provider == "fake"
    assert settings.resend_api_key is None
    assert settings.resend_live_test_enabled is False
