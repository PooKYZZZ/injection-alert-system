from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from web_app.infrastructure.database import get_db
from web_app.infrastructure.database import database as db_module
from web_app.infrastructure.database.database import Base
from web_app.presentation.api.routes import get_model_service
from web_app.presentation.app import create_app

INTERNAL_HEADERS = {"Authorization": "Bearer test-secret-key"}


class FakeWafModelService:
    def __init__(self, *, loaded: bool = True):
        self.loaded = loaded
        self.model_version = "triage-model-v1"

    def predict(self, http_request: str):
        return {
            "prediction": "SQL Injection",
            "confidence": 0.91,
            "confidence_tier": "HIGH",
            "inference_latency_ms": 4.2,
            "model_version": self.model_version,
        }


@pytest.fixture
def waf_api_client():
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
    app.dependency_overrides[get_model_service] = lambda: FakeWafModelService()

    original_session_factory = getattr(db_module, "AsyncSessionLocal", None)
    db_module.AsyncSessionLocal = session_factory

    with TestClient(app) as test_client:
        yield test_client, _init_tables

    app.dependency_overrides.clear()
    if original_session_factory is not None:
        db_module.AsyncSessionLocal = original_session_factory

    import asyncio

    asyncio.run(engine.dispose())


def _waf_payload() -> dict:
    return {
        "ingest_source": "modsec_audit_bridge",
        "transaction_id": "waf-txn-001",
        "timestamp": datetime(2026, 3, 24, 10, 0, 0, tzinfo=timezone.utc).isoformat(),
        "source_ip": "203.0.113.10",
        "request_method": "POST",
        "request_path": "/login",
        "query_string": "user=admin",
        "request_headers": {"user-agent": "curl/8.0"},
        "sanitized_body": "' OR 1=1 --",
        "crs_score": 8,
        "crs_rule_ids": ["942100", "949110"],
        "matched_rule_messages": ["SQL Injection Attack Detected via libinjection"],
        "matched_rule_tags": ["attack-sqli", "paranoia-level/1"],
    }


def test_waf_ingest_valid_event_returns_prediction(waf_api_client):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.post(
        "/api/internal/waf-events",
        json=_waf_payload(),
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["alert_id"] is not None
    assert payload["prediction"] == "SQL Injection"
    assert payload["confidence_level"] == "HIGH"
    assert payload["action_taken"] == "BLOCKED"


def test_waf_ingest_missing_token_returns_401(waf_api_client):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.post(
        "/api/internal/waf-events",
        json=_waf_payload(),
    )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_waf_ingest_invalid_payload_returns_422(waf_api_client):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    invalid_payload = _waf_payload()
    invalid_payload.pop("transaction_id")

    response = client.post(
        "/api/internal/waf-events",
        json=invalid_payload,
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 422
