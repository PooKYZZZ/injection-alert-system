from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from web_app.domain.enforcement import (
    ACTIVE_POLICY_VERSION,
    ChallengeGrant,
    CounterKind,
    EnforcementMode,
    EnforcementScope,
    EnforcementTier,
    NewEnforcementRecommendation,
    RecommendedAction,
    RequestWindowState,
)
from web_app.domain.source_address import SourceProvenance, SourceVerificationStatus
from web_app.infrastructure.database.database import Base, TrafficLog
from web_app.infrastructure.repositories.enforcement_recommendation_repository import (
    EnforcementRecommendationRepository,
)


@pytest.fixture
async def repository():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield EnforcementRecommendationRepository(session)
    await engine.dispose()


async def _insert_traffic_log(session: AsyncSession, source_ip: str) -> int:
    row = TrafficLog(
        source_ip=source_ip,
        source_provenance=SourceProvenance.DIRECT_REMOTE_ADDR.value,
        source_verification_status=SourceVerificationStatus.UNVERIFIED.value,
        request_path="/records/search",
        request_method="GET",
        http_request="GET /records/search HTTP/1.1",
        prediction="SQL Injection",
        confidence_level="HIGH",
        action_taken="BLOCKED",
        status="COMPLETED",
    )
    session.add(row)
    await session.commit()
    return row.id


def _recommendation(
    *,
    alert_id: int,
    tier: EnforcementTier,
    action: RecommendedAction,
    created_at: datetime,
    expires_at: datetime,
) -> NewEnforcementRecommendation:
    return NewEnforcementRecommendation(
        trigger_traffic_log_id=alert_id,
        scope=EnforcementScope.RECORD_SEARCH,
        tier=tier,
        action=action,
        mode=EnforcementMode.SHADOW,
        policy_version="confidence-enforcement-v1",
        created_at=created_at,
        expires_at=expires_at,
    )


@pytest.mark.asyncio
async def test_insert_is_idempotent_and_lookup_excludes_expired_rows(repository) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    session = repository._session
    alert_id = await _insert_traffic_log(session, "203.0.113.10")
    recommendation = _recommendation(
        alert_id=alert_id,
        tier=EnforcementTier.HIGH,
        action=RecommendedAction.APPLICATION_BLOCK,
        created_at=now,
        expires_at=now + timedelta(minutes=15),
    )

    assert await repository.insert_if_absent(recommendation) is True
    assert await repository.insert_if_absent(recommendation) is False
    active = await repository.find_effective_active(
        source_ip="203.0.113.10",
        scope=EnforcementScope.RECORD_SEARCH,
        now=now + timedelta(seconds=1),
    )

    assert active is not None
    assert active.trigger_traffic_log_id == alert_id
    assert active.tier is EnforcementTier.HIGH
    assert active.action is RecommendedAction.APPLICATION_BLOCK
    assert active.source_verification_status == "UNVERIFIED"
    assert (
        await repository.find_effective_active(
            source_ip="203.0.113.10",
            scope=EnforcementScope.RECORD_SEARCH,
            now=now + timedelta(minutes=16),
        )
        is None
    )


@pytest.mark.asyncio
async def test_lookup_uses_tier_precedence_then_newest_row(repository) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    session = repository._session
    low_id = await _insert_traffic_log(session, "203.0.113.11")
    high_id = await _insert_traffic_log(session, "203.0.113.11")
    critical_id = await _insert_traffic_log(session, "203.0.113.11")
    for alert_id, tier, action, created_at in [
        (low_id, EnforcementTier.LOW, RecommendedAction.MONITOR, now),
        (high_id, EnforcementTier.HIGH, RecommendedAction.APPLICATION_BLOCK, now + timedelta(seconds=1)),
        (critical_id, EnforcementTier.CRITICAL, RecommendedAction.WAF_BLOCK, now + timedelta(seconds=2)),
    ]:
        assert await repository.insert_if_absent(
            _recommendation(
                alert_id=alert_id,
                tier=tier,
                action=action,
                created_at=created_at,
                expires_at=now + timedelta(minutes=15),
            )
        )

    active = await repository.find_effective_active(
        source_ip="203.0.113.11",
        scope=EnforcementScope.RECORD_SEARCH,
        now=now + timedelta(seconds=3),
    )

    assert active is not None
    assert active.trigger_traffic_log_id == critical_id
    assert active.tier is EnforcementTier.CRITICAL
    assert active.action is RecommendedAction.WAF_BLOCK


