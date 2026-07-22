import logging
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from web_app.application.enforcement_use_cases import (
    CheckShadowEnforcementUseCase,
    EvaluateEnforcementUseCase,
    RecordShadowRecommendationUseCase,
    VerifyEnforcementChallengeUseCase,
)
from web_app.domain.enforcement import (
    ACTIVE_POLICY_VERSION,
    ChallengeGrant,
    EffectiveRecommendation,
    EnforcementMode,
    EnforcementScope,
    EnforcementTier,
    RecommendedAction,
    RequestWindowState,
    TurnstileVerificationResult,
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


class ActiveRepository(RecordingRepository):
    def __init__(self, effective=None, *, fail=False):
        super().__init__(effective, fail=fail)
        self.grants = {}
        self.counts = {}

    async def find_effective_enforceable(
        self, *, source_ip, scope, now, policy_version, require_verified
    ):
        if self.fail:
            raise RuntimeError("database unavailable")
        if self.effective is None or self.effective.policy_version != policy_version:
            return None
        if require_verified and self.effective.source_verification_status != "VERIFIED":
            return None
        return self.effective

    async def find_valid_challenge_grant(
        self, *, source_ip, scope, tier, policy_version, now
    ):
        grant = self.grants.get((source_ip, tier, policy_version))
        return grant if grant and grant.expires_at > now else None

    async def increment_request_window(
        self, *, source_ip, scope, counter_kind, policy_version, now, window_seconds
    ):
        if self.fail:
            raise RuntimeError("database unavailable")
        key = (source_ip, counter_kind, policy_version)
        self.counts[key] = self.counts.get(key, 0) + 1
        start = now.replace(second=0, microsecond=0)
        return RequestWindowState(
            source_ip=source_ip,
            scope=scope,
            counter_kind=counter_kind,
            policy_version=policy_version,
            window_start=start,
            window_end=start + timedelta(seconds=window_seconds),
            request_count=self.counts[key],
        )

    async def upsert_challenge_grant(self, grant):
        self.grants[(grant.source_ip, grant.tier, grant.policy_version)] = grant
        return grant


class StubTurnstile:
    def __init__(self, result):
        self.result = result
        self.tokens = []

    async def verify(self, *, token, remote_ip):
        self.tokens.append((token, remote_ip))
        return self.result


class ExpiringActiveRepository(ActiveRepository):
    async def find_effective_enforceable(
        self, *, source_ip, scope, now, policy_version, require_verified
    ):
        result = await super().find_effective_enforceable(
            source_ip=source_ip,
            scope=scope,
            now=now,
            policy_version=policy_version,
            require_verified=require_verified,
        )
        return result if result is not None and result.expires_at > now else None


def _active_recommendation(tier: EnforcementTier, *, source_status="VERIFIED"):
    return EffectiveRecommendation(
        trigger_traffic_log_id=42,
        scope=EnforcementScope.RECORD_SEARCH,
        tier=tier,
        action={
            EnforcementTier.LOW: RecommendedAction.CHALLENGE,
            EnforcementTier.MEDIUM: RecommendedAction.THROTTLE,
            EnforcementTier.HIGH: RecommendedAction.APPLICATION_BLOCK,
            EnforcementTier.CRITICAL: RecommendedAction.WAF_BLOCK,
        }[tier],
        mode=EnforcementMode.ENFORCE,
        policy_version=ACTIVE_POLICY_VERSION,
        created_at=datetime(2026, 7, 21, tzinfo=timezone.utc),
        expires_at=datetime(2026, 7, 21, 0, 15, tzinfo=timezone.utc),
        source_verification_status=source_status,
    )


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
async def test_record_shadow_recommendation_anchors_expiry_to_authoritative_event():
    repo = RecordingRepository()
    event_time = datetime(2026, 7, 20, 10, tzinfo=timezone.utc)
    now = event_time + timedelta(seconds=10)
    use_case = RecordShadowRecommendationUseCase(
        repository=repo, mode=EnforcementMode.SHADOW, ttl_seconds=900, clock=lambda: now
    )

    assert (
        await use_case.execute(
            alert_id=42,
            prediction="SQL Injection",
            confidence_level="HIGH",
            request_path="/records/search",
            occurred_at=event_time,
        )
        is True
    )
    assert repo.inserted[0].created_at == now
    assert repo.inserted[0].expires_at == event_time + timedelta(seconds=900)


@pytest.mark.asyncio
async def test_record_shadow_recommendation_does_not_resurrect_expired_event():
    repo = RecordingRepository()
    event_time = datetime(2026, 7, 20, 10, tzinfo=timezone.utc)
    now = event_time + timedelta(hours=5)
    use_case = RecordShadowRecommendationUseCase(
        repository=repo, mode=EnforcementMode.SHADOW, ttl_seconds=900, clock=lambda: now
    )

    assert (
        await use_case.execute(
            alert_id=42,
            prediction="SQL Injection",
            confidence_level="HIGH",
            request_path="/records/search",
            occurred_at=event_time,
        )
        is False
    )
    assert repo.inserted == []


@pytest.mark.asyncio
async def test_record_shadow_recommendation_skips_off_normal_and_unsupported():
    repo = RecordingRepository()
    use_case = RecordShadowRecommendationUseCase(
        repository=repo, mode=EnforcementMode.OFF, ttl_seconds=900
    )
    assert (
        await use_case.execute(
            alert_id=1,
            prediction="SQL Injection",
            confidence_level="CRITICAL",
            request_path="/records/search",
        )
        is False
    )
    assert repo.inserted == []

    use_case = RecordShadowRecommendationUseCase(
        repository=repo, mode=EnforcementMode.SHADOW, ttl_seconds=900
    )
    assert (
        await use_case.execute(
            alert_id=None,
            prediction="SQL Injection",
            confidence_level="CRITICAL",
            request_path="/records/search",
        )
        is False
    )
    assert (
        await use_case.execute(
            alert_id=2,
            prediction="Normal",
            confidence_level="CRITICAL",
            request_path="/records/search",
        )
        is False
    )
    assert (
        await use_case.execute(
            alert_id=3,
            prediction="SQL Injection",
            confidence_level="CRITICAL",
            request_path="/other",
        )
        is False
    )


@pytest.mark.asyncio
async def test_record_shadow_recommendation_is_fail_open():
    repo = RecordingRepository(fail=True)
    use_case = RecordShadowRecommendationUseCase(
        repository=repo, mode=EnforcementMode.SHADOW, ttl_seconds=900
    )
    assert (
        await use_case.execute(
            alert_id=42,
            prediction="SQL Injection",
            confidence_level="CRITICAL",
            request_path="/records/search",
        )
        is False
    )


@pytest.mark.asyncio
async def test_record_enforcement_recommendation_persists_explicit_v2_mode():
    repo = RecordingRepository()
    use_case = RecordShadowRecommendationUseCase(
        repository=repo,
        mode=EnforcementMode.ENFORCE,
        ttl_seconds=900,
        clock=lambda: datetime(2026, 7, 21, tzinfo=timezone.utc),
    )

    assert (
        await use_case.execute(
            alert_id=43,
            prediction="SQL Injection",
            confidence_level="LOW",
            request_path="/records/search",
        )
        is True
    )
    assert repo.inserted[0].mode is EnforcementMode.ENFORCE
    assert repo.inserted[0].policy_version == ACTIVE_POLICY_VERSION
    assert repo.inserted[0].action is RecommendedAction.CHALLENGE


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


@pytest.mark.asyncio
async def test_low_enforcement_allows_maximum_then_challenges_first_request_above_it():
    now = datetime(2026, 7, 21, 0, 1, tzinfo=timezone.utc)
    repo = ActiveRepository(_active_recommendation(EnforcementTier.LOW))
    use_case = EvaluateEnforcementUseCase(
        repository=repo,
        mode=EnforcementMode.ENFORCE,
        low_window_seconds=60,
        low_max_unchallenged_requests=2,
        medium_window_seconds=60,
        medium_max_requests=10,
        allow_unverified_source_for_tests=False,
        clock=lambda: now,
    )

    assert [
        (
            await use_case.execute(
                source_ip="203.0.113.20", scope=EnforcementScope.RECORD_SEARCH
            )
        ).decision
        for _ in range(3)
    ] == ["ALLOW", "ALLOW", "CHALLENGE"]


@pytest.mark.asyncio
async def test_low_valid_grant_allows_without_incrementing_counter():
    now = datetime(2026, 7, 21, 0, 1, tzinfo=timezone.utc)
    repo = ActiveRepository(_active_recommendation(EnforcementTier.LOW))
    repo.grants[("203.0.113.21", EnforcementTier.LOW, ACTIVE_POLICY_VERSION)] = (
        ChallengeGrant(
            source_ip="203.0.113.21",
            scope=EnforcementScope.RECORD_SEARCH,
            tier=EnforcementTier.LOW,
            policy_version=ACTIVE_POLICY_VERSION,
            verified_at=now,
            expires_at=now + timedelta(minutes=5),
        )
    )
    result = await EvaluateEnforcementUseCase(
        repository=repo,
        mode=EnforcementMode.ENFORCE,
        low_window_seconds=60,
        low_max_unchallenged_requests=2,
        medium_window_seconds=60,
        medium_max_requests=10,
        allow_unverified_source_for_tests=False,
        clock=lambda: now,
    ).execute(source_ip="203.0.113.21", scope=EnforcementScope.RECORD_SEARCH)

    assert result.decision == "ALLOW"
    assert repo.counts == {}


@pytest.mark.asyncio
async def test_medium_requires_grant_then_throttles_after_authoritative_limit():
    now = datetime(2026, 7, 21, 0, 1, tzinfo=timezone.utc)
    repo = ActiveRepository(_active_recommendation(EnforcementTier.MEDIUM))
    use_case = EvaluateEnforcementUseCase(
        repository=repo,
        mode=EnforcementMode.ENFORCE,
        low_window_seconds=60,
        low_max_unchallenged_requests=5,
        medium_window_seconds=60,
        medium_max_requests=2,
        allow_unverified_source_for_tests=False,
        clock=lambda: now,
    )
    first = await use_case.execute(
        source_ip="203.0.113.22", scope=EnforcementScope.RECORD_SEARCH
    )
    repo.grants[("203.0.113.22", EnforcementTier.MEDIUM, ACTIVE_POLICY_VERSION)] = (
        ChallengeGrant(
            source_ip="203.0.113.22",
            scope=EnforcementScope.RECORD_SEARCH,
            tier=EnforcementTier.MEDIUM,
            policy_version=ACTIVE_POLICY_VERSION,
            verified_at=now,
            expires_at=now + timedelta(minutes=5),
        )
    )
    results = [
        await use_case.execute(
            source_ip="203.0.113.22", scope=EnforcementScope.RECORD_SEARCH
        )
        for _ in range(3)
    ]

    assert first.decision == "CHALLENGE"
    assert [result.decision for result in results] == ["ALLOW", "ALLOW", "THROTTLE"]
    assert results[-1].retry_after_seconds == 60


@pytest.mark.asyncio
async def test_high_enforcement_blocks_without_challenge_or_counter_state():
    now = datetime(2026, 7, 21, 0, 1, tzinfo=timezone.utc)
    repo = ActiveRepository(_active_recommendation(EnforcementTier.HIGH))

    result = await EvaluateEnforcementUseCase(
        repository=repo,
        mode=EnforcementMode.ENFORCE,
        low_window_seconds=60,
        low_max_unchallenged_requests=5,
        medium_window_seconds=60,
        medium_max_requests=10,
        allow_unverified_source_for_tests=False,
        clock=lambda: now,
    ).execute(source_ip="203.0.113.22", scope=EnforcementScope.RECORD_SEARCH)

    assert result.decision == "BLOCK"
    assert result.matched is True
    assert result.recommendation is repo.effective
    assert result.challenge_tier is None
    assert result.retry_after_seconds is None
    assert repo.grants == {}
    assert repo.counts == {}


@pytest.mark.asyncio
async def test_high_enforcement_requires_application_block_policy_action():
    now = datetime(2026, 7, 21, 0, 1, tzinfo=timezone.utc)
    malformed = replace(
        _active_recommendation(EnforcementTier.HIGH),
        action=RecommendedAction.THROTTLE,
    )

    result = await EvaluateEnforcementUseCase(
        repository=ActiveRepository(malformed),
        mode=EnforcementMode.ENFORCE,
        low_window_seconds=60,
        low_max_unchallenged_requests=5,
        medium_window_seconds=60,
        medium_max_requests=10,
        allow_unverified_source_for_tests=False,
        clock=lambda: now,
    ).execute(source_ip="203.0.113.22", scope=EnforcementScope.RECORD_SEARCH)

    assert result.decision == "ALLOW"
    assert result.matched is False


@pytest.mark.asyncio
async def test_active_evaluation_fails_open_for_ineligible_source_and_repo_failure():
    now = datetime(2026, 7, 21, 0, 1, tzinfo=timezone.utc)
    unverified = ActiveRepository(
        _active_recommendation(EnforcementTier.LOW, source_status="UNVERIFIED")
    )
    result = await EvaluateEnforcementUseCase(
        repository=unverified,
        mode=EnforcementMode.ENFORCE,
        low_window_seconds=60,
        low_max_unchallenged_requests=0,
        medium_window_seconds=60,
        medium_max_requests=10,
        allow_unverified_source_for_tests=False,
        clock=lambda: now,
    ).execute(source_ip="203.0.113.23", scope=EnforcementScope.RECORD_SEARCH)
    assert result.decision == "ALLOW"
    assert result.matched is False

    failed = await EvaluateEnforcementUseCase(
        repository=ActiveRepository(
            _active_recommendation(EnforcementTier.LOW), fail=True
        ),
        mode=EnforcementMode.ENFORCE,
        low_window_seconds=60,
        low_max_unchallenged_requests=0,
        medium_window_seconds=60,
        medium_max_requests=10,
        allow_unverified_source_for_tests=True,
        clock=lambda: now,
    ).execute(source_ip="203.0.113.24", scope=EnforcementScope.RECORD_SEARCH)
    assert failed.decision == "ALLOW"
    assert failed.degraded is True


@pytest.mark.asyncio
async def test_successful_challenge_creates_tier_bound_grant_capped_by_recommendation():
    now = datetime(2026, 7, 21, 0, 1, tzinfo=timezone.utc)
    repo = ActiveRepository(_active_recommendation(EnforcementTier.LOW))
    result = await VerifyEnforcementChallengeUseCase(
        repository=repo,
        verifier=StubTurnstile(TurnstileVerificationResult(success=True)),
        mode=EnforcementMode.ENFORCE,
        grant_ttl_seconds=300,
        allow_unverified_source_for_tests=False,
        clock=lambda: now,
    ).execute(
        source_ip="203.0.113.25",
        scope=EnforcementScope.RECORD_SEARCH,
        token="valid-token",
    )

    assert result.verified is True
    grant = repo.grants[("203.0.113.25", EnforcementTier.LOW, ACTIVE_POLICY_VERSION)]
    assert grant.expires_at == now + timedelta(minutes=5)


@pytest.mark.asyncio
async def test_invalid_or_unavailable_challenge_never_creates_grant():
    now = datetime(2026, 7, 21, 0, 1, tzinfo=timezone.utc)
    for provider_result, expected_status in [
        (TurnstileVerificationResult(success=False), "INVALID"),
        (TurnstileVerificationResult(success=False, unavailable=True), "UNAVAILABLE"),
    ]:
        repo = ActiveRepository(_active_recommendation(EnforcementTier.MEDIUM))
        result = await VerifyEnforcementChallengeUseCase(
            repository=repo,
            verifier=StubTurnstile(provider_result),
            mode=EnforcementMode.ENFORCE,
            grant_ttl_seconds=300,
            allow_unverified_source_for_tests=False,
            clock=lambda: now,
        ).execute(
            source_ip="203.0.113.26",
            scope=EnforcementScope.RECORD_SEARCH,
            token="invalid-token",
        )
        assert result.verified is False
        assert result.status == expected_status
        assert repo.grants == {}


@pytest.mark.asyncio
async def test_challenge_uses_fresh_time_after_provider_verification() -> None:
    initial = datetime(2026, 7, 21, 0, 1, tzinfo=timezone.utc)
    expired = initial + timedelta(seconds=3)
    recommendation = replace(
        _active_recommendation(EnforcementTier.LOW),
        expires_at=initial + timedelta(seconds=2),
    )
    repo = ExpiringActiveRepository(recommendation)
    times = iter([initial, expired])

    result = await VerifyEnforcementChallengeUseCase(
        repository=repo,
        verifier=StubTurnstile(TurnstileVerificationResult(success=True)),
        mode=EnforcementMode.ENFORCE,
        grant_ttl_seconds=300,
        allow_unverified_source_for_tests=False,
        clock=lambda: next(times),
    ).execute(
        source_ip="203.0.113.27",
        scope=EnforcementScope.RECORD_SEARCH,
        token="valid-token",
    )

    assert result.verified is False
    assert result.status == "NO_ACTIVE_ENFORCEMENT"
    assert repo.grants == {}


@pytest.mark.asyncio
async def test_active_decision_and_challenge_success_emit_safe_structured_events(
    caplog: pytest.LogCaptureFixture,
) -> None:
    now = datetime(2026, 7, 21, 0, 1, tzinfo=timezone.utc)
    repo = ActiveRepository(_active_recommendation(EnforcementTier.MEDIUM))
    with caplog.at_level(logging.INFO):
        decision = await EvaluateEnforcementUseCase(
            repository=repo,
            mode=EnforcementMode.ENFORCE,
            low_window_seconds=60,
            low_max_unchallenged_requests=5,
            medium_window_seconds=60,
            medium_max_requests=10,
            allow_unverified_source_for_tests=False,
            clock=lambda: now,
        ).execute(
            source_ip="203.0.113.28",
            scope=EnforcementScope.RECORD_SEARCH,
        )
        challenge = await VerifyEnforcementChallengeUseCase(
            repository=repo,
            verifier=StubTurnstile(TurnstileVerificationResult(success=True)),
            mode=EnforcementMode.ENFORCE,
            grant_ttl_seconds=300,
            allow_unverified_source_for_tests=False,
            clock=lambda: now,
        ).execute(
            source_ip="203.0.113.28",
            scope=EnforcementScope.RECORD_SEARCH,
            token="must-not-appear-in-logs",
        )

    assert decision.decision == "CHALLENGE"
    assert challenge.verified is True
    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert '"event":"enforcement.evaluated"' in messages
    assert '"actual_decision":"CHALLENGE"' in messages
    assert '"event":"enforcement.challenge_verification_succeeded"' in messages
    assert "must-not-appear-in-logs" not in messages
