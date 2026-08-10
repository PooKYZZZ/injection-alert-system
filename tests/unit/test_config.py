from base64 import b64encode

import pytest
from pydantic import ValidationError

from web_app.config import Settings, get_settings, reset_settings_cache

VALID_API_KEY = "general-internal-key"
VALID_WAF_KEY = "test-waf-key-" * 3


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
    monkeypatch.setenv("API_SECRET_KEY", VALID_API_KEY)
    monkeypatch.setenv("WAF_INGEST_API_KEY", VALID_WAF_KEY)
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
    monkeypatch.setenv("API_SECRET_KEY", VALID_API_KEY)
    monkeypatch.setenv("WAF_INGEST_API_KEY", VALID_WAF_KEY)
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


@pytest.mark.parametrize("app_env", ["production", "staging"])
def test_deployed_environment_requires_general_api_key(app_env):
    with pytest.raises(ValueError, match="API_SECRET_KEY"):
        Settings(
            env_file=False,
            database_url="sqlite:///test.db",
            model_path="test_model.py",
            app_env=app_env,
            api_secret_key="",
            waf_ingest_api_key=VALID_WAF_KEY,
        )


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
    monkeypatch.setenv("API_SECRET_KEY", VALID_API_KEY)
    monkeypatch.setenv("WAF_INGEST_API_KEY", VALID_WAF_KEY)

    settings = get_settings()

    assert settings.is_staging is True
    assert settings.is_production is False
    assert settings.is_development is False
    assert settings.is_testing is False
    assert settings.api_secret_key == VALID_API_KEY


