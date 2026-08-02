from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from sqlalchemy import select

from web_app.infrastructure.database.database import Base, TrafficLabelReview as ReviewRow, TrafficLog
from web_app.infrastructure.repositories.traffic_label_review_repository import (
    TrafficLabelReviewRepository,
)


@pytest.fixture
async def repository():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield TrafficLabelReviewRepository(session)
    await engine.dispose()


async def _insert_alert(session: AsyncSession) -> int:
    alert = TrafficLog(
        source_ip="203.0.113.10",
        source_provenance="DIRECT_REMOTE_ADDR",
        source_verification_status="UNVERIFIED",
        http_request="GET /records/search HTTP/1.1",
        prediction="SQL Injection",
        model_version="model-v1",
        ingest_fingerprint_sha256="a" * 64,
        status="COMPLETED",
    )
    session.add(alert)
    await session.commit()
    return alert.id


@pytest.mark.asyncio
async def test_review_persists_metadata_and_latest_query(repository):
    alert_id = await _insert_alert(repository._session)
    reviewed_at = datetime.now(timezone.utc)

    review = await repository.create_review_revision(
        traffic_log_id=alert_id,
        verified_label="SQL Injection",
        approval_state="approved_for_training",
        reviewer_id="analyst-1",
        reviewer_role="ANALYST",
        reviewed_at=reviewed_at,
        review_note="Confirmed by analyst",
    )

    assert review is not None
    assert review.revision == 1
    assert review.predicted_label == "SQL Injection"
    assert review.model_version == "model-v1"
    assert review.input_hash == "a" * 64
    assert (await repository.get_latest_review(alert_id)).id == review.id


@pytest.mark.asyncio
async def test_unknown_alert_is_rejected_without_review(repository):
    assert await repository.create_review_revision(
        traffic_log_id=999,
        verified_label="Normal",
        approval_state="excluded_from_training",
        reviewer_id="analyst-1",
        reviewer_role="ANALYST",
        reviewed_at=datetime.now(timezone.utc),
    ) is None
    assert await repository.get_latest_review(999) is None


@pytest.mark.asyncio
async def test_second_review_is_revision_two_and_history_is_preserved(repository):
    alert_id = await _insert_alert(repository._session)
    common = {
        "traffic_log_id": alert_id,
        "reviewer_id": "analyst-1",
        "reviewer_role": "ANALYST",
        "reviewed_at": datetime.now(timezone.utc),
    }
    first = await repository.create_review_revision(
        **common,
        verified_label="SQL Injection",
        approval_state="approved_for_training",
    )
    second = await repository.create_review_revision(
        **common,
        verified_label="Other Attacks",
        approval_state="excluded_from_training",
    )

    assert first.revision == 1
    assert second.revision == 2
    rows = (await repository._session.execute(
        select(ReviewRow).order_by(ReviewRow.revision)
    )).scalars().all()
    assert [row.revision for row in rows] == [1, 2]
    assert (await repository.get_latest_review(alert_id)).verified_label == "Other Attacks"


@pytest.mark.asyncio
async def test_database_rejects_noncanonical_label_and_approval_state(repository):
    alert_id = await _insert_alert(repository._session)
    arguments = {
        "traffic_log_id": alert_id,
        "reviewer_id": "analyst-1",
        "reviewer_role": "ANALYST",
        "reviewed_at": datetime.now(timezone.utc),
    }
    with pytest.raises(IntegrityError):
        await repository.create_review_revision(
            **arguments,
            verified_label="Free-form label",
            approval_state="approved_for_training",
        )
    await repository._session.rollback()

    with pytest.raises(IntegrityError):
        await repository.create_review_revision(
            **arguments,
            verified_label="Normal",
            approval_state="maybe_training",
        )
    await repository._session.rollback()
