import asyncio
import os
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from web_app.infrastructure.database.database import TrafficLabelReview, TrafficLog
from web_app.infrastructure.repositories.traffic_label_review_repository import (
    TrafficLabelReviewRepository,
)

POSTGRES_URL = os.getenv("CYBERTRACE_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires an explicit disposable PostgreSQL URL",
)


@pytest.mark.asyncio
async def test_concurrent_review_revisions_are_serialized_in_postgres():
    assert POSTGRES_URL is not None
    async_url = POSTGRES_URL
    if async_url.startswith("postgresql://"):
        async_url = "postgresql+asyncpg://" + async_url.removeprefix("postgresql://")
    elif async_url.startswith("postgres://"):
        async_url = "postgresql+asyncpg://" + async_url.removeprefix("postgres://")
    engine = create_async_engine(async_url, pool_size=5, max_overflow=0)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    traffic_log_id: int | None = None
    try:
        async with factory() as session:
            result = await session.execute(
                insert(TrafficLog)
                .values(
                    source_ip="203.0.113.240",
                    source_provenance="DIRECT_REMOTE_ADDR",
                    source_verification_status="UNVERIFIED",
                    http_request="POST /records/search HTTP/1.1",
                    request_path="/records/search",
                    request_method="POST",
                    status="COMPLETED",
                    prediction="SQL Injection",
                    confidence=0.98,
                    confidence_level="HIGH",
                    model_version="concurrency-test-model",
                    model_input_hash="a" * 64,
                    model_input_text="post /records/search injected=true",
                    preprocessing_version="http-preprocessor-v1",
                )
                .returning(TrafficLog.id)
            )
            traffic_log_id = result.scalar_one()
            await session.commit()

        async def create_review(reviewer_id: str):
            async with factory() as session:
                repository = TrafficLabelReviewRepository(session)
                return await repository.create_review_revision(
                    traffic_log_id=traffic_log_id,
                    verified_label="SQL Injection",
                    approval_state="approved_for_training",
                    reviewer_id=reviewer_id,
                    reviewer_role="ANALYST",
                    reviewed_at=datetime.now(timezone.utc),
                )

        first, second = await asyncio.gather(
            create_review("concurrency-analyst-1"),
            create_review("concurrency-analyst-2"),
        )

        assert {first.revision, second.revision} == {1, 2}
        async with factory() as session:
            rows = (
                await session.execute(
                    select(TrafficLabelReview)
                    .where(TrafficLabelReview.traffic_log_id == traffic_log_id)
                    .order_by(TrafficLabelReview.revision)
                )
            ).scalars().all()
            assert [row.revision for row in rows] == [1, 2]
            assert rows[-1].model_input_text == "post /records/search injected=true"
    finally:
        if traffic_log_id is not None:
            async with factory() as session:
                await session.execute(
                    delete(TrafficLabelReview).where(
                        TrafficLabelReview.traffic_log_id == traffic_log_id
                    )
                )
                await session.execute(
                    delete(TrafficLog).where(TrafficLog.id == traffic_log_id)
                )
                await session.commit()
        await engine.dispose()
