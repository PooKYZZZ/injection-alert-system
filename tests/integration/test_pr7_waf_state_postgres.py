import asyncio
import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import delete, func, insert, select, text, update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from web_app.domain.waf_state import WafLifecycle
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
                prediction="SQL Injection",
                confidence_level="CRITICAL",
            )
        )
        await session.commit()


async def _insert_traffic_log(
    factory,
    traffic_log_id: int,
    *,
    source_ip: str = "203.0.113.10",
    request_path: str = "/records/search",
    source_provenance: str = "CLOUDFLARE_CONNECTING_IP",
    source_verification_status: str = "VERIFIED",
    prediction: str = "SQL Injection",
    confidence_level: str = "CRITICAL",
) -> None:
    async with factory() as session:
        await session.execute(
            insert(TrafficLog).values(
                id=traffic_log_id,
                source_ip=source_ip,
                source_provenance=source_provenance,
                source_verification_status=source_verification_status,
                request_path=request_path,
                http_request="GET /records/search HTTP/1.1",
                created_at=datetime.now(timezone.utc),
                timestamp=datetime.now(timezone.utc),
                status="COMPLETED",
                processing_attempt=0,
                prediction=prediction,
                confidence_level=confidence_level,
            )
        )
        await session.commit()


@pytest.mark.asyncio
async def test_recommendation_and_effective_state_are_one_idempotent_mutation(
    session_factory,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_traffic_log(session_factory, 10)

    async with session_factory() as session:
        repository = WafStateRepository(session)
        first = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=10,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
        )
        second = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=10,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
        )
        recommendation_count = await session.scalar(
            select(func.count()).select_from(EnforcementRecommendationRow)
        )

    assert first.category == "ACTIVATED"
    assert second.category == "DUPLICATE"
    assert first.recommendation_id == second.recommendation_id
    assert recommendation_count == 1


@pytest.mark.asyncio
async def test_capacity_rejection_is_final_for_effective_state_but_keeps_history(
    session_factory,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_traffic_log(session_factory, 11, source_ip="203.0.113.11")
    await _insert_traffic_log(session_factory, 12, source_ip="203.0.113.12")

    async with session_factory() as session:
        repository = WafStateRepository(session)
        first = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=11,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
            capacity=1,
        )
        rejected = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=12,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
            capacity=1,
        )
        recommendations = await session.scalar(
            select(func.count()).select_from(EnforcementRecommendationRow)
        )
        effective_rows = await session.scalar(
            select(func.count()).select_from(WafEffectiveStateRow)
        )

    assert first.category == "ACTIVATED"
    assert rejected.category == "CAPACITY_REJECTED"
    assert rejected.revision == first.revision
    assert recommendations == 2
    assert effective_rows == 1


@pytest.mark.asyncio
async def test_capacity_rejection_is_not_reconsidered_after_owner_revoke(
    session_factory,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_traffic_log(session_factory, 20, source_ip="203.0.113.20")
    await _insert_traffic_log(session_factory, 21, source_ip="203.0.113.21")
    await _insert_traffic_log(session_factory, 22, source_ip="203.0.113.22")

    async with session_factory() as session:
        repository = WafStateRepository(session)
        owner = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=20,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
            capacity=1,
        )
        rejected = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=21,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
            capacity=1,
        )
        await repository.revoke(recommendation_id=owner.recommendation_id)
        replay = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=21,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
            capacity=1,
        )
        new_candidate = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=22,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
            capacity=1,
        )

    assert rejected.category == "CAPACITY_REJECTED"
    assert replay.category == "DUPLICATE"
    assert new_candidate.category == "ACTIVATED"