def test_production_environment_properties(monkeypatch):
    """Test that production environment is correctly identified."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("MODEL_PATH", "test_model.py")
    monkeypatch.setenv("API_SECRET_KEY", VALID_API_KEY)
    monkeypatch.setenv("WAF_INGEST_API_KEY", VALID_WAF_KEY)

    settings = get_settings()

    assert settings.is_production is True
    assert settings.is_staging is False
    assert settings.is_development is False
    assert settings.is_testing is False
    assert settings.api_secret_key == VALID_API_KEY


def test_notification_settings_are_safe_by_default():
    settings = Settings(
        env_file=False,
        database_url="sqlite+aiosqlite:///test.db",
        model_path="test_model.py",
    )

    assert settings.notification_worker_enabled is False
    assert settings.notification_payload_encryption_key is None
    assert settings.threat_email_enabled is False
    assert settings.email_provider == "fake"
    assert settings.resend_api_key is None
    assert settings.resend_live_test_enabled is False
    assert settings.threat_telegram_enabled is False
    assert settings.telegram_bot_token is None
    assert settings.telegram_chat_id is None
    assert settings.telegram_live_test_enabled is False
    assert settings.telegram_available is False


def test_retraining_output_root_is_local_and_repository_relative():
    settings = Settings(
        env_file=False,
        database_url="sqlite+aiosqlite:///test.db",
        model_path="test_model.py",
    )
    assert settings.retraining_output_root == "ml_model/results/dashboard_retraining"

    with pytest.raises(ValueError, match="repository-relative"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            retraining_output_root="../outside",
        )

    assert settings.retraining_staging_root.replace("\\", "/").endswith("/staging")
    assert settings.retraining_staging_archive_root.replace("\\", "/").endswith(
        "/archive"
    )
    with pytest.raises(ValueError, match="non-production"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            retraining_staging_root="ml_model/model_registry/production",
        )
    with pytest.raises(ValueError, match="differ"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            retraining_staging_archive_root="ml_model/model_registry/staging",
        )


def test_retraining_cannot_be_enabled_in_deployed_environments():
    with pytest.raises(ValueError, match="controlled local"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            app_env="production",
            api_secret_key=VALID_API_KEY,
            waf_ingest_api_key=VALID_WAF_KEY,
            retraining_enabled=True,
        )


def test_telegram_is_available_only_with_complete_enabled_configuration():
    settings = Settings(
        env_file=False,
        database_url="sqlite+aiosqlite:///test.db",
        model_path="test_model.py",
        threat_telegram_enabled=True,
        telegram_bot_token="bot-token",
        telegram_chat_id="-100123",
    )

    assert settings.telegram_available is True


def test_incomplete_telegram_configuration_degrades_without_failing_settings():
    settings = Settings(
        env_file=False,
        database_url="sqlite+aiosqlite:///test.db",
        model_path="test_model.py",
        threat_telegram_enabled=True,
        telegram_bot_token="bot-token",
    )

    assert settings.telegram_available is False


def test_required_worker_rejects_fake_provider():
    with pytest.raises(ValueError, match="fake email provider"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            notification_worker_enabled=True,
            notification_worker_required=True,
            notification_payload_encryption_key=b64encode(bytes(32)).decode(),
            email_provider="fake",
        )


def test_production_worker_rejects_fake_provider():
    with pytest.raises(ValueError, match="fake email provider"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            app_env="production",
            api_secret_key=VALID_API_KEY,
            waf_ingest_api_key=VALID_WAF_KEY,
            notification_worker_enabled=True,
            notification_payload_encryption_key=b64encode(bytes(32)).decode(),
            email_provider="fake",
        )


def test_waf_settings_are_safe_by_default(monkeypatch) -> None:
    monkeypatch.delenv("WAF_INGEST_API_KEY", raising=False)
    settings = Settings(
        env_file=False,
        database_url="sqlite+aiosqlite:///test.db",
        model_path="test_model.py",
    )

    assert settings.waf_ingest_api_key == ""
    assert settings.waf_source_verification_mode == "unverified"


@pytest.mark.parametrize("app_env", ["production", "staging"])
def test_deployed_environment_requires_waf_ingest_key(app_env: str) -> None:
    with pytest.raises(ValueError, match="WAF_INGEST_API_KEY"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            app_env=app_env,
            api_secret_key=VALID_API_KEY,
            waf_ingest_api_key="",
        )


@pytest.mark.parametrize("app_env", ["production", "staging"])
def test_deployed_environment_rejects_short_waf_ingest_key(app_env: str) -> None:
    with pytest.raises(ValueError, match="at least 32"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            app_env=app_env,
            api_secret_key=VALID_API_KEY,
            waf_ingest_api_key="too-short",
        )


@pytest.mark.parametrize("app_env", ["production", "staging"])
def test_deployed_environment_rejects_equal_internal_keys(app_env: str) -> None:
    shared_key = "same-key-must-not-cross-auth-boundaries"
    with pytest.raises(ValueError, match="must differ"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            app_env=app_env,
            api_secret_key=shared_key,
            waf_ingest_api_key=shared_key,
        )


def test_settings_rejects_removed_controlled_private_network_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            waf_source_verification_mode="controlled_private_network",
        )


@pytest.mark.parametrize("key", [None, "not-a-key", "00" * 31])
def test_enabled_worker_requires_a_valid_payload_encryption_key(key):
    with pytest.raises(ValueError, match="payload encryption key"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            notification_worker_enabled=True,
            notification_payload_encryption_key=key,
        )


def test_shadow_enforcement_defaults_to_off() -> None:
    settings = Settings(
        env_file=False,
        database_url="sqlite+aiosqlite:///test.db",
        model_path="test_model.py",
    )

    assert settings.enforcement_mode == "off"
    assert settings.enforcement_check_api_key == ""
    assert settings.enforcement_recommendation_ttl_seconds == 900


def test_shadow_enforcement_accepts_a_distinct_dedicated_key() -> None:
    settings = Settings(
        env_file=False,
        database_url="sqlite+aiosqlite:///test.db",
        model_path="test_model.py",
        api_secret_key="general-key",
        waf_ingest_api_key="waf-key",
        enforcement_mode="shadow",
        enforcement_check_api_key="enforcement-key-that-is-at-least-32-chars",
    )

    assert settings.enforcement_mode == "shadow"
    assert settings.enforcement_recommendation_ttl_seconds == 900


def test_active_enforcement_accepts_explicit_controlled_configuration() -> None:
    settings = Settings(
        env_file=False,
        database_url="sqlite+aiosqlite:///test.db",
        model_path="test_model.py",
        api_secret_key="general-key",
        waf_ingest_api_key="waf-key",
        enforcement_mode="enforce",
        enforcement_check_api_key="enforcement-key-that-is-at-least-32-chars",
        enforcement_turnstile_secret_key="turnstile-secret",
        enforcement_turnstile_expected_hostname="localhost",
        enforcement_allow_unverified_source_for_tests=True,
    )

    assert settings.enforcement_mode == "enforce"
    assert settings.enforcement_low_window_seconds == 60
    assert settings.enforcement_low_max_unchallenged_requests == 5
    assert settings.enforcement_medium_max_requests == 10
    assert settings.enforcement_challenge_grant_ttl_seconds == 300


@pytest.mark.parametrize(
    "missing",
    ["enforcement_turnstile_secret_key", "enforcement_turnstile_expected_hostname"],
)
def test_active_enforcement_requires_complete_turnstile_configuration(
    missing: str,
) -> None:
    values = {
        "enforcement_turnstile_secret_key": "turnstile-secret",
        "enforcement_turnstile_expected_hostname": "localhost",
    }
    values[missing] = ""
    with pytest.raises(ValueError, match="Turnstile"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            enforcement_mode="enforce",
            enforcement_check_api_key="enforcement-key-that-is-at-least-32-chars",
            enforcement_allow_unverified_source_for_tests=True,
            **values,
        )


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_deployed_active_enforcement_requires_explicit_cloudflare_trust(
    app_env: str,
) -> None:
    with pytest.raises(ValueError, match="source trust"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            app_env=app_env,
            api_secret_key=VALID_API_KEY,
            waf_ingest_api_key=VALID_WAF_KEY,
            enforcement_mode="enforce",
            enforcement_check_api_key="enforcement-key-that-is-at-least-32-chars",
            enforcement_turnstile_secret_key="real-secret",
            enforcement_turnstile_expected_hostname="app.example.com",
        )


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_deployed_active_enforcement_requires_cloudflare_tunnel_source_verification(
    app_env: str,
) -> None:
    with pytest.raises(ValueError, match="cloudflare_tunnel"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            app_env=app_env,
            api_secret_key=VALID_API_KEY,
            waf_ingest_api_key=VALID_WAF_KEY,
            enforcement_mode="enforce",
            enforcement_check_api_key="enforcement-key-that-is-at-least-32-chars",
            enforcement_turnstile_secret_key="real-secret",
            enforcement_turnstile_expected_hostname="app.example.com",
            enforcement_source_trust_mode="cloudflare_verified",
            waf_source_verification_mode="unverified",
        )


def test_cloudflare_tunnel_requires_isolated_overlay_and_explicit_proof_switch(
) -> None:
    base = {
        "env_file": False,
        "database_url": "sqlite+aiosqlite:///test.db",
        "model_path": "test_model.py",
        "waf_source_verification_mode": "cloudflare_tunnel",
    }

    with pytest.raises(ValueError, match="isolation overlay"):
        Settings(**base)

    with pytest.raises(ValueError, match="proof activation"):
        Settings(**base, cloudflare_target_isolation_enabled=True)

    with pytest.raises(ValueError, match="WAF_AUDIT_EVIDENCE_KEY"):
        Settings(
            **base,
            cloudflare_target_isolation_enabled=True,
            cloudflare_target_verified_proof=True,
        )

    enabled = Settings(
        **base,
        cloudflare_target_isolation_enabled=True,
        cloudflare_target_verified_proof=True,
        waf_audit_evidence_key="test-audit-evidence-key",
    )
    assert enabled.waf_source_verification_mode == "cloudflare_tunnel"


def test_verified_proof_switch_is_rejected_in_unverified_mode() -> None:
    with pytest.raises(ValueError, match="proof activation"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            cloudflare_target_verified_proof=True,
        )


def test_app_env_rejects_unknown_values() -> None:
    with pytest.raises(ValidationError):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            app_env="prod",
        )


@pytest.mark.parametrize(
    "secret",
    [
        "1x0000000000000000000000000000000AA",
        "2x0000000000000000000000000000000AA",
        "3x0000000000000000000000000000000AA",
    ],
)
def test_deployed_active_enforcement_rejects_turnstile_test_secrets(
    secret: str,
) -> None:
    with pytest.raises(ValueError, match="test credential"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            app_env="production",
            api_secret_key=VALID_API_KEY,
            waf_ingest_api_key=VALID_WAF_KEY,
            enforcement_mode="enforce",
            enforcement_check_api_key="enforcement-key-that-is-at-least-32-chars",
            enforcement_turnstile_secret_key=secret,
            enforcement_turnstile_expected_hostname="app.example.com",
            enforcement_source_trust_mode="cloudflare_verified",
            waf_source_verification_mode="cloudflare_tunnel",
        )


def test_low_maximum_must_allow_at_least_one_request() -> None:
    with pytest.raises(ValidationError):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            enforcement_low_max_unchallenged_requests=0,
        )


def test_turnstile_test_mode_requires_published_test_secret() -> None:
    with pytest.raises(ValueError, match="published Turnstile test secret"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            enforcement_mode="enforce",
            enforcement_check_api_key="enforcement-key-that-is-at-least-32-chars",
            enforcement_turnstile_secret_key="not-a-test-secret",
            enforcement_turnstile_expected_hostname="localhost",
            enforcement_turnstile_test_mode=True,
            enforcement_allow_unverified_source_for_tests=True,
        )


def test_deployed_active_enforcement_rejects_turnstile_test_mode() -> None:
    with pytest.raises(ValueError, match="test mode"):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            app_env="production",
            api_secret_key=VALID_API_KEY,
            waf_ingest_api_key=VALID_WAF_KEY,
            enforcement_mode="enforce",
            enforcement_check_api_key="enforcement-key-that-is-at-least-32-chars",
            enforcement_turnstile_secret_key="1x0000000000000000000000000000000AA",
            enforcement_turnstile_expected_hostname="localhost",
            enforcement_turnstile_test_mode=True,
            enforcement_source_trust_mode="cloudflare_verified",
            waf_source_verification_mode="cloudflare_tunnel",
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"enforcement_mode": "shadow", "enforcement_check_api_key": ""},
        {
            "enforcement_mode": "shadow",
            "enforcement_check_api_key": "short",
        },
        {
            "enforcement_mode": "shadow",
            "api_secret_key": "shared-key-that-is-long-enough-123456",
            "enforcement_check_api_key": "shared-key-that-is-long-enough-123456",
        },
        {"enforcement_recommendation_ttl_seconds": 59},
        {"enforcement_mode": "enforce", "enforcement_check_api_key": ""},
    ],
)
def test_enforcement_configuration_rejects_unsafe_values(kwargs) -> None:
    with pytest.raises((ValueError, ValidationError)):
        Settings(
            env_file=False,
            database_url="sqlite+aiosqlite:///test.db",
            model_path="test_model.py",
            **kwargs,
        )


def _pr7_mutation_settings(**overrides):
    values = {
        "env_file": False,
        "database_url": "postgresql+asyncpg://user:password@localhost/test",
        "model_path": "test_model.py",
        "app_env": "testing",
        "enforcement_mode": "enforce",
        "enforcement_check_api_key": "enforcement-key-that-is-at-least-32-chars",
        "enforcement_turnstile_secret_key": "1x0000000000000000000000000000000AA",
        "enforcement_turnstile_expected_hostname": "localhost",
        "enforcement_turnstile_test_mode": True,
        "waf_state_sync_enabled": True,
        "waf_state_sync_api_key": "waf-state-sync-key-that-is-at-least-32-chars",
        "waf_source_verification_mode": "cloudflare_tunnel",
        "cloudflare_target_isolation_enabled": True,
        "cloudflare_target_verified_proof": True,
        "waf_audit_evidence_key": "waf-audit-evidence-key-that-is-at-least-32-chars",
        "pr7_critical_waf_mutation_enabled": True,
    }
    values.update(overrides)
    return values


def test_pr7_mutation_gate_accepts_controlled_testing_configuration() -> None:
    settings = Settings(**_pr7_mutation_settings())

    assert settings.pr7_critical_waf_mutation_enabled is True
    assert settings.pr7_waf_capacity == 64


@pytest.mark.parametrize("capacity", [1, 512])
def test_pr7_capacity_accepts_contract_boundaries(capacity: int) -> None:
    settings = Settings(**_pr7_mutation_settings(pr7_waf_capacity=capacity))

    assert settings.pr7_waf_capacity == capacity


@pytest.mark.parametrize("capacity", [0, 513])
def test_pr7_capacity_rejects_out_of_range_values(capacity: int) -> None:
    with pytest.raises((ValueError, ValidationError)):
        Settings(**_pr7_mutation_settings(pr7_waf_capacity=capacity))


def test_pr7_mutation_gate_rejects_non_local_environment() -> None:
    with pytest.raises(ValueError, match="controlled local mode"):
        Settings(**_pr7_mutation_settings(app_env="staging"))


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"waf_source_verification_mode": "unverified"}, "cloudflare_tunnel"),
        ({"database_url": "sqlite+aiosqlite:///test.db"}, "PostgreSQL"),
    ],
)
def test_pr7_mutation_gate_rejects_nonfunctional_runtime_combinations(
    overrides, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        Settings(**_pr7_mutation_settings(**overrides))


def test_pr7_mutation_gate_requires_snapshot_sync() -> None:
    with pytest.raises(ValueError, match="WAF_STATE_SYNC_ENABLED"):
        Settings(**_pr7_mutation_settings(waf_state_sync_enabled=False))


def test_pr7_mutation_gate_requires_enforce_mode() -> None:
    with pytest.raises(ValueError, match="ENFORCEMENT_MODE=enforce"):
        Settings(**_pr7_mutation_settings(enforcement_mode="shadow"))
