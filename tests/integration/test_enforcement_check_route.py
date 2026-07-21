from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import web_app.presentation.api.routes as routes
import web_app.presentation.dependencies.auth as auth
from web_app.config import reset_settings_cache
from web_app.presentation.app import create_app
from web_app.domain.enforcement import (
    ACTIVE_POLICY_VERSION,
    CounterKind,
    EffectiveRecommendation,
    EnforcementMode,
    EnforcementScope,
    EnforcementTier,
    RecommendedAction,
    RequestWindowState,
    TurnstileVerificationResult,
)


class EmptyRepository:
    async def find_effective_active(self, **kwargs):
        return None


class FailingRepository:
    async def find_effective_active(self, **kwargs):
        raise RuntimeError("database unavailable")


class ActiveLowRepository:
    def __init__(self):
        self.recommendation = EffectiveRecommendation(
            trigger_traffic_log_id=1,
            scope=EnforcementScope.RECORD_SEARCH,
            tier=EnforcementTier.LOW,
            action=RecommendedAction.CHALLENGE,
            mode=EnforcementMode.ENFORCE,
            policy_version=ACTIVE_POLICY_VERSION,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            source_verification_status="UNVERIFIED",
        )
        self.count = 0

    async def find_effective_enforceable(self, **kwargs):
        return self.recommendation

    async def find_valid_challenge_grant(self, **kwargs):
        return None

    async def increment_request_window(self, **kwargs):
        self.count += 1
        now = kwargs["now"]
        return RequestWindowState(
            source_ip=kwargs["source_ip"],
            scope=kwargs["scope"],
            counter_kind=kwargs["counter_kind"],
            policy_version=kwargs["policy_version"],
            window_start=now,
            window_end=now + timedelta(seconds=60),
            request_count=self.count,
        )

    async def upsert_challenge_grant(self, grant):
        self.grant = grant
        return grant


class SuccessfulVerifier:
    async def verify(self, **kwargs):
        return TurnstileVerificationResult(success=True)


@pytest.fixture(autouse=True)
def disable_notification_worker_for_route_tests(monkeypatch):
    monkeypatch.setenv("NOTIFICATION_WORKER_ENABLED", "false")
    monkeypatch.setenv("NOTIFICATION_WORKER_REQUIRED", "false")
    reset_settings_cache()
    yield
    reset_settings_cache()


def test_enforcement_check_requires_its_dedicated_credential(monkeypatch):
    key = "enforcement-key-for-integration-tests-32chars"
    settings = SimpleNamespace(enforcement_check_api_key=key, enforcement_mode="shadow")
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    app = create_app()
    app.dependency_overrides[routes.get_enforcement_repository] = (
        lambda: EmptyRepository()
    )
    with TestClient(app) as client:
        missing = client.post(
            "/api/internal/enforcement/check",
            json={"scope": "RECORD_SEARCH", "source_ip": "203.0.113.10"},
        )
        valid = client.post(
            "/api/internal/enforcement/check",
            headers={"Authorization": f"Bearer {key}"},
            json={"scope": "RECORD_SEARCH", "source_ip": "203.0.113.10"},
        )
    app.dependency_overrides.clear()

    assert missing.status_code == 401
    assert valid.status_code == 200
    assert valid.json() == {"decision": "ALLOW"}


def test_enforcement_check_returns_503_when_lookup_is_unavailable(monkeypatch):
    key = "enforcement-key-for-integration-tests-32chars"
    settings = SimpleNamespace(enforcement_check_api_key=key, enforcement_mode="shadow")
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    app = create_app()
    app.dependency_overrides[routes.get_enforcement_repository] = (
        lambda: FailingRepository()
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/internal/enforcement/check",
            headers={"Authorization": f"Bearer {key}"},
            json={"scope": "RECORD_SEARCH", "source_ip": "203.0.113.10"},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json() == {"detail": "Shadow enforcement lookup unavailable"}


def test_active_enforcement_returns_challenge_for_unverified_test_source(monkeypatch):
    key = "enforcement-key-for-integration-tests-32chars"
    settings = SimpleNamespace(
        enforcement_check_api_key=key,
        enforcement_mode="enforce",
        enforcement_low_window_seconds=60,
        enforcement_low_max_unchallenged_requests=0,
        enforcement_medium_window_seconds=60,
        enforcement_medium_max_requests=10,
        enforcement_allow_unverified_source_for_tests=True,
        enforcement_challenge_grant_ttl_seconds=300,
        enforcement_turnstile_secret_key="secret",
        enforcement_turnstile_expected_hostname="localhost",
        enforcement_turnstile_timeout_seconds=3,
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    app = create_app()
    app.dependency_overrides[routes.get_enforcement_repository] = (
        lambda: ActiveLowRepository()
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/internal/enforcement/check",
            headers={"Authorization": f"Bearer {key}"},
            json={"scope": "RECORD_SEARCH", "source_ip": "203.0.113.10"},
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "decision": "CHALLENGE",
        "enforcement_tier": "LOW",
    }


def test_active_challenge_verification_persists_only_verified_grant(monkeypatch):
    key = "enforcement-key-for-integration-tests-32chars"
    settings = SimpleNamespace(
        enforcement_check_api_key=key,
        enforcement_mode="enforce",
        enforcement_challenge_grant_ttl_seconds=300,
        enforcement_allow_unverified_source_for_tests=True,
        enforcement_turnstile_secret_key="secret",
        enforcement_turnstile_expected_hostname="localhost",
        enforcement_turnstile_timeout_seconds=3,
    )
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    app = create_app()
    repository = ActiveLowRepository()
    app.dependency_overrides[routes.get_enforcement_repository] = lambda: repository
    app.dependency_overrides[routes.get_turnstile_verifier] = lambda: SuccessfulVerifier()
    with TestClient(app) as client:
        response = client.post(
            "/api/internal/enforcement/challenge",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "scope": "RECORD_SEARCH",
                "source_ip": "203.0.113.10",
                "token": "valid-token",
            },
        )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"verified": True, "status": "VERIFIED"}
    assert repository.grant.tier is EnforcementTier.LOW