@pytest.mark.asyncio
async def test_shorter_or_equal_rejection_is_not_reconsidered_after_owner_revoke(
    session_factory,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_traffic_log(session_factory, 30, source_ip="203.0.113.30")
    await _insert_traffic_log(session_factory, 31, source_ip="203.0.113.30")
    await _insert_traffic_log(session_factory, 32, source_ip="203.0.113.30")

    async with session_factory() as session:
        repository = WafStateRepository(session)
        owner = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=30,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=8),
        )
        shorter = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=31,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=1),
        )
        await repository.revoke(recommendation_id=owner.recommendation_id)
        replay = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=31,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=9),
        )
        new_candidate = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=32,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
        )

    assert shorter.category == "SHORTER_OR_EQUAL"
    assert replay.category == "DUPLICATE"
    assert new_candidate.category == "ACTIVATED"


@pytest.mark.asyncio
async def test_expired_candidate_is_final_and_new_candidate_can_activate(
    session_factory,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_traffic_log(session_factory, 40, source_ip="203.0.113.40")
    await _insert_traffic_log(session_factory, 41, source_ip="203.0.113.41")

    async with session_factory() as session:
        repository = WafStateRepository(session)
        expired = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=40,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now - timedelta(seconds=1),
        )
        replay = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=40,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
        )
        new_candidate = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=41,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
        )

    assert expired.category == "EXPIRED_CANDIDATE"
    assert replay.category == "DUPLICATE"
    assert new_candidate.category == "ACTIVATED"


@pytest.mark.asyncio
async def test_authoritative_eligibility_rejects_unverified_or_normal_traffic(
    session_factory,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_traffic_log(
        session_factory,
        50,
        source_verification_status="UNVERIFIED",
    )
    await _insert_traffic_log(
        session_factory,
        51,
        source_ip="203.0.113.51",
        prediction="Normal",
    )

    async with session_factory() as session:
        repository = WafStateRepository(session)
        unverified = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=50,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
        )
        normal = await repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=51,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
        )

    assert unverified.category == "INELIGIBLE"
    assert normal.category == "INELIGIBLE"


@pytest.mark.asyncio
async def test_snapshot_transaction_reports_repeatable_read_and_read_only(
    session_factory,
) -> None:
    async with session_factory() as session:
        engine = session.bind.execution_options(
            isolation_level="REPEATABLE READ",
            postgresql_readonly=True,
        )
        async with engine.connect() as connection:
            async with connection.begin():
                isolation = (
                    await connection.execute(text("SHOW transaction_isolation"))
                ).scalar_one()
                read_only = (
                    await connection.execute(text("SHOW transaction_read_only"))
                ).scalar_one()
    assert isolation == "repeatable read"
    assert read_only == "on"


