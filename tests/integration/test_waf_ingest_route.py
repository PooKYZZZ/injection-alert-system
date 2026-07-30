import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import web_app.presentation.api.routes as routes_module
from scripts.modsecurity_replay_harness import (
    build_waf_ingest_payload,
    detect_modsecurity_events,
    normalize_sample_row,
)
from web_app.application.waf_event_fingerprint import build_waf_event_fingerprint
from web_app.application.waf_event_sanitizer import sanitize_waf_event
from web_app.domain.source_address import SourceProvenance
from web_app.infrastructure.database import database as db_module
from web_app.infrastructure.database import get_db
from web_app.infrastructure.database.database import Base, TrafficLog
from web_app.presentation.api.routes import (
    get_enforcement_repository,
    get_inference_queue,
    get_model_service,
    get_waf_state_repository,
)
from web_app.presentation.app import create_app

INTERNAL_HEADERS = {"Authorization": "Bearer test-secret-key"}
WAF_HEADERS = {
    "Authorization": "Bearer test-waf-ingest-key-at-least-32-characters"
}


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


class CriticalWafModelService(FakeWafModelService):
    def predict(self, http_request: str):
        return {
            "prediction": "SQL Injection",
            "confidence": 0.97,
            "confidence_tier": "CRITICAL",
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


async def _count_traffic_logs(session_factory) -> int:
    async with session_factory() as session:
        result = await session.execute(select(func.count(TrafficLog.id)))
        return int(result.scalar_one())


def _waf_payload() -> dict:
    return {
        "ingest_source": "modsec_audit_bridge",
        "transaction_id": "waf-txn-001",
        "timestamp": "2026-03-24T10:00:00Z",
        "source_ip": "203.0.113.10",
        "source_provenance": "DIRECT_REMOTE_ADDR",
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


def _structured_events(caplog, event_name):
    return [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
        and json.loads(record.getMessage()).get("event") == event_name
    ]


def _payload_fingerprint(payload: dict) -> str:
    sanitized = sanitize_waf_event(
        {
            "request_headers": payload.get("request_headers") or {},
            "sanitized_body": payload.get("sanitized_body"),
        }
    )
    return build_waf_event_fingerprint(
        source_event_timestamp=datetime.fromisoformat(
            payload["timestamp"].replace("Z", "+00:00")
        ),
        source_ip=payload.get("source_ip"),
        source_provenance=SourceProvenance(payload["source_provenance"]),
        cf_connecting_ip_matches_client_ip=payload.get(
            "cf_connecting_ip_matches_client_ip"
        ),
        request_method=payload["request_method"],
        request_path=payload["request_path"],
        query_string=payload.get("query_string"),
        request_headers=sanitized.get("request_headers") or {},
        sanitized_body=sanitized.get("sanitized_body"),
        crs_score=payload["crs_score"],
        crs_rule_ids=payload["crs_rule_ids"],
        ingest_source=payload["ingest_source"],
        matched_rule_messages=payload.get("matched_rule_messages"),
        matched_rule_tags=payload.get("matched_rule_tags"),
    )


def test_waf_ingest_valid_event_returns_prediction(waf_api_client, caplog):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/internal/waf-events",
            json=_waf_payload(),
            headers={
                **WAF_HEADERS,
                "X-Request-ID": "waf-request-001",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["alert_id"] is not None
    assert payload["prediction"] == "SQL Injection"
    assert payload["confidence_level"] == "HIGH"
    assert payload["action_taken"] == "BLOCKED"
    received = _structured_events(caplog, "waf_ingest.received")[-1]
    completed = _structured_events(caplog, "waf_ingest.completed")[-1]
    request_completed = _structured_events(caplog, "request.completed")[-1]
    assert received["request_id"] == "waf-request-001"
    assert received["transaction_id"] == "waf-txn-001"
    assert received["request_path"] == "/login"
    assert received["request_method"] == "POST"
    assert received["crs_rule_count"] == 2
    assert completed["request_id"] == "waf-request-001"
    assert completed["transaction_id"] == "waf-txn-001"
    assert completed["alert_id"] == payload["alert_id"]
    assert completed["prediction"] == "SQL Injection"
    assert completed["confidence_tier"] == "HIGH"
    assert completed["action_taken"] == "BLOCKED"
    assert completed["model_version"] == "triage-model-v1"
    assert request_completed["route"] == "/api/internal/waf-events"
    assert "test-secret-key" not in caplog.text
    assert "' OR 1=1 --" not in caplog.text


def test_shadow_persistence_starts_after_inference_queue_releases_worker(
    waf_api_client,
    monkeypatch,
):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())
    monkeypatch.setenv("ENFORCEMENT_MODE", "shadow")
    monkeypatch.setenv(
        "ENFORCEMENT_CHECK_API_KEY", "test-enforcement-key-at-least-32-characters"
    )
    from web_app.config import get_settings

    get_settings.cache_clear()
    events: list[str] = []

    class TrackingQueue:
        def health(self):
            return {"depth": 0}

        async def submit(self, coro_factory):
            events.append("queue_started")
            result = await coro_factory()
            events.append("queue_released")
            return result

    class TrackingEnforcementRepository:
        async def insert_if_absent(self, recommendation):
            events.append("shadow_persistence")
            return True

    client.app.dependency_overrides[get_inference_queue] = lambda: TrackingQueue()
    client.app.dependency_overrides[get_enforcement_repository] = (
        lambda: TrackingEnforcementRepository()
    )

    payload = _waf_payload()
    payload["timestamp"] = datetime.now(timezone.utc).isoformat()
    payload["request_path"] = "/records/search"
    response = client.post(
        "/api/internal/waf-events",
        json=payload,
        headers=WAF_HEADERS,
    )

    assert response.status_code == 200
    assert events == ["queue_started", "queue_released", "shadow_persistence"]


def test_critical_pr7_ingest_uses_atomic_writer_without_generic_double_write(
    waf_api_client, monkeypatch, caplog
):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())
    settings = routes_module.get_settings().model_copy(
        update={
            "enforcement_mode": "enforce",
            "pr7_critical_waf_mutation_enabled": True,
            "pr7_waf_capacity": 64,
        }
    )
    monkeypatch.setattr(routes_module, "get_settings", lambda: settings)

    class ExplodingGenericRepository:
        async def insert_if_absent(self, recommendation):
            raise AssertionError("generic recommendation writer must not run")

    class RecordingWafStateRepository:
        def __init__(self):
            self.calls: list[dict[str, object]] = []

        async def record_critical_waf_recommendation(self, **kwargs):
            self.calls.append(kwargs)
            from web_app.application.post_triage_enforcement import WafMutationOutcome

            return WafMutationOutcome("ACTIVATED", 17, 4, True)

    waf_repository = RecordingWafStateRepository()
    client.app.dependency_overrides[get_model_service] = (
        lambda: CriticalWafModelService()
    )
    client.app.dependency_overrides[get_enforcement_repository] = (
        lambda: ExplodingGenericRepository()
    )
    client.app.dependency_overrides[get_waf_state_repository] = (
        lambda: waf_repository
    )
    payload = _waf_payload()
    payload.update(
        {
            "transaction_id": "waf-txn-pr7-coordinator",
            "request_path": "/records/search",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/internal/waf-events",
            json=payload,
            headers=WAF_HEADERS,
        )

    assert response.status_code == 200
    assert response.json()["confidence_level"] == "CRITICAL"
    assert len(waf_repository.calls) == 1
    event = _structured_events(
        caplog, "enforcement.post_triage_dispatch_completed"
    )[-1]
    assert event["route"] == "PR7"
    assert event["category"] == "ACTIVATED"
    assert event["revision"] == 4
    assert event["state_changed"] is True


def test_pr7_mutation_failure_keeps_successful_ingest_response(
    waf_api_client, monkeypatch, caplog
):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())
    settings = routes_module.get_settings().model_copy(
        update={
            "enforcement_mode": "enforce",
            "pr7_critical_waf_mutation_enabled": True,
        }
    )
    monkeypatch.setattr(routes_module, "get_settings", lambda: settings)

    class FailingWafStateRepository:
        async def record_critical_waf_recommendation(self, **kwargs):
            raise RuntimeError("database failure")

    client.app.dependency_overrides[get_model_service] = (
        lambda: CriticalWafModelService()
    )
    client.app.dependency_overrides[get_waf_state_repository] = (
        lambda: FailingWafStateRepository()
    )
    payload = _waf_payload()
    payload.update(
        {
            "transaction_id": "waf-txn-pr7-failure-isolated",
            "request_path": "/records/search",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )

    with caplog.at_level(logging.WARNING):
        response = client.post(
            "/api/internal/waf-events",
            json=payload,
            headers=WAF_HEADERS,
        )

    assert response.status_code == 200
    assert response.json()["alert_id"] is not None
    event = _structured_events(
        caplog, "enforcement.post_triage_dispatch_failed"
    )[-1]
    assert event["transaction_id"] == "waf-txn-pr7-failure-isolated"
    assert event["error_type"] == "RuntimeError"
    assert "database failure" not in caplog.text


def test_waf_ingest_queue_full_returns_503_with_retry_after(
    waf_api_client, caplog
):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    class FullQueue:
        def health(self):
            return {"depth": 100}

        async def submit(self, coro_factory):
            from web_app.application.inference_queue import InferenceQueueFullError

            raise InferenceQueueFullError("full")

    client.app.dependency_overrides[get_inference_queue] = lambda: FullQueue()

    with caplog.at_level(logging.WARNING):
        response = client.post(
            "/api/internal/waf-events",
            json=_waf_payload(),
            headers={
                **WAF_HEADERS,
                "X-Request-ID": "waf-queue-full-request",
            },
        )

    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == "waf-queue-full-request"
    assert response.headers["Retry-After"] == "5"
    assert response.json()["detail"] == "Inference queue is full"
    event = _structured_events(caplog, "waf_ingest.queue_full")[-1]
    assert event["request_id"] == "waf-queue-full-request"
    assert event["transaction_id"] == "waf-txn-001"
    assert event["queue_depth"] == 100
    assert event["status_code"] == 503
    assert "test-secret-key" not in caplog.text


def test_waf_ingest_model_not_ready_is_logged(waf_api_client, caplog):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    class UnavailableQueue:
        def health(self):
            return {"depth": 0}

        async def submit(self, coro_factory):
            from web_app.application.triage_use_case import ModelNotReadyError

            raise ModelNotReadyError("model unavailable")

    client.app.dependency_overrides[get_inference_queue] = lambda: UnavailableQueue()

    with caplog.at_level(logging.WARNING):
        response = client.post(
            "/api/internal/waf-events",
            json=_waf_payload(),
            headers=WAF_HEADERS,
        )

    assert response.status_code == 503
    event = _structured_events(caplog, "waf_ingest.model_not_ready")[-1]
    assert event["transaction_id"] == "waf-txn-001"
    assert event["status_code"] == 503


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


def test_general_internal_key_cannot_submit_waf_event(waf_api_client):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.post(
        "/api/internal/waf-events",
        json=_waf_payload(),
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 401


def test_waf_key_cannot_read_waf_event_lookup(waf_api_client):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    response = client.get(
        "/api/internal/waf-events/missing",
        headers=WAF_HEADERS,
    )

    assert response.status_code == 401


def test_waf_ingest_invalid_payload_returns_422(waf_api_client):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    invalid_payload = _waf_payload()
    invalid_payload.pop("transaction_id")

    response = client.post(
        "/api/internal/waf-events",
        json=invalid_payload,
        headers=WAF_HEADERS,
    )

    assert response.status_code == 422


def test_waf_ingest_invalid_timestamp_is_canonicalized_to_null(waf_api_client):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())

    invalid_payload = _waf_payload()
    invalid_payload["timestamp"] = "not-a-timestamp"

    response = client.post(
        "/api/internal/waf-events",
        json=invalid_payload,
        headers=WAF_HEADERS,
    )

    assert response.status_code == 200


def test_replay_generated_payload_is_accepted_by_real_waf_route(waf_api_client):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())
    replay = normalize_sample_row(
        {
            "request_http_method": "GET",
            "request_http_request": "/replay?id=1",
        },
        replay_tx="tx-route-replay",
    )
    logs = (
        'modsecurity-1 | {"transaction":{"client_ip":"::ffff:203.0.113.21",'
        '"unique_id":"route-replay-1","request":{"headers":'
        '{"X-Replay-Tx":"tx-route-replay"}},"messages":'
        '[{"details":{"ruleId":"942100"},"message":"SQL Injection"}]}}'
    )
    payload = build_waf_ingest_payload(
        replay,
        detect_modsecurity_events(logs, replay_tx="tx-route-replay"),
    )

    response = client.post(
        "/api/internal/waf-events",
        json=payload,
        headers=WAF_HEADERS,
    )

    assert response.status_code == 200
    assert response.status_code != 422


def test_cloudflare_mode_persists_direct_evidence_as_unverified(
    waf_api_client, monkeypatch, caplog
):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())
    settings = routes_module.get_settings().model_copy(
        update={
            "waf_source_verification_mode": "cloudflare_tunnel",
            "waf_audit_evidence_key": "test-audit-evidence-key",
        }
    )
    monkeypatch.setattr(routes_module, "get_settings", lambda: settings)
    payload = _waf_payload()
    payload["transaction_id"] = "waf-txn-mode-mismatch"

    with caplog.at_level(logging.WARNING):
        response = client.post(
            "/api/internal/waf-events",
            json=payload,
            headers=WAF_HEADERS,
        )

    assert response.status_code == 200
    lookup = client.get(
        "/api/internal/waf-events/waf-txn-mode-mismatch",
        headers=INTERNAL_HEADERS,
    )
    assert lookup.status_code == 200
    assert lookup.json()["source_provenance"] == "DIRECT_REMOTE_ADDR"
    assert lookup.json()["source_verification_status"] == "UNVERIFIED"
    event = _structured_events(caplog, "source_provenance_mode_mismatch")[-1]
    assert event["transaction_id"] == "waf-txn-mode-mismatch"
    assert event["verification_mode"] == "cloudflare_tunnel"
    assert event["source_provenance"] == "DIRECT_REMOTE_ADDR"
    assert "request_headers" not in event
    assert "sanitized_body" not in event
    assert "authorization" not in caplog.text.lower()


