from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from web_app.domain.interfaces import TrafficLogEntity
from web_app.infrastructure.database.database import Base
from web_app.infrastructure.repositories.traffic_log_repository import (
    TrafficLogRepository,
)


@pytest.fixture
async def repository() -> TrafficLogRepository:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield TrafficLogRepository(session)

    await engine.dispose()


@pytest.mark.asyncio
async def test_get_stats_summary_returns_zero_safe_defaults(repository: TrafficLogRepository):
    summary = await repository.get_stats_summary()

    assert summary.total_requests == 0
    assert summary.avg_inference_latency_ms == 0.0
    assert summary.counts_by_label == {
        "SQL Injection": 0,
        "Code Injection": 0,
        "Other Attacks": 0,
        "Normal": 0,
    }


@pytest.mark.asyncio
async def test_get_alert_list_returns_filtered_total_and_stable_order(
    repository: TrafficLogRepository,
):
    older = TrafficLogEntity(
        transaction_id="txn-older",
        source_ip="10.0.0.1",
        request_path="/search",
        request_method="GET",
        http_request="GET /search?q=admin",
        prediction="Normal",
        confidence=0.45,
        confidence_level="LOW",
        inference_latency_ms=8.0,
        action_taken="ALLOWED",
    )
    newer = TrafficLogEntity(
        transaction_id="txn-newer",
        source_ip="10.0.0.2",
        request_path="/login",
        request_method="POST",
        http_request="POST /login username=admin' OR '1'='1",
        prediction="SQL Injection",
        confidence=0.93,
        confidence_level="HIGH",
        inference_latency_ms=12.5,
        action_taken="BLOCKED",
    )

    saved_older = await repository.save(older)
    saved_newer = await repository.save(newer)

    page = await repository.get_alert_list(
        page=1,
        page_size=1,
        severity="HIGH",
        time_range="7d",
        search="login",
    )

    assert page.total == 1
    assert page.page == 1
    assert page.page_size == 1
    assert [item.id for item in page.items] == [saved_newer.id]
    assert saved_older.id != saved_newer.id


@pytest.mark.asyncio
async def test_get_by_transaction_id_returns_entity(
    repository: TrafficLogRepository,
):
    saved = await repository.save(
        TrafficLogEntity(
            transaction_id="txn-123",
            source_ip="10.0.0.3",
            request_path="/api/users",
            request_method="GET",
            http_request="GET /api/users?id=1",
            prediction="Normal",
            confidence=0.61,
            confidence_level="MEDIUM",
            inference_latency_ms=4.5,
            action_taken="THROTTLED",
        )
    )

    found = await repository.get_by_transaction_id("txn-123")

    assert found is not None
    assert found.id == saved.id
    assert found.transaction_id == "txn-123"


@pytest.mark.asyncio
async def test_get_alert_list_preserves_filtered_total_when_page_is_empty(
    repository: TrafficLogRepository,
):
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-page-1",
            source_ip="10.0.0.4",
            request_path="/alerts",
            request_method="GET",
            http_request="GET /alerts?q=match",
            prediction="SQL Injection",
            confidence=0.91,
            confidence_level="HIGH",
            inference_latency_ms=6.0,
            action_taken="BLOCKED",
        )
    )

    page = await repository.get_alert_list(
        page=2,
        page_size=1,
        severity="HIGH",
        time_range="7d",
        search="match",
    )

    assert page.total == 1
    assert page.page == 2
    assert page.page_size == 1
    assert page.items == []


@pytest.mark.asyncio
async def test_save_if_absent_returns_existing_entity_for_duplicate_transaction_id(
    repository: TrafficLogRepository,
):
    entity = TrafficLogEntity(
        transaction_id="txn-dup-1",
        timestamp=datetime.now(),
        source_ip="198.51.100.10",
        request_path="/triage",
        request_method="POST",
        http_request="POST /triage HTTP/1.1",
        crs_score=11,
        crs_rule_ids=["942100"],
        prediction="SQL Injection",
        confidence=0.93,
        confidence_level="HIGH",
        inference_latency_ms=8.1,
        model_version="test-model-v1",
        action_taken="BLOCKED",
    )

    first, first_created = await repository.save_if_absent(entity)
    second, second_created = await repository.save_if_absent(entity)

    assert first_created is True
    assert second_created is False
    assert second.id == first.id
    assert second.transaction_id == "txn-dup-1"


@pytest.mark.asyncio
async def test_claim_processing_uses_transaction_id_reservation(
    repository: TrafficLogRepository,
):
    placeholder = TrafficLogEntity(
        transaction_id="txn-claim-1",
        timestamp=datetime.now(),
        source_ip="198.51.100.11",
        request_path="/triage",
        request_method="POST",
        http_request="POST /triage HTTP/1.1",
        crs_score=7,
        crs_rule_ids=["942100"],
        status="PROCESSING",
    )

    first_claim = await repository.claim_processing(placeholder)
    second_claim = await repository.claim_processing(placeholder)
    stored = await repository.get_by_transaction_id("txn-claim-1")

    assert first_claim is True
    assert second_claim is False
    assert stored is not None
    assert stored.status == "PROCESSING"
    assert stored.prediction is None


@pytest.mark.asyncio
async def test_complete_processing_updates_placeholder_row(
    repository: TrafficLogRepository,
):
    await repository.claim_processing(
        TrafficLogEntity(
            transaction_id="txn-complete-1",
            timestamp=datetime.now(),
            source_ip="198.51.100.12",
            request_path="/triage",
            request_method="POST",
            http_request="POST /triage HTTP/1.1",
            crs_score=7,
            crs_rule_ids=["942100"],
            status="PROCESSING",
        )
    )

    completed = await repository.complete_processing(
        "txn-complete-1",
        prediction="SQL Injection",
        confidence=0.98,
        confidence_level="HIGH",
        inference_latency_ms=3.4,
        model_version="test-model-v1",
        action_taken="BLOCKED",
    )

    assert completed.status == "COMPLETED"
    assert completed.prediction == "SQL Injection"
    assert completed.action_taken == "BLOCKED"
