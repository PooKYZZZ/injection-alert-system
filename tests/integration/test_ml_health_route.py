from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from web_app.infrastructure.database import get_db
from web_app.infrastructure.database import database as db_module
from web_app.infrastructure.database.database import Base
from web_app.presentation.api.routes import get_model_service
from web_app.presentation.app import create_app

INTERNAL_HEADERS = {"Authorization": "Bearer test-secret-key"}


class FakeModelHealthService:
    model_version = "mock-model-service"
    loaded = True
    is_mock = True
    avg_inference_latency_ms = 12.5
    total_processed = 7
    confidence_thresholds = {"low": 0.5, "high": 0.8}
    eval_metadata = {}


@pytest.fixture
def ml_health_client():
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

    import asyncio

    asyncio.run(_init_tables())
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    if original_session_factory is not None:
        db_module.AsyncSessionLocal = original_session_factory

    asyncio.run(engine.dispose())


def test_ml_health_returns_existing_fields(ml_health_client):
    response = ml_health_client.get("/api/ml-health", headers=INTERNAL_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    for field in (
        "model_version",
        "loaded",
        "status",
        "avg_inference_latency_ms",
        "total_processed",
        "drift_detected",
        "drift_score",
        "confidence_thresholds",
        "macro_f1",
        "ece",
        "per_class_f1",
        "calibration_bins",
        "prediction_distribution",
    ):
        assert field in payload


def test_ml_health_includes_queue_health_fields(ml_health_client):
    response = ml_health_client.get("/api/ml-health", headers=INTERNAL_HEADERS)

    assert response.status_code == 200
    queue = response.json()["queue"]
    assert set(queue) == {
        "enabled",
        "max_size",
        "depth",
        "available_capacity",
        "worker_count",
        "worker_running",
        "total_enqueued",
        "total_processed",
        "total_failed",
        "overflow_count",
        "last_error",
        "last_error_at",
        "last_processed_at",
    }
