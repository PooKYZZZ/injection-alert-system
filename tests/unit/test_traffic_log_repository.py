from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from web_app.domain.interfaces import TrafficLogEntity
from web_app.infrastructure.database.database import Base
from web_app.infrastructure.repositories import traffic_log_repository as repo_module
from web_app.infrastructure.repositories.traffic_log_repository import (
    _StatsCache,
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
        yield TrafficLogRepository(session, session_factory=session_factory)

    await engine.dispose()


@pytest.fixture(autouse=True)
def clear_stats_cache():
    repo_module._stats_cache._store.clear()
    yield
    repo_module._stats_cache._store.clear()


@pytest.mark.asyncio
async def test_get_stats_summary_returns_zero_safe_defaults(
    repository: TrafficLogRepository,
):
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
async def test_save_and_reload_preserves_waf_metadata(
    repository: TrafficLogRepository,
):
    saved = await repository.save(
        TrafficLogEntity(
            transaction_id="txn-waf-meta-1",
            source_ip="203.0.113.10",
            request_path="/login",
            request_method="POST",
            http_request="POST /login HTTP/1.1",
            crs_score=12,
            crs_rule_ids=["942100", "949110"],
            ingest_source="modsec_audit_bridge",
            matched_rule_messages=["SQL Injection Attack Detected via libinjection"],
            matched_rule_tags=["attack-sqli", "paranoia-level/1"],
            prediction="SQL Injection",
            confidence=0.91,
            confidence_level="HIGH",
            action_taken="BLOCKED",
        )
    )

    reloaded = await repository.get_by_transaction_id("txn-waf-meta-1")

    assert reloaded is not None
    assert reloaded.id == saved.id
    assert reloaded.crs_score == 12
    assert reloaded.crs_rule_ids == ["942100", "949110"]
    assert reloaded.ingest_source == "modsec_audit_bridge"
    assert reloaded.matched_rule_messages == [
        "SQL Injection Attack Detected via libinjection"
    ]
    assert reloaded.matched_rule_tags == ["attack-sqli", "paranoia-level/1"]


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
async def test_claim_or_reclaim_processing_claims_fresh_row_and_sets_lease(
    repository: TrafficLogRepository,
):
    now = datetime.now(timezone.utc)
    claimed = await repository.claim_or_reclaim_processing(
        TrafficLogEntity(
            transaction_id="txn-lease-1",
            timestamp=now,
            source_ip="198.51.100.12",
            request_path="/triage",
            request_method="POST",
            http_request="POST /triage HTTP/1.1",
            crs_score=7,
            crs_rule_ids=["942100"],
            status="PROCESSING",
        ),
        owner_token="owner-1",
        lease_expires_at=now + timedelta(seconds=30),
        now=now,
    )

    assert claimed is not None
    assert claimed.status == "PROCESSING"
    assert claimed.processing_owner_token == "owner-1"
    assert claimed.processing_attempt == 1
    assert claimed.lease_expires_at is not None


@pytest.mark.asyncio
async def test_claim_or_reclaim_processing_reclaims_stale_row(
    repository: TrafficLogRepository,
):
    stale_now = datetime.now(timezone.utc)
    await repository.claim_or_reclaim_processing(
        TrafficLogEntity(
            transaction_id="txn-reclaim-1",
            timestamp=stale_now - timedelta(seconds=31),
            source_ip="198.51.100.13",
            request_path="/triage",
            request_method="POST",
            http_request="POST /triage HTTP/1.1",
            crs_score=7,
            crs_rule_ids=["942100"],
            status="PROCESSING",
        ),
        owner_token="old-owner",
        lease_expires_at=stale_now - timedelta(seconds=1),
        now=stale_now - timedelta(seconds=1),
    )

    reclaimed = await repository.claim_or_reclaim_processing(
        TrafficLogEntity(
            transaction_id="txn-reclaim-1",
            timestamp=stale_now,
            source_ip="198.51.100.13",
            request_path="/triage",
            request_method="POST",
            http_request="POST /triage HTTP/1.1",
            crs_score=7,
            crs_rule_ids=["942100"],
            status="PROCESSING",
        ),
        owner_token="new-owner",
        lease_expires_at=stale_now + timedelta(seconds=30),
        now=stale_now,
    )

    assert reclaimed is not None
    assert reclaimed.processing_owner_token == "new-owner"
    assert reclaimed.processing_attempt == 2


@pytest.mark.asyncio
async def test_complete_processing_updates_placeholder_row(
    repository: TrafficLogRepository,
):
    now = datetime.now(timezone.utc)
    await repository.claim_or_reclaim_processing(
        TrafficLogEntity(
            transaction_id="txn-complete-1",
            timestamp=now,
            source_ip="198.51.100.12",
            request_path="/triage",
            request_method="POST",
            http_request="POST /triage HTTP/1.1",
            crs_score=7,
            crs_rule_ids=["942100"],
            status="PROCESSING",
        ),
        owner_token="owner-complete",
        lease_expires_at=now + timedelta(seconds=30),
        now=now,
    )

    completed = await repository.complete_processing(
        "txn-complete-1",
        owner_token="owner-complete",
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


@pytest.mark.asyncio
async def test_complete_processing_rejects_late_owner(
    repository: TrafficLogRepository,
):
    now = datetime.now(timezone.utc)
    await repository.claim_or_reclaim_processing(
        TrafficLogEntity(
            transaction_id="txn-complete-late-1",
            timestamp=now,
            source_ip="198.51.100.14",
            request_path="/triage",
            request_method="POST",
            http_request="POST /triage HTTP/1.1",
            crs_score=7,
            crs_rule_ids=["942100"],
            status="PROCESSING",
        ),
        owner_token="owner-old",
        lease_expires_at=now + timedelta(seconds=30),
        now=now,
    )
    await repository.claim_or_reclaim_processing(
        TrafficLogEntity(
            transaction_id="txn-complete-late-1",
            timestamp=now + timedelta(seconds=31),
            source_ip="198.51.100.14",
            request_path="/triage",
            request_method="POST",
            http_request="POST /triage HTTP/1.1",
            crs_score=7,
            crs_rule_ids=["942100"],
            status="PROCESSING",
        ),
        owner_token="owner-new",
        lease_expires_at=now + timedelta(seconds=61),
        now=now + timedelta(seconds=31),
    )

    completed = await repository.complete_processing(
        "txn-complete-late-1",
        owner_token="owner-old",
        prediction="SQL Injection",
        confidence=0.98,
        confidence_level="HIGH",
        inference_latency_ms=3.4,
        model_version="test-model-v1",
        action_taken="BLOCKED",
    )

    assert completed.processing_owner_token == "owner-new"
    assert completed.status == "PROCESSING"


@pytest.mark.asyncio
async def test_activity_buckets_use_monotonic_window_aligned_starts(
    repository: TrafficLogRepository,
):
    reference_time = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
    window_start = reference_time - timedelta(hours=24)

    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-bucket-boundary-1",
            timestamp=window_start,
            source_ip="198.51.100.20",
            request_path="/boundary/start",
            request_method="GET",
            http_request="GET /boundary/start",
            prediction="SQL Injection",
            confidence=0.95,
            confidence_level="HIGH",
            inference_latency_ms=2.0,
            action_taken="BLOCKED",
        )
    )
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-bucket-boundary-2",
            timestamp=reference_time - timedelta(seconds=1),
            source_ip="198.51.100.21",
            request_path="/boundary/end-minus-1s",
            request_method="GET",
            http_request="GET /boundary/end-minus-1s",
            prediction="Normal",
            confidence=0.10,
            confidence_level="LOW",
            inference_latency_ms=1.5,
            action_taken="ALLOWED",
        )
    )
    # End boundary is exclusive; this row must not be counted.
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-bucket-boundary-3",
            timestamp=reference_time,
            source_ip="198.51.100.22",
            request_path="/boundary/end",
            request_method="GET",
            http_request="GET /boundary/end",
            prediction="Code Injection",
            confidence=0.91,
            confidence_level="HIGH",
            inference_latency_ms=1.8,
            action_taken="THROTTLED",
        )
    )

    buckets = await repository.get_activity_buckets(
        window="24h",
        buckets=24,
        reference_time=reference_time,
    )

    assert len(buckets) == 24
    assert buckets[0].timestamp_start == window_start

    for idx in range(1, len(buckets)):
        assert buckets[idx].timestamp_start > buckets[idx - 1].timestamp_start
        assert (
            buckets[idx].timestamp_start - buckets[idx - 1].timestamp_start
        ) == timedelta(hours=1)

    assert sum(bucket.total_count for bucket in buckets) == 2
    assert sum(bucket.blocked_count for bucket in buckets) == 1
    assert sum(bucket.allowed_count for bucket in buckets) == 1
    assert sum(bucket.throttled_count for bucket in buckets) == 0


