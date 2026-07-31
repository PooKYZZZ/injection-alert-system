import base64
import re
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TURNSTILE_TEST_SECRETS = {
    "1x0000000000000000000000000000000AA",
    "2x0000000000000000000000000000000AA",
    "3x0000000000000000000000000000000AA",
}


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
    app_env: Literal["development", "testing", "staging", "production"] = (
        "development"
    )
    log_level: str = "INFO"
    model_path: str
    model_registry_path: str = ""
    api_secret_key: str = ""
    waf_ingest_api_key: str = ""
    waf_audit_evidence_key: str = ""
    waf_state_sync_enabled: bool = False
    waf_state_sync_api_key: str = ""
    pr7_critical_waf_mutation_enabled: bool = False
    pr7_waf_capacity: int = Field(default=64, ge=1, le=512)
    waf_source_verification_mode: Literal[
        "unverified",
        "cloudflare_tunnel",
    ] = "unverified"
    cloudflare_target_isolation_enabled: bool = False
    cloudflare_target_verified_proof: bool = False
    enforcement_mode: Literal["off", "shadow", "enforce"] = "off"
    enforcement_check_api_key: str = ""
    enforcement_recommendation_ttl_seconds: int = Field(default=900, ge=60, le=86400)
    enforcement_low_window_seconds: int = Field(default=60, ge=1, le=3600)
    enforcement_medium_window_seconds: int = Field(default=60, ge=1, le=3600)
    enforcement_low_max_unchallenged_requests: int = Field(default=5, ge=1, le=10000)
    enforcement_medium_max_requests: int = Field(default=10, ge=1, le=10000)
    enforcement_challenge_grant_ttl_seconds: int = Field(default=300, ge=1, le=3600)
    enforcement_turnstile_secret_key: str = ""
    enforcement_turnstile_expected_hostname: str = ""
    enforcement_turnstile_timeout_seconds: float = Field(default=3.0, gt=0, le=3)
    enforcement_turnstile_test_mode: bool = False
    enforcement_allow_unverified_source_for_tests: bool = False
    enforcement_source_trust_mode: Literal["unverified", "cloudflare_verified"] = (
        "unverified"
    )
    groq_api_key: str | None = None
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"]
    )
    is_development: bool = False
    enable_api_docs: bool = True
    confidence_low_threshold: float = 0.50
    confidence_high_threshold: float = 0.80
    confidence_critical_threshold: float = 0.90
    stale_processing_timeout_seconds: int = 30
    inference_queue_maxsize: int = Field(default=100, ge=1)
    notification_worker_enabled: bool = False
    notification_worker_poll_seconds: float = Field(default=2.0, gt=0, le=60)
    notification_worker_batch_size: int = Field(default=1, ge=1, le=100)
    notification_worker_required: bool = False
    notification_worker_lease_seconds: int = Field(default=60, ge=5, le=300)
    notification_payload_encryption_key: str | None = None
    email_provider: Literal["fake", "resend"] = "fake"
    resend_api_key: str | None = None
    resend_from_email: str = "onboarding@resend.dev"
    resend_smoke_test_to: str | None = None
    resend_live_test_enabled: bool = False
    threat_email_enabled: bool = False
    threat_email_to: str | None = None
    threat_telegram_enabled: bool = False
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_live_test_enabled: bool = False
    dashboard_base_url: str = "http://localhost:3000"
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
    # Enable HTTP request preprocessing for model input (training-serving consistency)
    enable_http_model_preprocessing: bool = True

    @model_validator(mode="after")
    def apply_environment_defaults(self) -> "Settings":
        if "is_development" not in self.model_fields_set:
            self.is_development = self.app_env == "development"
        # Disable API docs in production and staging unless explicitly enabled.
        if "enable_api_docs" not in self.model_fields_set:
            if self.app_env == "production" or self.app_env == "staging":
                self.enable_api_docs = False
        if not (
            0.0
            <= self.confidence_low_threshold
            < self.confidence_high_threshold
            < self.confidence_critical_threshold
            <= 1.0
        ):
            raise ValueError(
                "confidence thresholds must satisfy 0.0 <= low < high < critical <= 1.0"
            )
        if self.enforcement_mode in {"shadow", "enforce"}:
            key = self.enforcement_check_api_key.strip()
            if not key:
                raise ValueError(
                    "ENFORCEMENT_CHECK_API_KEY is required when enforcement is active"
                )
            if len(key) < 32:
                raise ValueError(
                    "ENFORCEMENT_CHECK_API_KEY must be at least 32 characters"
                )
            if key in {self.api_secret_key, self.waf_ingest_api_key}:
                raise ValueError(
                    "ENFORCEMENT_CHECK_API_KEY must differ from API_SECRET_KEY "
                    "and WAF_INGEST_API_KEY"
                )
        if self.waf_state_sync_enabled:
            if self.app_env not in {"development", "testing"}:
                raise ValueError(
                    "WAF state sync is restricted to controlled local mode"
                )
            if len(self.waf_state_sync_api_key.strip()) < 32:
                raise ValueError(
                    "WAF_STATE_SYNC_API_KEY must be at least 32 characters"
                )
        if self.pr7_critical_waf_mutation_enabled:
            if self.app_env not in {"development", "testing"}:
                raise ValueError(
                    "PR7 CRITICAL mutation is restricted to controlled local mode"
                )
            if not self.waf_state_sync_enabled:
                raise ValueError(
                    "PR7 CRITICAL mutation requires WAF_STATE_SYNC_ENABLED"
                )
            if self.enforcement_mode != "enforce":
                raise ValueError(
                    "PR7 CRITICAL mutation requires ENFORCEMENT_MODE=enforce"
                )
            if self.waf_source_verification_mode != "cloudflare_tunnel":
                raise ValueError(
                    "PR7 CRITICAL mutation requires cloudflare_tunnel "
                    "source verification"
                )
            if not self.database_url.startswith(
                ("postgresql+asyncpg://", "postgresql://")
            ):
                raise ValueError(
                    "PR7 CRITICAL mutation requires a PostgreSQL database"
                )
        if self.enforcement_allow_unverified_source_for_tests and (
            self.is_production or self.is_staging
        ):
            raise ValueError(
                "unverified source bypass is forbidden in staging and production"
            )
        if (
            self.enforcement_mode == "enforce"
            and self.enforcement_challenge_grant_ttl_seconds
            > self.enforcement_recommendation_ttl_seconds
        ):
            raise ValueError("challenge grant TTL cannot exceed recommendation TTL")
        if self.enforcement_mode == "enforce":
            if not self.enforcement_turnstile_secret_key.strip():
                raise ValueError(
                    "ENFORCE mode requires enforcement Turnstile secret configuration"
                )
            if not self.enforcement_turnstile_expected_hostname.strip():
                raise ValueError(
                    "ENFORCE mode requires enforcement Turnstile hostname configuration"
                )
            if (
                self.is_production or self.is_staging
            ) and self.enforcement_source_trust_mode != "cloudflare_verified":
                raise ValueError(
                    "ENFORCE mode requires explicit cloudflare_verified source trust "
                    "in staging and production"
                )
            if (
                self.is_production or self.is_staging
            ) and self.waf_source_verification_mode != "cloudflare_tunnel":
                raise ValueError(
                    "ENFORCE mode requires cloudflare_tunnel WAF source verification "
                    "in staging and production"
                )
            if self.enforcement_turnstile_test_mode:
                if self.is_production or self.is_staging:
                    raise ValueError(
                        "enforcement Turnstile test mode is forbidden in staging "
                        "and production"
                    )
                if (
                    self.enforcement_turnstile_secret_key.strip()
                    not in TURNSTILE_TEST_SECRETS
                ):
                    raise ValueError(
                        "enforcement Turnstile test mode requires a published "
                        "Turnstile test secret"
                    )
            if (
                (self.is_production or self.is_staging)
                and self.enforcement_turnstile_secret_key.strip()
                in TURNSTILE_TEST_SECRETS
            ):
                raise ValueError(
                    "Cloudflare Turnstile test credentials are forbidden in staging "
                    "and production"
                )
        if self.cloudflare_target_verified_proof and (
            not self.cloudflare_target_isolation_enabled
            or self.waf_source_verification_mode != "cloudflare_tunnel"
        ):
            raise ValueError(
                "Cloudflare proof activation requires cloudflare_tunnel mode and "
                "the isolation overlay"
            )
        if self.waf_source_verification_mode == "cloudflare_tunnel":
            if not self.cloudflare_target_isolation_enabled:
                raise ValueError(
                    "cloudflare_tunnel mode requires the isolation overlay"
                )
            if not self.cloudflare_target_verified_proof:
                raise ValueError(
                    "cloudflare_tunnel mode requires explicit proof activation"
                )
            if not self.waf_audit_evidence_key.strip():
                raise ValueError(
                    "cloudflare_tunnel mode requires WAF_AUDIT_EVIDENCE_KEY"
                )
        if self.is_production or self.is_staging:
            if not self.api_secret_key:
                raise ValueError("API_SECRET_KEY is required in production and staging")
            if not self.waf_ingest_api_key:
                raise ValueError(
                    "WAF_INGEST_API_KEY is required in production and staging"
                )
            if len(self.waf_ingest_api_key) < 32:
                raise ValueError(
                    "WAF_INGEST_API_KEY must be at least 32 characters in "
                    "production and staging"
                )
            if self.waf_ingest_api_key == self.api_secret_key:
                raise ValueError("WAF_INGEST_API_KEY must differ from API_SECRET_KEY")
        if self.notification_worker_enabled:
            raw_key = (self.notification_payload_encryption_key or "").strip()
            try:
                payload_key = (
                    bytes.fromhex(raw_key)
                    if re.fullmatch(r"[0-9a-fA-F]{64}", raw_key)
                    else base64.b64decode(raw_key, validate=True)
                )
            except (ValueError, base64.binascii.Error):
                payload_key = b""
            if len(payload_key) != 32:
                raise ValueError(
                    "enabled notification worker requires a valid payload "
                    "encryption key"
                )
        if (
            self.notification_worker_enabled
            and self.email_provider == "resend"
            and (not self.resend_api_key or not self.resend_from_email)
        ):
            raise ValueError(
                "enabled Resend notification worker requires server-side "
                "provider configuration"
            )
        if (
            self.notification_worker_enabled
            and self.notification_worker_required
            and self.email_provider == "fake"
        ):
            raise ValueError(
                "required notification worker cannot use the fake email provider"
            )
        if (
            self.notification_worker_enabled
            and (self.is_production or self.is_staging)
            and self.email_provider == "fake"
        ):
            raise ValueError(
                "staging and production notification workers cannot use "
                "the fake email provider"
            )
        if self.threat_email_enabled and not self.threat_email_to:
            raise ValueError("enabled threat email notifications require a recipient")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"

    @property
    def is_staging(self) -> bool:
        return self.app_env == "staging"

    @property
    def telegram_available(self) -> bool:
        return bool(
            self.threat_telegram_enabled
            and (self.telegram_bot_token or "").strip()
            and (self.telegram_chat_id or "").strip()
        )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def reset_settings_cache():
    """Clear the settings cache. Useful for testing."""
    get_settings.cache_clear()
