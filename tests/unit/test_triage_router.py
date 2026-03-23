from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from web_app.presentation.api import triage_router
from web_app.presentation.schemas import TriageIngestRequest


class DummyUseCase:
    init_kwargs = None
    ingest_called_with = None

    def __init__(self, **kwargs):
        DummyUseCase.init_kwargs = kwargs

    async def ingest(self, command):
        DummyUseCase.ingest_called_with = command
        return SimpleNamespace(
            alert_id=7,
            prediction="SQL Injection",
            confidence=0.93,
            confidence_level="HIGH",
            action_taken="BLOCKED",
            model_version="test-model",
        )


@pytest.mark.asyncio
async def test_ingest_triage_passes_preprocessing_flag(monkeypatch):
    settings = SimpleNamespace(
        stale_processing_timeout_seconds=17,
        enable_http_model_preprocessing=False,
    )
    monkeypatch.setattr(triage_router, "get_settings", lambda: settings)
    monkeypatch.setattr(triage_router, "get_model_service", lambda request: "model-service")
    monkeypatch.setattr(triage_router, "get_repository", lambda db=None: "repository")
    monkeypatch.setattr(triage_router, "TriageUseCase", DummyUseCase)

    payload = TriageIngestRequest(
        transaction_id="txn-1",
        timestamp=datetime(2026, 3, 23, tzinfo=timezone.utc),
        source_ip="127.0.0.1",
        request_method="POST",
        request_uri="/login",
        request_headers={"content-type": "application/json"},
        request_body="{}",
        http_request="POST /login HTTP/1.1",
        crs_score=5,
        crs_rule_ids=[],
    )

    result = await triage_router.ingest_triage(
        payload=payload,
        model_service="model-service",
        repository="repository",
    )

    assert DummyUseCase.init_kwargs == {
        "classifier": "model-service",
        "repository": "repository",
        "stale_processing_timeout_seconds": 17,
        "enable_preprocessing": False,
    }
    assert DummyUseCase.ingest_called_with.transaction_id == "txn-1"
    assert DummyUseCase.ingest_called_with.http_request == "POST /login HTTP/1.1"
    assert result.alert_id == 7
    assert result.action_taken == "BLOCKED"