@pytest.mark.asyncio
async def test_active_lookup_ignores_shadow_and_deferred_highest_tiers(repository) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    session = repository._session
    low_id = await _insert_traffic_log(session, "203.0.113.12")
    critical_id = await _insert_traffic_log(session, "203.0.113.12")
    assert await repository.insert_if_absent(
        _recommendation(
            alert_id=low_id,
            tier=EnforcementTier.LOW,
            action=RecommendedAction.MONITOR,
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
    )
    active = _recommendation(
        alert_id=critical_id,
        tier=EnforcementTier.CRITICAL,
        action=RecommendedAction.WAF_BLOCK,
        created_at=now + timedelta(seconds=1),
        expires_at=now + timedelta(minutes=15),
    )
    active = replace(
        active, mode=EnforcementMode.ENFORCE, policy_version=ACTIVE_POLICY_VERSION
    )
    assert await repository.insert_if_absent(active)

    selected = await repository.find_effective_enforceable(
        source_ip="203.0.113.12",
        scope=EnforcementScope.RECORD_SEARCH,
        now=now + timedelta(seconds=2),
        policy_version=ACTIVE_POLICY_VERSION,
    )
    assert selected is None


@pytest.mark.asyncio
async def test_request_window_upsert_returns_authoritative_count_and_window(repository) -> None:
    now = datetime(2026, 7, 21, 10, 0, 7, tzinfo=timezone.utc)
    first = await repository.increment_request_window(
        source_ip="203.0.113.13",
        scope=EnforcementScope.RECORD_SEARCH,
        counter_kind=CounterKind.LOW_LIGHT,
        policy_version=ACTIVE_POLICY_VERSION,
        now=now,
        window_seconds=60,
    )
    second = await repository.increment_request_window(
        source_ip="203.0.113.13",
        scope=EnforcementScope.RECORD_SEARCH,
        counter_kind=CounterKind.LOW_LIGHT,
        policy_version=ACTIVE_POLICY_VERSION,
        now=now + timedelta(seconds=10),
        window_seconds=60,
    )

    assert isinstance(first, RequestWindowState)
    assert first.request_count == 1
    assert second.request_count == 2
    assert second.window_start == datetime(2026, 7, 21, 10, 0, tzinfo=timezone.utc)
    assert second.window_end == datetime(2026, 7, 21, 10, 1, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_challenge_grant_is_tier_bound_and_expiry_is_retrievable(repository) -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    grant = ChallengeGrant(
        source_ip="203.0.113.14",
        scope=EnforcementScope.RECORD_SEARCH,
        tier=EnforcementTier.LOW,
        policy_version=ACTIVE_POLICY_VERSION,
        verified_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    await repository.upsert_challenge_grant(grant)

    assert await repository.find_valid_challenge_grant(
        source_ip="203.0.113.14",
        scope=EnforcementScope.RECORD_SEARCH,
        tier=EnforcementTier.LOW,
        policy_version=ACTIVE_POLICY_VERSION,
        now=now + timedelta(seconds=1),
    ) is not None
    assert await repository.find_valid_challenge_grant(
        source_ip="203.0.113.14",
        scope=EnforcementScope.RECORD_SEARCH,
        tier=EnforcementTier.MEDIUM,
        policy_version=ACTIVE_POLICY_VERSION,
        now=now + timedelta(seconds=1),
    ) is None