@pytest.mark.asyncio
async def test_windowed_stats_and_bucket_totals_stay_consistent(
    repository: TrafficLogRepository,
):
    reference_time = datetime(2026, 3, 22, 0, 0, 0, tzinfo=timezone.utc)

    entries = [
        ("txn-consistency-1", reference_time - timedelta(hours=1), "BLOCKED"),
        ("txn-consistency-2", reference_time - timedelta(hours=2), "THROTTLED"),
        ("txn-consistency-3", reference_time - timedelta(hours=3), "ALLOWED"),
        ("txn-consistency-4", reference_time - timedelta(hours=4), "BLOCKED"),
    ]

    for txn, ts, action in entries:
        await repository.save(
            TrafficLogEntity(
                transaction_id=txn,
                timestamp=ts,
                source_ip="203.0.113.50",
                request_path="/stats-consistency",
                request_method="POST",
                http_request="POST /stats-consistency",
                prediction="SQL Injection" if action != "ALLOWED" else "Normal",
                confidence=0.8,
                confidence_level="HIGH" if action != "ALLOWED" else "LOW",
                inference_latency_ms=2.5,
                action_taken=action,
            )
        )

    summary = await repository.get_stats_summary(
        window="24h",
        reference_time=reference_time,
    )
    buckets = await repository.get_activity_buckets(
        window="24h",
        buckets=24,
        reference_time=reference_time,
    )

    assert summary.total_requests == sum(bucket.total_count for bucket in buckets)
    assert summary.blocked_count == sum(bucket.blocked_count for bucket in buckets)
    assert summary.allowed_count == sum(bucket.allowed_count for bucket in buckets)
    assert summary.throttled_count == sum(bucket.throttled_count for bucket in buckets)