@pytest.mark.asyncio
async def test_snapshot_has_stable_view_across_concurrent_commit(
    session_factory,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_traffic_log(session_factory, 60, source_ip="203.0.113.60")
    await _insert_traffic_log(session_factory, 61, source_ip="203.0.113.61")
    async with session_factory() as session:
        await WafStateRepository(session).record_critical_waf_recommendation(
            trigger_traffic_log_id=60,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
        )

    async with session_factory() as snapshot_session:
        engine = snapshot_session.bind.execution_options(
            isolation_level="REPEATABLE READ",
            postgresql_readonly=True,
        )
        async with engine.connect() as connection:
            async with connection.begin():
                before_revision = (
                    await connection.execute(
                        select(WafEnforcementStateRow.revision).where(
                            WafEnforcementStateRow.id == 1
                        )
                    )
                ).scalar_one()
                before_count = (
                    await connection.execute(
                        select(func.count())
                        .select_from(WafEffectiveStateRow)
                        .where(WafEffectiveStateRow.status == WafLifecycle.ACTIVE)
                    )
                ).scalar_one()
                async with session_factory() as mutation_session:
                    await WafStateRepository(
                        mutation_session
                    ).record_critical_waf_recommendation(
                        trigger_traffic_log_id=61,
                        recommendation_expires_at=now + timedelta(minutes=10),
                        effective_expires_at=now + timedelta(minutes=5),
                    )
                after_revision = (
                    await connection.execute(
                        select(WafEnforcementStateRow.revision).where(
                            WafEnforcementStateRow.id == 1
                        )
                    )
                ).scalar_one()
                after_count = (
                    await connection.execute(
                        select(func.count())
                        .select_from(WafEffectiveStateRow)
                        .where(WafEffectiveStateRow.status == WafLifecycle.ACTIVE)
                    )
                ).scalar_one()
    async with session_factory() as session:
        current = await WafStateRepository(session).snapshot()

    assert (before_revision, after_revision, before_count, after_count) == (1, 1, 1, 1)
    assert current.revision == 2
    assert len(current.items) == 2


@pytest.mark.asyncio
async def test_lock_wait_reads_mutation_clock_after_singleton_lock(
    session_factory,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_traffic_log(session_factory, 70, source_ip="203.0.113.70")
    async with session_factory() as blocker:
        await blocker.begin()
        await blocker.execute(
            select(WafEnforcementStateRow)
            .where(WafEnforcementStateRow.id == 1)
            .with_for_update()
        )
        task = asyncio.create_task(
            _run_activation_after_lock_wait(
                session_factory,
                now,
            )
        )
        await asyncio.sleep(1.2)
        await blocker.commit()
        result = await task
    assert result.category == "EXPIRED_CANDIDATE"


async def _run_activation_after_lock_wait(session_factory, now: datetime):
    async with session_factory() as session:
        return await WafStateRepository(session).record_critical_waf_recommendation(
            trigger_traffic_log_id=70,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(seconds=1),
        )


@pytest.mark.asyncio
async def test_different_keys_serialize_revisions_without_collision(
    session_factory,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_traffic_log(session_factory, 80, source_ip="203.0.113.80")
    await _insert_traffic_log(session_factory, 81, source_ip="203.0.113.81")

    async def activate(log_id: int):
        async with session_factory() as session:
            return await WafStateRepository(session).record_critical_waf_recommendation(
                trigger_traffic_log_id=log_id,
                recommendation_expires_at=now + timedelta(minutes=10),
                effective_expires_at=now + timedelta(minutes=5),
            )

    results = await asyncio.gather(activate(80), activate(81))
    assert {result.category for result in results} == {"ACTIVATED"}
    assert {result.revision for result in results} == {1, 2}


@pytest.mark.asyncio
async def test_atomic_mutation_rolls_back_recommendation_on_state_failure(
    session_factory,
    monkeypatch,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_traffic_log(session_factory, 13)

    async def fail_after_recommendation_insert(*args, **kwargs):
        raise RuntimeError("injected state mutation failure")

    monkeypatch.setattr(
        WafStateRepository, "_expire_active", fail_after_recommendation_insert
    )
    async with session_factory() as session:
        with pytest.raises(RuntimeError, match="injected state mutation failure"):
            await WafStateRepository(session).record_critical_waf_recommendation(
                trigger_traffic_log_id=13,
                recommendation_expires_at=now + timedelta(minutes=10),
                effective_expires_at=now + timedelta(minutes=5),
            )

    async with session_factory() as session:
        recommendation_count = await session.scalar(
            select(func.count()).select_from(EnforcementRecommendationRow)
        )
    assert recommendation_count == 0


@pytest.mark.asyncio
async def test_same_key_concurrency_has_one_active_owner_and_one_revision(
    session_factory,
) -> None:
    now = datetime.now(timezone.utc)
    await _insert_traffic_log(session_factory, 14)
    await _insert_traffic_log(session_factory, 15)

    async def activate(traffic_log_id: int):
        async with session_factory() as session:
            return await WafStateRepository(session).record_critical_waf_recommendation(
                trigger_traffic_log_id=traffic_log_id,
                recommendation_expires_at=now + timedelta(minutes=10),
                effective_expires_at=now + timedelta(minutes=5),
            )

    results = await asyncio.gather(activate(14), activate(15))
    categories = {result.category for result in results}
    async with session_factory() as session:
        active_count = await session.scalar(
            select(func.count())
            .select_from(WafEffectiveStateRow)
            .where(WafEffectiveStateRow.status == "ACTIVE")
        )
        revision = await session.scalar(
            select(WafEnforcementStateRow.revision).where(
                WafEnforcementStateRow.id == 1
            )
        )

    assert categories == {"ACTIVATED", "SHORTER_OR_EQUAL"}
    assert active_count == 1
    assert revision == 1


@pytest.mark.asyncio
async def test_activation_duplicate_extension_and_snapshot(session_factory) -> None:
    now = datetime.now(timezone.utc)
    await _insert_recommendation(
        session_factory, 1, expires_at=now + timedelta(minutes=10)
    )
    async with session_factory() as session:
        first = await WafStateRepository(session).record_critical_waf_recommendation(
            trigger_traffic_log_id=1,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
        )
        duplicate = await WafStateRepository(
            session
        ).record_critical_waf_recommendation(
            trigger_traffic_log_id=1,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
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
    await _insert_recommendation(
        session_factory,
        3,
        expires_at=now + timedelta(minutes=10),
        source_ip="203.0.113.8",
    )
    async with session_factory() as session:
        first = await WafStateRepository(session).record_critical_waf_recommendation(
            trigger_traffic_log_id=1,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(seconds=1),
        )
        shorter = await WafStateRepository(session).record_critical_waf_recommendation(
            trigger_traffic_log_id=2,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(seconds=1),
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
        replay = await WafStateRepository(session).record_critical_waf_recommendation(
            trigger_traffic_log_id=2,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=8),
        )
        new_candidate = await WafStateRepository(
            session
        ).record_critical_waf_recommendation(
            trigger_traffic_log_id=3,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=8),
        )
    assert replay.category == "DUPLICATE_WITH_CLEANUP"
    assert new_candidate.category == "ACTIVATED"
    assert new_candidate.revision == 3


@pytest.mark.asyncio
async def test_longer_candidate_supersedes_active_owner(session_factory) -> None:
    now = datetime.now(timezone.utc)
    await _insert_recommendation(
        session_factory,
        1,
        expires_at=now + timedelta(minutes=30),
        source_ip="203.0.113.10",
    )
    await _insert_recommendation(
        session_factory,
        2,
        expires_at=now + timedelta(minutes=30),
        source_ip="203.0.113.10",
    )
    async with session_factory() as session:
        owner = await WafStateRepository(
            session
        ).record_critical_waf_recommendation(
            trigger_traffic_log_id=1,
            recommendation_expires_at=now + timedelta(minutes=30),
            effective_expires_at=now + timedelta(minutes=5),
        )
        replacement = await WafStateRepository(
            session
        ).record_critical_waf_recommendation(
            trigger_traffic_log_id=2,
            recommendation_expires_at=now + timedelta(minutes=30),
            effective_expires_at=now + timedelta(minutes=10),
        )
    assert owner.category == "ACTIVATED"
    assert replacement.category == "SUPERSEDED"
    assert replacement.revision == 2

    async with session_factory() as session:
        snapshot = await WafStateRepository(session).snapshot()
    assert snapshot.revision == 2
    assert [item["recommendation_id"] for item in snapshot.items] == [2]


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
        activated = await WafStateRepository(
            session
        ).record_critical_waf_recommendation(
            trigger_traffic_log_id=1,
            recommendation_expires_at=now + timedelta(minutes=10),
            effective_expires_at=now + timedelta(minutes=5),
        )
        revoked = await WafStateRepository(session).revoke(
            recommendation_id=activated.recommendation_id
        )
        noop = await WafStateRepository(session).revoke(
            recommendation_id=activated.recommendation_id
        )
        snapshot = await WafStateRepository(session).snapshot()
    assert revoked.category == "REVOKED"
    assert noop.category == "TERMINAL_NOOP"
    assert snapshot.items == []
    assert snapshot.revision == 2
