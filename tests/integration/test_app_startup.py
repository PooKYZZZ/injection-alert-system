from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from web_app.config import Settings
from web_app.infrastructure.database import database as db_module
from web_app.infrastructure.database import get_db
from web_app.infrastructure.database.database import Base, TrafficLog
from web_app.presentation import app as app_module
from web_app.presentation.api.routes import get_model_service
from web_app.presentation.app import create_app

INTERNAL_HEADERS = {"Authorization": "Bearer test-secret-key"}


def _make_settings(model_registry_path: Path, app_env: str) -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite://",
        app_env=app_env,
        model_path="unused",
        model_registry_path=str(model_registry_path),
        api_secret_key="test-secret",
    )


async def _fake_init_db() -> None:
    return None


class FakeModelHealthService:
    def __init__(
        self,
        *,
        model_version: str = "mock-model-service",
        loaded: bool = True,
        is_mock: bool = True,
        avg_inference_latency_ms: float = 0.0,
        total_processed: int = 0,
        confidence_thresholds: dict[str, float] | None = None,
        eval_metadata: dict[str, object] | None = None,
    ):
        self.model_version = model_version
        self.loaded = loaded
        self.is_mock = is_mock
        self.avg_inference_latency_ms = avg_inference_latency_ms
        self.total_processed = total_processed
        self.confidence_thresholds = confidence_thresholds or {
            "low": 0.5,
            "high": 0.8,
        }
        self.eval_metadata = eval_metadata or {}


class FakeTriageModelService(FakeModelHealthService):
    def __init__(self, *, loaded: bool = True):
        super().__init__(
            model_version="triage-model-v1",
            loaded=loaded,
            is_mock=False,
        )
        self.predict_calls = 0

    def predict(self, http_request: str):
        self.predict_calls += 1
        return {
            "prediction": "SQL Injection",
            "confidence": 0.91,
            "confidence_tier": "HIGH",
            "inference_latency_ms": 4.2,
            "model_version": self.model_version,
        }


def _triage_payload(transaction_id: str) -> dict:
    return {
        "transaction_id": transaction_id,
        "timestamp": "2026-03-15T08:00:00Z",
        "source_ip": "203.0.113.55",
        "request_method": "POST",
        "request_uri": "/login",
        "request_headers": {
            "Host": "lares.test",
            "User-Agent": "pytest",
        },
        "request_body": "username=admin&password=pass",
        "http_request": "POST /login HTTP/1.1",
        "crs_score": 9,
        "crs_rule_ids": ["942100", "942110"],
    }


@pytest.fixture
def api_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def _override_get_db():
        async with session_factory() as session:
            yield session

    async def _init_tables() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    app = create_app()
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_model_service] = lambda: FakeModelHealthService()

    original_session_factory = getattr(db_module, "AsyncSessionLocal", None)
    db_module.AsyncSessionLocal = session_factory

    with TestClient(app) as test_client:
        yield test_client, session_factory, _init_tables

    app.dependency_overrides.clear()
    if original_session_factory is not None:
        db_module.AsyncSessionLocal = original_session_factory
    import asyncio

    asyncio.run(engine.dispose())


async def _count_traffic_logs(session_factory) -> int:
    async with session_factory() as session:
        result = await session.execute(select(func.count(TrafficLog.id)))
        return int(result.scalar_one())