@pytest.mark.asyncio
async def test_windowed_summary_filters_are_strictly_bounded(
    repository: TrafficLogRepository,
):
    reference_time = datetime(2026, 3, 22, 12, 0, 0, tzinfo=timezone.utc)

    # In-window records for a 1h range [11:00, 12:00)
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-window-in-1",
            timestamp=reference_time - timedelta(minutes=30),
            source_ip="198.51.100.30",
            request_path="/api/login",
            request_method="POST",
            http_request="POST /api/login",
            prediction="SQL Injection",
            confidence=0.95,
            confidence_level="HIGH",
            inference_latency_ms=2.1,
            action_taken="BLOCKED",
        )
    )
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-window-in-2",
            timestamp=reference_time - timedelta(minutes=5),
            source_ip="198.51.100.30",
            request_path="/api/search",
            request_method="GET",
            http_request="GET /api/search?q=1",
            prediction="Code Injection",
            confidence=0.82,
            confidence_level="HIGH",
            inference_latency_ms=3.2,
            action_taken="THROTTLED",
        )
    )
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-window-in-3",
            timestamp=reference_time - timedelta(minutes=1),
            source_ip="198.51.100.31",
            request_path="/api/public",
            request_method="GET",
            http_request="GET /api/public",
            prediction="Other Attacks",
            confidence=0.66,
            confidence_level="MEDIUM",
            inference_latency_ms=1.9,
            action_taken="ALLOWED",
        )
    )

    # Out-of-window records that must be excluded by the same [start, end) filter.
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-window-out-old",
            timestamp=reference_time - timedelta(hours=2),
            source_ip="198.51.100.99",
            request_path="/api/admin",
            request_method="GET",
            http_request="GET /api/admin",
            prediction="SQL Injection",
            confidence=0.99,
            confidence_level="HIGH",
            inference_latency_ms=4.8,
            action_taken="BLOCKED",
        )
    )
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-window-out-end-exclusive",
            timestamp=reference_time,
            source_ip="198.51.100.88",
            request_path="/api/end",
            request_method="GET",
            http_request="GET /api/end",
            prediction="SQL Injection",
            confidence=0.91,
            confidence_level="HIGH",
            inference_latency_ms=2.4,
            action_taken="BLOCKED",
        )
    )

    summary = await repository.get_stats_summary(
        window="1h",
        reference_time=reference_time,
    )
    buckets = await repository.get_activity_buckets(
        window="1h",
        buckets=6,
        reference_time=reference_time,
    )

    assert summary.total_requests == 3
    assert summary.blocked_count == 1
    assert summary.throttled_count == 1
    assert summary.allowed_count == 1
    assert summary.total_requests == sum(bucket.total_count for bucket in buckets)
    assert summary.blocked_count == sum(bucket.blocked_count for bucket in buckets)
    assert summary.throttled_count == sum(bucket.throttled_count for bucket in buckets)
    assert summary.allowed_count == sum(bucket.allowed_count for bucket in buckets)
    assert summary.false_positive_count == 1
    assert summary.false_positive_rate == round((1 / 3) * 100, 2)
    assert summary.counts_by_label["SQL Injection"] == 1
    assert summary.counts_by_label["Code Injection"] == 1
    assert summary.counts_by_label["Other Attacks"] == 1
    assert summary.counts_by_label["Normal"] == 0
    assert summary.attack_distribution == {
        "SQL Injection": 1,
        "Code Injection": 1,
        "Other Attacks": 1,
    }

    assert summary.top_source_ips
    assert summary.top_source_ips[0].ip == "198.51.100.30"
    assert summary.top_source_ips[0].count == 2
    assert summary.top_source_ips[0].action == "THROTTLED"

    top_paths = {item.path: item.hits for item in summary.top_targeted_paths}
    assert top_paths == {
        "/api/login": 1,
        "/api/search": 1,
        "/api/public": 1,
    }


