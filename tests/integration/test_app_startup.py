from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from web_app.config import Settings
from web_app.infrastructure.database.database import Base
from web_app.presentation import app as app_module
from web_app.presentation.app import create_app
from web_app.presentation.api.routes import get_model_service
from web_app.infrastructure.database import get_db

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

    with TestClient(app) as test_client:
        yield test_client, session_factory, _init_tables

    app.dependency_overrides.clear()
    import asyncio
    asyncio.run(engine.dispose())


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
        assert app.state.model is mock_service


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
            raise AssertionError("mock loader should not run for explicit artifact path")

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
        assert app.state.model is app.state.model_service


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
        "confidence_thresholds": {
            "low": 0.5,
            "high": 0.8,
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
    assert response.json() == {
        "total_requests": 0,
        "counts_by_label": {
            "SQL Injection": 0,
            "Code Injection": 0,
            "Other Attacks": 0,
            "Normal": 0,
        },
        "avg_inference_latency_ms": 0.0,
    }


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
    assert payload["items"][0]["payload_snippet"] == "POST /login username=admin' OR '1'='1"


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
    assert list_payload["items"][0]["payload_snippet"] == "GET /legacy?q=test"

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["id"] == 1
    assert detail_payload["request_path"] is None
    assert detail_payload["request_method"] is None
    assert detail_payload["crs_score"] is None
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