def test_cloudflare_payload_without_bridge_audit_marker_cannot_claim_verified(
    waf_api_client, monkeypatch
):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())
    settings = routes_module.get_settings().model_copy(
        update={
            "waf_source_verification_mode": "cloudflare_tunnel",
            "waf_audit_evidence_key": "test-audit-evidence-key",
        }
    )
    monkeypatch.setattr(routes_module, "get_settings", lambda: settings)
    payload = _waf_payload()
    payload.update(
        {
            "transaction_id": "waf-txn-forged-cloudflare",
            "source_provenance": "CLOUDFLARE_CONNECTING_IP",
            "cf_connecting_ip_matches_client_ip": True,
        }
    )

    response = client.post(
        "/api/internal/waf-events",
        json=payload,
        headers=WAF_HEADERS,
    )

    assert response.status_code == 200
    lookup = client.get(
        "/api/internal/waf-events/waf-txn-forged-cloudflare",
        headers=INTERNAL_HEADERS,
    )
    assert lookup.json()["source_provenance"] == "DIRECT_REMOTE_ADDR"
    assert lookup.json()["source_verification_status"] == "UNVERIFIED"


def test_marked_cloudflare_audit_evidence_can_verify_server_side(
    waf_api_client, monkeypatch
):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())
    settings = routes_module.get_settings().model_copy(
        update={
            "waf_source_verification_mode": "cloudflare_tunnel",
            "waf_audit_evidence_key": "test-audit-evidence-key",
        }
    )
    monkeypatch.setattr(routes_module, "get_settings", lambda: settings)
    payload = _waf_payload()
    payload.update(
        {
            "transaction_id": "waf-txn-marked-cloudflare",
            "source_provenance": "CLOUDFLARE_CONNECTING_IP",
            "cf_connecting_ip_matches_client_ip": True,
        }
    )

    response = client.post(
        "/api/internal/waf-events",
        json=payload,
        headers={
            **WAF_HEADERS,
            "X-CyberTrace-WAF-Audit": "modsecurity",
            "X-CyberTrace-WAF-Audit-Key": "test-audit-evidence-key",
        },
    )

    assert response.status_code == 200
    lookup = client.get(
        "/api/internal/waf-events/waf-txn-marked-cloudflare",
        headers=INTERNAL_HEADERS,
    )
    assert lookup.json()["source_provenance"] == "CLOUDFLARE_CONNECTING_IP"
    assert lookup.json()["source_verification_status"] == "VERIFIED"


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
        headers=WAF_HEADERS,
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
    assert body["source_provenance"] == "DIRECT_REMOTE_ADDR"
    assert body["source_verification_status"] == "UNVERIFIED"
    assert "ingest_fingerprint_sha256" not in body
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
        headers=WAF_HEADERS,
    )
    second = client.post(
        "/api/internal/waf-events",
        json=payload,
        headers=WAF_HEADERS,
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
    assert asyncio.run(_count_traffic_logs(db_module.AsyncSessionLocal)) == 1


def test_waf_ingest_processing_duplicate_returns_409_with_retry_after(
    waf_api_client, caplog
):
    client, init_tables = waf_api_client
    import asyncio
    payload = _waf_payload()
    payload["transaction_id"] = "waf-txn-processing-1"

    async def _seed_processing() -> None:
        await init_tables()
        session_factory = db_module.AsyncSessionLocal
        async with session_factory() as session:
            session.add(
                TrafficLog(
                    transaction_id="waf-txn-processing-1",
                    created_at=datetime.now(timezone.utc),
                    timestamp=datetime.now(timezone.utc),
                    source_ip="203.0.113.10",
                    source_provenance="DIRECT_REMOTE_ADDR",
                    source_verification_status="UNVERIFIED",
                    request_path="/login",
                    request_method="POST",
                    http_request="POST /login HTTP/1.1",
                    crs_score=8,
                    crs_rule_ids=["942100"],
                    status="PROCESSING",
                    lease_expires_at=datetime.now(timezone.utc)
                    + timedelta(seconds=30),
                    processing_owner_token="owner-old",
                    processing_attempt=1,
                    ingest_fingerprint_sha256=_payload_fingerprint(payload),
                )
            )
            await session.commit()

    asyncio.run(_seed_processing())

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/internal/waf-events",
            json=payload,
            headers=WAF_HEADERS,
        )

    assert response.status_code == 409
    assert response.headers["Retry-After"] == "5"
    event = _structured_events(
        caplog, "waf_ingest.duplicate_or_processing"
    )[-1]
    assert event["transaction_id"] == "waf-txn-processing-1"
    assert event["status_code"] == 409


