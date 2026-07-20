from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from web_app.domain.enforcement import (
    EnforcementMode,
    EnforcementScope,
    EnforcementTier,
    NewEnforcementRecommendation,
    RecommendedAction,
)
from web_app.infrastructure.repositories.enforcement_recommendation_repository import (
    EnforcementRecommendationRepository,
)

POSTGRES_URL = os.getenv("CYBERTRACE_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires an explicit disposable PostgreSQL URL",
)


@pytest.fixture(autouse=True)
def migrated_database(monkeypatch: pytest.MonkeyPatch):
    assert POSTGRES_URL is not None
    monkeypatch.setenv("DATABASE_URL", POSTGRES_URL)
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO traffic_logs (
                    source_ip, source_provenance,
                    source_verification_status, http_request
                ) VALUES (
                    '203.0.113.10', 'DIRECT_REMOTE_ADDR',
                    'UNVERIFIED', 'GET /records/search'
                )
                RETURNING id
                """
            )
            trigger_id = cursor.fetchone()[0]

    yield trigger_id

    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM enforcement_recommendations "
                "WHERE trigger_traffic_log_id = %s",
                (trigger_id,),
            )
            cursor.execute("DELETE FROM traffic_logs WHERE id = %s", (trigger_id,))


@pytest.mark.asyncio
async def test_concurrent_repository_inserts_are_idempotent(
    migrated_database: int,
) -> None:
    assert POSTGRES_URL is not None
    trigger_id = migrated_database

    async_url = POSTGRES_URL
    if async_url.startswith("postgresql://"):
        async_url = "postgresql+asyncpg://" + async_url.removeprefix("postgresql://")
    elif async_url.startswith("postgres://"):
        async_url = "postgresql+asyncpg://" + async_url.removeprefix("postgres://")
    engine = create_async_engine(async_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(timezone.utc)
    recommendation = NewEnforcementRecommendation(
        trigger_traffic_log_id=trigger_id,
        scope=EnforcementScope.RECORD_SEARCH,
        tier=EnforcementTier.HIGH,
        action=RecommendedAction.APPLICATION_BLOCK,
        mode=EnforcementMode.SHADOW,
        policy_version="confidence-enforcement-v1",
        created_at=now,
        expires_at=now + timedelta(minutes=15),
    )

    async def insert_once() -> bool:
        async with session_factory() as session:
            return await EnforcementRecommendationRepository(session).insert_if_absent(
                recommendation
            )

    results = await asyncio.gather(insert_once(), insert_once())
    assert sorted(results) == [False, True]
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM enforcement_recommendations "
                "WHERE trigger_traffic_log_id = %s",
                (trigger_id,),
            )
            assert cursor.fetchone()[0] == 1
    await engine.dispose()