def test_startup_fails_fast_when_artifact_missing_in_production(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    missing_path = tmp_path / "missing-run"

    monkeypatch.setattr(
        app_module,
        "get_settings",
        lambda: _make_settings(missing_path, "production"),
    )
    monkeypatch.setattr(app_module, "init_db", _fake_init_db)

    with pytest.raises(RuntimeError, match="MODEL_REGISTRY_PATH"):
        with TestClient(app_module.create_app()):
            pass


def test_startup_uses_mock_service_when_artifact_missing_in_testing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    missing_path = tmp_path / "missing-run"
    mock_service = object()

    class FakeModelService:
        def __init__(self, settings):
            raise AssertionError("real loader should not run for missing test artifact")

        @classmethod
        def create_mock(cls):
            return mock_service

    monkeypatch.setattr(
        app_module,
        "get_settings",
        lambda: _make_settings(missing_path, "testing"),
    )
    monkeypatch.setattr(app_module, "init_db", _fake_init_db)
    monkeypatch.setattr(app_module, "ModelService", FakeModelService)

    app = app_module.create_app()
    with TestClient(app):
        assert app.state.model_service is mock_service


def test_startup_stores_real_model_service_on_app_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    run_dir = tmp_path / "distilbert_v3_907k_cleaned_20260312_133755"
    run_dir.mkdir()
    (run_dir / "best_distilbert_ckpt.pt").write_bytes(b"checkpoint")

    class FakeModelService:
        def __init__(self, settings):
            self.settings = settings
            self.model_version = "distilbert_v3_907k_cleaned_20260312_133755"

        @classmethod
        def create_mock(cls):
            raise AssertionError(
                "mock loader should not run for explicit artifact path"
            )

    monkeypatch.setattr(
        app_module,
        "get_settings",
        lambda: _make_settings(run_dir, "production"),
    )
    monkeypatch.setattr(app_module, "init_db", _fake_init_db)
    monkeypatch.setattr(app_module, "ModelService", FakeModelService)

    app = app_module.create_app()
    with TestClient(app):
        assert isinstance(app.state.model_service, FakeModelService)


@pytest.mark.parametrize("app_env", ["production", "staging"])
def test_startup_skips_init_db_in_production_like_environments(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    app_env: str,
):
    run_dir = tmp_path / "distilbert_v3_907k_cleaned_20260312_133755"
    run_dir.mkdir()
    (run_dir / "best_distilbert_ckpt.pt").write_bytes(b"checkpoint")

    class FakeModelService:
        def __init__(self, settings):
            self.settings = settings

    async def fail_init_db() -> None:
        raise AssertionError("init_db should not run in production-like environments")

    monkeypatch.setattr(
        app_module,
        "get_settings",
        lambda: _make_settings(run_dir, app_env),
    )
    monkeypatch.setattr(app_module, "init_db", fail_init_db)
    monkeypatch.setattr(app_module, "ModelService", FakeModelService)

    with TestClient(app_module.create_app()):
        pass


def test_ml_health_returns_degraded_when_mock_model_active(api_client):
    client, _, _ = api_client

    response = client.get(
        "/api/ml-health",
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == {
        "model_version": "mock-model-service",
        "loaded": True,
        "status": "degraded",
        "avg_inference_latency_ms": 0.0,
        "total_processed": 0,
        "drift_detected": False,
        "drift_score": None,  # Drift unavailable when DB not initialized
        "confidence_thresholds": {
            "low": 0.5,
            "high": 0.8,
        },
        # Optional eval metadata defaults when not available
        "macro_f1": None,
        "ece": None,
        "per_class_f1": {},
        "calibration_bins": [],
        "prediction_distribution": {},
        "queue": {
            "enabled": True,
            "max_size": 100,
            "depth": 0,
            "available_capacity": 100,
            "worker_count": 1,
            "worker_running": True,
            "total_enqueued": 0,
            "total_processed": 0,
            "total_failed": 0,
            "overflow_count": 0,
            "last_error": None,
            "last_error_at": None,
            "last_processed_at": None,
        },
    }


def test_unknown_alert_id_returns_404(api_client):
    client, _, init_tables = api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.get(
        "/api/alerts/9999",
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Alert not found"}


def test_stats_returns_zeroed_response_for_empty_table(api_client):
    client, _, init_tables = api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.get(
        "/api/stats",
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200
    response_data = response.json()
    # Verify core stats
    assert response_data["total_requests"] == 0
    assert response_data["counts_by_label"]["SQL Injection"] == 0
    assert response_data["avg_inference_latency_ms"] == 0.0
    assert response_data["blocked_count"] == 0
    assert response_data["avg_confidence"] is None
    # Verify activity_buckets is returned with 24 empty buckets
    assert "activity_buckets" in response_data
    assert len(response_data["activity_buckets"]) == 24
    # All buckets should have zero counts when there's no data
    for bucket in response_data["activity_buckets"]:
        assert bucket["total_count"] == 0
        assert bucket["blocked_count"] == 0


def test_alert_list_returns_pagination_shape(api_client):
    client, session_factory, init_tables = api_client
    import asyncio

    from web_app.infrastructure.database.database import TrafficLog

    async def _seed() -> None:
        await init_tables()
        async with session_factory() as session:
            session.add(
                TrafficLog(
                    transaction_id="txn-list-1",
                    source_ip="192.168.1.10",
                    request_path="/login",
                    request_method="POST",
                    http_request="POST /login username=admin' OR '1'='1",
                    prediction="SQL Injection",
                    confidence=0.97,
                    confidence_level="HIGH",
                    inference_latency_ms=11.2,
                    action_taken="BLOCKED",
                    crs_score=9,
                    crs_rule_ids=["942100", "942110"],
                    analyst_label="SQL Injection",
                    labeled_at=datetime(2026, 3, 15, 0, 5, tzinfo=timezone.utc),
                    labeled_by="analyst@lares.test",
                )
            )
            await session.commit()

    asyncio.run(_seed())

    response = client.get(
        "/api/alerts?page=1&page_size=20",
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["page"] == 1
    assert payload["page_size"] == 20
    assert isinstance(payload["items"], list)
    assert payload["items"][0]["id"] == 1
    assert (
        payload["items"][0]["payload_snippet"]
        == "POST /login username=admin' OR '1'='1"
    )
    assert payload["items"][0]["crs_rule_ids"] == ["942100", "942110"]
    assert payload["items"][0]["analyst_label"] == "SQL Injection"
    assert payload["items"][0]["labeled_by"] == "analyst@lares.test"
    assert payload["items"][0]["labeled_at"] == "2026-03-15T00:05:00Z"


def test_alert_read_endpoints_tolerate_sparse_legacy_rows(api_client):
    client, session_factory, init_tables = api_client
    import asyncio

    from web_app.infrastructure.database.database import TrafficLog

    async def _seed_sparse_row() -> None:
        await init_tables()
        async with session_factory() as session:
            session.add(
                TrafficLog(
                    transaction_id="txn-legacy-1",
                    source_ip="203.0.113.7",
                    http_request="GET /legacy?q=test",
                    prediction="Normal",
                    confidence=0.41,
                    confidence_level="LOW",
                    action_taken="ALLOWED",
                )
            )
            await session.commit()

    asyncio.run(_seed_sparse_row())

    headers = INTERNAL_HEADERS
    list_response = client.get(
        "/api/alerts?page=1&page_size=20&search=203.0.113.7",
        headers=headers,
    )
    detail_response = client.get("/api/alerts/1", headers=headers)

    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 1
    assert list_payload["items"][0]["id"] == 1
    assert list_payload["items"][0]["request_path"] is None
    assert list_payload["items"][0]["request_method"] is None
    assert list_payload["items"][0]["crs_score"] is None
    assert list_payload["items"][0]["crs_rule_ids"] is None
    assert list_payload["items"][0]["analyst_label"] is None
    assert list_payload["items"][0]["labeled_at"] is None
    assert list_payload["items"][0]["labeled_by"] is None
    assert list_payload["items"][0]["payload_snippet"] == "GET /legacy?q=test"

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == 1
    assert detail_payload["request_path"] is None
    assert detail_payload["request_method"] is None
    assert detail_payload["crs_score"] is None
    assert detail_payload["crs_rule_ids"] is None
    assert detail_payload["analyst_label"] is None
    assert detail_payload["labeled_at"] is None
    assert detail_payload["labeled_by"] is None
    assert detail_payload["payload_snippet"] == "GET /legacy?q=test"


def test_auth_missing_token_returns_401(api_client):
    client, _, init_tables = api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.get("/api/stats")

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_auth_wrong_scheme_returns_401(api_client):
    client, _, init_tables = api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.get(
        "/api/stats",
        headers={"Authorization": "Basic test-secret"},
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_auth_invalid_token_returns_401(api_client):
    client, _, init_tables = api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.get(
        "/api/stats",
        headers={"Authorization": "Bearer wrong-secret"},
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_auth_valid_token_allows_access(api_client):
    client, _, init_tables = api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.get(
        "/api/stats",
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200


def test_auth_api_health_endpoint_is_public(api_client):
    client, _, _ = api_client

    response = client.get("/api/health")

    assert response.status_code == 200


def test_triage_missing_token_returns_401(api_client):
    client, _, init_tables = api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.post("/api/triage", json=_triage_payload("txn-auth-missing"))

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_triage_valid_token_allows_ingest(api_client):
    client, _, init_tables = api_client
    import asyncio

    asyncio.run(init_tables())
    service = FakeTriageModelService()
    client.app.state.model_service = service

    response = client.post(
        "/api/triage",
        json=_triage_payload("txn-auth-valid"),
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["prediction"] == "SQL Injection"
    assert service.predict_calls == 1


def test_triage_returns_503_when_model_not_ready(api_client):
    client, _, init_tables = api_client
    import asyncio

    asyncio.run(init_tables())
    service = FakeTriageModelService(loaded=False)
    client.app.state.model_service = service

    response = client.post(
        "/api/triage",
        json=_triage_payload("txn-model-down"),
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Model service is unavailable or not ready"
    assert service.predict_calls == 0


def test_triage_duplicate_ingest_is_idempotent(api_client):
    client, session_factory, init_tables = api_client
    import asyncio

    asyncio.run(init_tables())
    service = FakeTriageModelService()
    client.app.state.model_service = service

    first = client.post(
        "/api/triage",
        json=_triage_payload("txn-dup-1"),
        headers=INTERNAL_HEADERS,
    )
    second = client.post(
        "/api/triage",
        json=_triage_payload("txn-dup-1"),
        headers=INTERNAL_HEADERS,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["alert_id"] == second.json()["alert_id"]
    assert first.json() == second.json()
    assert service.predict_calls == 1
    assert asyncio.run(_count_traffic_logs(session_factory)) == 1


def test_triage_processing_row_returns_409_with_retry_after(api_client):
    client, session_factory, init_tables = api_client
    import asyncio

    async def _seed_processing() -> None:
        await init_tables()
        async with session_factory() as session:
            session.add(
                TrafficLog(
                    transaction_id="txn-processing-1",
                    created_at=datetime.now(timezone.utc),
                    timestamp=datetime.now(timezone.utc),
                    source_ip="203.0.113.55",
                    request_path="/login",
                    request_method="POST",
                    http_request="POST /login HTTP/1.1",
                    crs_score=9,
                    crs_rule_ids=["942100"],
                    status="PROCESSING",
                    lease_expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
                    processing_owner_token="owner-old",
                    processing_attempt=1,
                )
            )
            await session.commit()

    asyncio.run(_seed_processing())
    service = FakeTriageModelService()
    client.app.state.model_service = service

    response = client.post(
        "/api/triage",
        json=_triage_payload("txn-processing-1"),
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 409
    assert response.headers["Retry-After"] == "5"
    assert service.predict_calls == 0


def test_triage_expired_processing_lease_is_reclaimed_and_completes(api_client):
    """An expired PROCESSING lease is reclaimed and completes successfully."""
    client, session_factory, init_tables = api_client
    import asyncio

    async def _seed_expired_processing() -> None:
        await init_tables()
        async with session_factory() as session:
            session.add(
                TrafficLog(
                    transaction_id="txn-stale-1",
                    created_at=datetime.now(timezone.utc) - timedelta(seconds=31),
                    timestamp=datetime.now(timezone.utc),
                    source_ip="203.0.113.55",
                    request_path="/login",
                    request_method="POST",
                    http_request="POST /login HTTP/1.1",
                    crs_score=9,
                    crs_rule_ids=["942100"],
                    status="PROCESSING",
                    lease_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
                    processing_owner_token="owner-old",
                    processing_attempt=1,
                )
            )
            await session.commit()

    asyncio.run(_seed_expired_processing())
    service = FakeTriageModelService()
    client.app.state.model_service = service

    response = client.post(
        "/api/triage",
        json=_triage_payload("txn-stale-1"),
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["alert_id"] is not None
    assert response.json()["prediction"] == "SQL Injection"
    assert service.predict_calls == 1


def test_processing_placeholder_rows_do_not_appear_in_alerts(api_client):
    client, session_factory, init_tables = api_client
    import asyncio

    async def _seed_rows() -> None:
        await init_tables()
        async with session_factory() as session:
            session.add_all(
                [
                    TrafficLog(
                        transaction_id="txn-completed-visible",
                        created_at=datetime.now(timezone.utc),
                        timestamp=datetime.now(timezone.utc),
                        source_ip="203.0.113.10",
                        request_path="/visible",
                        request_method="GET",
                        http_request="GET /visible HTTP/1.1",
                        prediction="Normal",
                        confidence=0.44,
                        confidence_level="LOW",
                        action_taken="ALLOWED",
                        status="COMPLETED",
                    ),
                    TrafficLog(
                        transaction_id="txn-processing-hidden",
                        created_at=datetime.now(timezone.utc),
                        timestamp=datetime.now(timezone.utc),
                        source_ip="203.0.113.11",
                        request_path="/hidden",
                        request_method="POST",
                        http_request="POST /hidden HTTP/1.1",
                        crs_score=9,
                        crs_rule_ids=["942100"],
                        status="PROCESSING",
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed_rows())

    response = client.get("/api/alerts?page=1&page_size=20", headers=INTERNAL_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0]["request_path"] == "/visible"


def test_processing_placeholder_rows_do_not_count_in_stats(api_client):
    client, session_factory, init_tables = api_client
    import asyncio

    async def _seed_rows() -> None:
        await init_tables()
        async with session_factory() as session:
            session.add_all(
                [
                    TrafficLog(
                        transaction_id="txn-stats-visible",
                        created_at=datetime.now(timezone.utc),
                        timestamp=datetime.now(timezone.utc),
                        source_ip="203.0.113.12",
                        request_path="/stats-visible",
                        request_method="GET",
                        http_request="GET /stats-visible HTTP/1.1",
                        prediction="SQL Injection",
                        confidence=0.92,
                        confidence_level="HIGH",
                        inference_latency_ms=2.5,
                        action_taken="BLOCKED",
                        status="COMPLETED",
                    ),
                    TrafficLog(
                        transaction_id="txn-stats-hidden",
                        created_at=datetime.now(timezone.utc),
                        timestamp=datetime.now(timezone.utc),
                        source_ip="203.0.113.13",
                        request_path="/stats-hidden",
                        request_method="POST",
                        http_request="POST /stats-hidden HTTP/1.1",
                        crs_score=8,
                        crs_rule_ids=["942110"],
                        status="PROCESSING",
                    ),
                ]
            )
            await session.commit()

    asyncio.run(_seed_rows())

    response = client.get("/api/stats", headers=INTERNAL_HEADERS)

    assert response.status_code == 200
    response_data = response.json()
    # Verify core stats
    assert response_data["total_requests"] == 1
    assert response_data["counts_by_label"]["SQL Injection"] == 1
    assert response_data["avg_inference_latency_ms"] == 2.5
    assert response_data["blocked_count"] == 1
    assert response_data["avg_confidence"] == 0.92
    # Verify activity_buckets is returned with 24 buckets
    assert "activity_buckets" in response_data
    assert len(response_data["activity_buckets"]) == 24