def test_concurrent_duplicate_transaction_runs_inference_once(waf_api_client):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())
    prediction_started = threading.Event()
    release_prediction = threading.Event()
    prediction_count = 0
    count_lock = threading.Lock()

    class BlockingModelService(FakeWafModelService):
        def predict(self, http_request: str):
            nonlocal prediction_count
            with count_lock:
                prediction_count += 1
            prediction_started.set()
            assert release_prediction.wait(timeout=5)
            return super().predict(http_request)

    class ConcurrentQueue:
        def health(self):
            return {"depth": 0}

        async def submit(self, coro_factory):
            return await coro_factory()

    client.app.dependency_overrides[get_model_service] = (
        lambda: BlockingModelService()
    )
    client.app.dependency_overrides[get_inference_queue] = (
        lambda: ConcurrentQueue()
    )
    payload = _waf_payload()
    payload["transaction_id"] = "waf-txn-live-concurrent"

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(
            client.post,
            "/api/internal/waf-events",
            json=payload,
            headers=WAF_HEADERS,
        )
        assert prediction_started.wait(timeout=5)
        second_future = executor.submit(
            client.post,
            "/api/internal/waf-events",
            json=payload,
            headers=WAF_HEADERS,
        )
        second = second_future.result(timeout=5)
        release_prediction.set()
        first = first_future.result(timeout=5)

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.headers["Retry-After"] == "5"
    assert prediction_count == 1
    assert asyncio.run(_count_traffic_logs(db_module.AsyncSessionLocal)) == 1


def test_telegram_enqueue_failure_cannot_rollback_persisted_waf_alert(
    waf_api_client, monkeypatch
):
    client, init_tables = waf_api_client
    import asyncio

    asyncio.run(init_tables())
    actual_settings = routes_module.get_settings()
    telegram_settings = actual_settings.model_copy(
        update={
            "threat_email_enabled": False,
            "threat_telegram_enabled": True,
            "telegram_bot_token": "test-token",
            "telegram_chat_id": "-100123",
        }
    )
    monkeypatch.setattr(routes_module, "get_settings", lambda: telegram_settings)

    class FailingOutbox:
        def __init__(self) -> None:
            self.channels: list[str] = []

        async def enqueue(self, notification):
            self.channels.append(notification.channel)
            raise RuntimeError("telegram unavailable")

    failing_outbox = FailingOutbox()
    client.app.state.notification_outbox_repository = failing_outbox
    payload = _waf_payload()
    payload["transaction_id"] = "waf-txn-telegram-failure"

    response = client.post(
        "/api/internal/waf-events",
        json=payload,
        headers=WAF_HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["alert_id"] is not None
    assert failing_outbox.channels == ["telegram"]
    assert asyncio.run(_count_traffic_logs(db_module.AsyncSessionLocal)) == 1