@pytest.mark.asyncio
async def test_seven_day_bucket_boundaries_are_deterministic(
    repository: TrafficLogRepository,
):
    reference_time = datetime(2026, 3, 22, 0, 0, 0, tzinfo=timezone.utc)
    buckets = await repository.get_activity_buckets(
        window="7d",
        buckets=24,
        reference_time=reference_time,
    )

    assert len(buckets) == 24
    assert buckets[0].timestamp_start == reference_time - timedelta(days=7)

    expected_step = timedelta(seconds=int(timedelta(days=7).total_seconds()) // 24)
    for idx in range(1, len(buckets)):
        assert (
            buckets[idx].timestamp_start - buckets[idx - 1].timestamp_start
        ) == expected_step


@pytest.mark.asyncio
async def test_get_alert_list_sorts_by_severity_rank(
    repository: TrafficLogRepository,
):
    now = datetime.now(timezone.utc)

    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-severity-high",
            timestamp=now - timedelta(minutes=3),
            source_ip="198.51.100.40",
            request_path="/high",
            request_method="GET",
            http_request="GET /high",
            prediction="SQL Injection",
            confidence=0.95,
            confidence_level="HIGH",
            inference_latency_ms=2.0,
            action_taken="BLOCKED",
        )
    )
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-severity-low",
            timestamp=now - timedelta(minutes=2),
            source_ip="198.51.100.41",
            request_path="/low",
            request_method="GET",
            http_request="GET /low",
            prediction="Normal",
            confidence=0.25,
            confidence_level="LOW",
            inference_latency_ms=2.0,
            action_taken="ALLOWED",
        )
    )
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-severity-medium",
            timestamp=now - timedelta(minutes=1),
            source_ip="198.51.100.42",
            request_path="/medium",
            request_method="GET",
            http_request="GET /medium",
            prediction="Code Injection",
            confidence=0.55,
            confidence_level="MEDIUM",
            inference_latency_ms=2.0,
            action_taken="THROTTLED",
        )
    )

    page = await repository.get_alert_list(
        page=1,
        page_size=10,
        sort_by="severity",
        sort_dir="desc",
        time_range="7d",
    )

    assert [item.confidence_level for item in page.items] == [
        "HIGH",
        "MEDIUM",
        "LOW",
    ]


