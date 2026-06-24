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
        "timestamp": "2026-03-24T10:00:00Z",
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


def test_waf_ingest_invalid_token_returns_401(waf_api_client):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.post(
        "/api/internal/waf-events",
        json=_waf_payload(),
        headers={"Authorization": "Bearer wrong-secret"},
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


def test_waf_ingest_invalid_timestamp_returns_422(waf_api_client):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    invalid_payload = _waf_payload()
    invalid_payload["timestamp"] = "not-a-timestamp"

    response = client.post(
        "/api/internal/waf-events",
        json=invalid_payload,
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 422


def test_waf_ingest_lookup_returns_stored_event_by_transaction_id(waf_api_client):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    payload = _waf_payload()
    payload["transaction_id"] = "waf-txn-lookup-1"
    payload["source_ip"] = "172.21.0.1"
    payload["request_path"] = "/api/health"
    payload["query_string"] = "id=15%27%20OR%2015%3D15--"
    payload["crs_score"] = 5
    payload["crs_rule_ids"] = ["942100", "949110"]
    payload["matched_rule_messages"] = [
        "SQL Injection Attack Detected via libinjection",
        "Inbound Anomaly Score Exceeded (Total Score: 5)",
    ]
    ingest_response = client.post(
        "/api/internal/waf-events",
        json=payload,
        headers=INTERNAL_HEADERS,
    )
    assert ingest_response.status_code == 200

    response = client.get(
        "/api/internal/waf-events/waf-txn-lookup-1",
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["transaction_id"] == "waf-txn-lookup-1"
    assert body["alert_id"] is not None
    assert body["ingest_source"] == "modsec_audit_bridge"
    assert body["prediction"] == "SQL Injection"
    assert body["action_taken"] == "BLOCKED"
    for key in ("source_ip", "request_path", "query_string"):
        assert key in body
        assert body[key] is not None
    assert body["source_ip"] == "172.21.0.1"
    assert body["request_path"] == "/api/health"
    assert body["query_string"] == "id=15%27%20OR%2015%3D15--"
    assert body["crs_score"] == 5
    assert body["crs_rule_ids"] == ["942100", "949110"]
    assert body["matched_rule_messages"] == [
        "SQL Injection Attack Detected via libinjection",
        "Inbound Anomaly Score Exceeded (Total Score: 5)",
    ]
    assert body["matched_rule_tags"] == ["attack-sqli", "paranoia-level/1"]


def test_waf_ingest_lookup_returns_not_found_for_unknown_transaction_id(
    waf_api_client,
):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.get(
        "/api/internal/waf-events/waf-txn-missing",
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is False
    assert body["transaction_id"] == "waf-txn-missing"
    assert body["alert_id"] is None


def test_waf_ingest_duplicate_transaction_id_returns_existing_alert(
    waf_api_client,
):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    payload = _waf_payload()
    payload["transaction_id"] = "waf-txn-dupe-1"

    first = client.post(
        "/api/internal/waf-events",
        json=payload,
        headers=INTERNAL_HEADERS,
    )
    second = client.post(
        "/api/internal/waf-events",
        json=payload,
        headers=INTERNAL_HEADERS,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["alert_id"] == first.json()["alert_id"]
    assert second.json()["prediction"] == first.json()["prediction"]

    lookup = client.get(
        "/api/internal/waf-events/waf-txn-dupe-1",
        headers=INTERNAL_HEADERS,
    )
    assert lookup.status_code == 200
    assert lookup.json()["found"] is True
    assert lookup.json()["alert_id"] == first.json()["alert_id"]
