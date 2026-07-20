from datetime import datetime, timedelta, timezone

import pytest

from web_app.application.enforcement_use_cases import (
    CheckShadowEnforcementUseCase,
    RecordShadowRecommendationUseCase,
)
from web_app.domain.enforcement import (
    EffectiveRecommendation,
    EnforcementMode,
    EnforcementScope,
    EnforcementTier,
    RecommendedAction,
)


class RecordingRepository:
    def __init__(self, effective=None, *, fail=False):
        self.inserted = []
        self.effective = effective
        self.fail = fail

    async def insert_if_absent(self, recommendation):
        if self.fail:
            raise RuntimeError("database unavailable")
        self.inserted.append(recommendation)
        return True

    async def find_effective_active(self, *, source_ip, scope, now):
        if self.fail:
            raise RuntimeError("database unavailable")
        return self.effective


@pytest.mark.asyncio
async def test_record_shadow_recommendation_persists_expiring_policy():
    repo = RecordingRepository()
    now = datetime(2026, 7, 20, tzinfo=timezone.utc)
    use_case = RecordShadowRecommendationUseCase(
        repository=repo, mode=EnforcementMode.SHADOW, ttl_seconds=900, clock=lambda: now
    )

    recorded = await use_case.execute(
        alert_id=42,
        prediction="SQL Injection",
        confidence_level="HIGH",
        request_path="/records/search",
    )

    assert recorded is True
    assert repo.inserted[0].trigger_traffic_log_id == 42
    assert repo.inserted[0].action is RecommendedAction.APPLICATION_BLOCK
    assert repo.inserted[0].expires_at == now + timedelta(seconds=900)


@pytest.mark.asyncio
async def test_record_shadow_recommendation_skips_off_normal_and_unsupported():
    repo = RecordingRepository()
    use_case = RecordShadowRecommendationUseCase(
        repository=repo, mode=EnforcementMode.OFF, ttl_seconds=900
    )
    assert await use_case.execute(
        alert_id=1,
        prediction="SQL Injection",
        confidence_level="CRITICAL",
        request_path="/records/search",
    ) is False
    assert repo.inserted == []

    use_case = RecordShadowRecommendationUseCase(
        repository=repo, mode=EnforcementMode.SHADOW, ttl_seconds=900
    )
    assert await use_case.execute(
        alert_id=None,
        prediction="SQL Injection",
        confidence_level="CRITICAL",
        request_path="/records/search",
    ) is False
    assert await use_case.execute(
        alert_id=2,
        prediction="Normal",
        confidence_level="CRITICAL",
        request_path="/records/search",
    ) is False
    assert await use_case.execute(
        alert_id=3,
        prediction="SQL Injection",
        confidence_level="CRITICAL",
        request_path="/other",
    ) is False


@pytest.mark.asyncio
async def test_record_shadow_recommendation_is_fail_open():
    repo = RecordingRepository(fail=True)
    use_case = RecordShadowRecommendationUseCase(
        repository=repo, mode=EnforcementMode.SHADOW, ttl_seconds=900
    )
    assert await use_case.execute(
        alert_id=42,
        prediction="SQL Injection",
        confidence_level="CRITICAL",
        request_path="/records/search",
    ) is False


@pytest.mark.asyncio
async def test_check_shadow_enforcement_always_allows_and_logs_match():
    repo = RecordingRepository(
        EffectiveRecommendation(
            trigger_traffic_log_id=42,
            scope=EnforcementScope.RECORD_SEARCH,
            tier=EnforcementTier.CRITICAL,
            action=RecommendedAction.WAF_BLOCK,
            mode=EnforcementMode.SHADOW,
            policy_version="confidence-enforcement-v1",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            source_verification_status="VERIFIED",
        )
    )
    result = await CheckShadowEnforcementUseCase(
        repository=repo, mode=EnforcementMode.SHADOW
    ).execute(source_ip="::ffff:192.0.2.10", scope=EnforcementScope.RECORD_SEARCH)
    assert result.decision == "ALLOW"
    assert result.matched is True


@pytest.mark.asyncio
async def test_check_shadow_enforcement_invalid_ip_or_failure_allows():
    repo = RecordingRepository(fail=True)
    result = await CheckShadowEnforcementUseCase(
        repository=repo, mode=EnforcementMode.SHADOW
    ).execute(source_ip="not-an-ip", scope=EnforcementScope.RECORD_SEARCH)
    assert result.decision == "ALLOW"
    assert result.matched is False

    result = await CheckShadowEnforcementUseCase(
        repository=repo, mode=EnforcementMode.SHADOW
    ).execute(source_ip="192.0.2.10", scope=EnforcementScope.RECORD_SEARCH)
    assert result.decision == "ALLOW"
    assert result.matched is False
    assert result.degraded is True
