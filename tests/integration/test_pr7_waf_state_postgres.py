import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, insert, update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from web_app.infrastructure.database.database import (
    EnforcementRecommendationRow,
    TrafficLog,
    WafEffectiveStateRow,
    WafEnforcementStateRow,
)
from web_app.infrastructure.repositories.waf_state_repository import (
    WafStateRepository,
)

DATABASE_URL = os.environ.get("PR7_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="PR7_TEST_DATABASE_URL is not configured"
)


@pytest.fixture
async def session_factory():
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(delete(WafEffectiveStateRow))
        await session.execute(delete(EnforcementRecommendationRow))
        await session.execute(delete(TrafficLog))
        await session.execute(update(WafEnforcementStateRow).values(revision=0))
        await session.commit()
    yield factory
    await engine.dispose()


async def _insert_recommendation(
    factory,
    recommendation_id: int,
    *,
    expires_at: datetime,
    source_ip: str = "203.0.113.7",
    request_path: str = "/records/search",
) -> None:
    async with factory() as session:
        await session.execute(
            insert(TrafficLog).values(
                id=recommendation_id,
                source_ip=source_ip,
                source_provenance="CLOUDFLARE_CONNECTING_IP",
                source_verification_status="VERIFIED",
                request_path=request_path,
                http_request="GET /records/search HTTP/1.1",
                created_at=datetime.now(timezone.utc),
                timestamp=datetime.now(timezone.utc),
                status="COMPLETED",
                processing_attempt=0,
            )
        )
        await session.execute(
            insert(EnforcementRecommendationRow).values(
                id=recommendation_id,
                trigger_traffic_log_id=recommendation_id,
                scope="RECORD_SEARCH",
                enforcement_tier="CRITICAL",
                recommended_action="WAF_BLOCK",
                enforcement_mode="SHADOW",
                policy_version="confidence-waf-enforcement-v1",
                created_at=datetime.now(timezone.utc),
                expires_at=expires_at,
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_activation_duplicate_extension_and_snapshot(session_factory) -> None:
    now = datetime.now(timezone.utc)
    await _insert_recommendation(
        session_factory, 1, expires_at=now + timedelta(minutes=10)
    )
    async with session_factory() as session:
        first = await WafStateRepository(session).record_active(
            recommendation_id=1,
            source_ip="::ffff:203.0.113.7",
            protected_path="/records/search",
            expires_at=now + timedelta(minutes=5),
        )
        duplicate = await WafStateRepository(session).record_active(
            recommendation_id=1,
            source_ip="203.0.113.7",
            protected_path="/records/search",
            expires_at=now + timedelta(minutes=5),
        )
    assert first.category == "ACTIVATED"
    assert duplicate.category == "DUPLICATE"
    assert duplicate.revision == first.revision

    async with session_factory() as session:
        snapshot = await WafStateRepository(session).snapshot()
    assert snapshot.revision == 1
    assert snapshot.items[0]["source_ip"] == "203.0.113.7"


@pytest.mark.asyncio
async def test_longer_owner_supersedes_and_passive_expiry_is_snapshot_stable(
    session_factory,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_recommendation(
        session_factory,
        1,
        expires_at=now + timedelta(minutes=10),
        source_ip="203.0.113.8",
    )
    await _insert_recommendation(
        session_factory,
        2,
        expires_at=now + timedelta(minutes=10),
        source_ip="203.0.113.8",
    )
    async with session_factory() as session:
        first = await WafStateRepository(session).record_active(
            recommendation_id=1,
            source_ip="203.0.113.8",
            protected_path="/records/search",
            expires_at=now + timedelta(seconds=1),
        )
        shorter = await WafStateRepository(session).record_active(
            recommendation_id=2,
            source_ip="203.0.113.8",
            protected_path="/records/search",
            expires_at=now + timedelta(seconds=1),
        )
    assert first.revision == 1
    assert shorter.category == "SHORTER_OR_EQUAL"
    assert shorter.revision == 1

    await asyncio.sleep(1.2)
    async with session_factory() as session:
        passive = await WafStateRepository(session).snapshot()
    assert passive.revision == 1
    assert len(passive.items) == 1

    async with session_factory() as session:
        longer = await WafStateRepository(session).record_active(
            recommendation_id=2,
            source_ip="203.0.113.8",
            protected_path="/records/search",
            expires_at=now + timedelta(minutes=8),
        )
    assert longer.category == "ACTIVATED"
    assert longer.revision == 2


@pytest.mark.asyncio
async def test_revoke_active_removes_snapshot_owner_and_terminal_revoke_is_noop(
    session_factory,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_recommendation(
        session_factory,
        1,
        expires_at=now + timedelta(minutes=10),
        source_ip="203.0.113.9",
    )
    async with session_factory() as session:
        await WafStateRepository(session).record_active(
            recommendation_id=1,
            source_ip="203.0.113.9",
            protected_path="/records/search",
            expires_at=now + timedelta(minutes=5),
        )
        revoked = await WafStateRepository(session).revoke(recommendation_id=1)
        noop = await WafStateRepository(session).revoke(recommendation_id=1)
        snapshot = await WafStateRepository(session).snapshot()
    assert revoked.category == "REVOKED"
    assert noop.category == "TERMINAL_NOOP"
    assert snapshot.items == []
    assert snapshot.revision == 2