@pytest.mark.asyncio
async def test_get_stats_summary_reuses_cache_for_same_minute_reference_time(
    repository: TrafficLogRepository,
):
    original_with_own_session = repository._with_own_session
    call_count = 0

    async def counting_with_own_session(coro_factory):
        nonlocal call_count
        call_count += 1
        return await original_with_own_session(coro_factory)

    repository._with_own_session = counting_with_own_session  # type: ignore[assignment]

    first = await repository.get_stats_summary(
        window="24h",
        reference_time=datetime(2026, 3, 22, 12, 34, 5, tzinfo=timezone.utc),
    )
    second = await repository.get_stats_summary(
        window="24h",
        reference_time=datetime(2026, 3, 22, 12, 34, 55, tzinfo=timezone.utc),
    )

    assert first == second
    assert call_count == 6


def test_stats_cache_purges_expired_entries_when_setting_new_values():
    cache = _StatsCache()
    cache._store["expired"] = (datetime.now(timezone.utc).timestamp() - 1, object())

    cache.set("fresh", object())

    assert "expired" not in cache._store
    assert cache.get("fresh") is not None


@pytest.mark.asyncio
async def test_get_alert_list_triage_new_includes_null_and_literal_new(
    repository: TrafficLogRepository,
):
    now = datetime.now(timezone.utc)

    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-triage-null",
            timestamp=now - timedelta(minutes=3),
            source_ip="198.51.100.201",
            request_path="/triage/null",
            request_method="GET",
            http_request="GET /triage/null",
            prediction="SQL Injection",
            confidence=0.91,
            confidence_level="HIGH",
            inference_latency_ms=2.0,
            action_taken="BLOCKED",
            triage_status=None,
        )
    )
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-triage-literal-new",
            timestamp=now - timedelta(minutes=2),
            source_ip="198.51.100.202",
            request_path="/triage/new",
            request_method="GET",
            http_request="GET /triage/new",
            prediction="SQL Injection",
            confidence=0.92,
            confidence_level="HIGH",
            inference_latency_ms=2.1,
            action_taken="BLOCKED",
            triage_status="new",
        )
    )
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-triage-investigating",
            timestamp=now - timedelta(minutes=1),
            source_ip="198.51.100.203",
            request_path="/triage/investigating",
            request_method="GET",
            http_request="GET /triage/investigating",
            prediction="SQL Injection",
            confidence=0.93,
            confidence_level="HIGH",
            inference_latency_ms=2.2,
            action_taken="BLOCKED",
            triage_status="investigating",
        )
    )

    page = await repository.get_alert_list(
        page=1,
        page_size=20,
        time_range="7d",
        triage_status="new",
    )

    assert page.total == 2
    assert {item.transaction_id for item in page.items} == {
        "txn-triage-null",
        "txn-triage-literal-new",
    }


@pytest.mark.asyncio
async def test_get_alert_list_triage_non_new_filters_by_exact_status(
    repository: TrafficLogRepository,
):
    now = datetime.now(timezone.utc)

    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-triage2-null",
            timestamp=now - timedelta(minutes=3),
            source_ip="198.51.100.211",
            request_path="/triage2/null",
            request_method="GET",
            http_request="GET /triage2/null",
            prediction="SQL Injection",
            confidence=0.91,
            confidence_level="HIGH",
            inference_latency_ms=2.0,
            action_taken="BLOCKED",
            triage_status=None,
        )
    )
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-triage2-new",
            timestamp=now - timedelta(minutes=2),
            source_ip="198.51.100.212",
            request_path="/triage2/new",
            request_method="GET",
            http_request="GET /triage2/new",
            prediction="SQL Injection",
            confidence=0.92,
            confidence_level="HIGH",
            inference_latency_ms=2.1,
            action_taken="BLOCKED",
            triage_status="new",
        )
    )
    await repository.save(
        TrafficLogEntity(
            transaction_id="txn-triage2-investigating",
            timestamp=now - timedelta(minutes=1),
            source_ip="198.51.100.213",
            request_path="/triage2/investigating",
            request_method="GET",
            http_request="GET /triage2/investigating",
            prediction="SQL Injection",
            confidence=0.93,
            confidence_level="HIGH",
            inference_latency_ms=2.2,
            action_taken="BLOCKED",
            triage_status="investigating",
        )
    )

    page = await repository.get_alert_list(
        page=1,
        page_size=20,
        time_range="7d",
        triage_status="investigating",
    )

    assert page.total == 1
    assert [item.transaction_id for item in page.items] == [
        "txn-triage2-investigating"
    ]
