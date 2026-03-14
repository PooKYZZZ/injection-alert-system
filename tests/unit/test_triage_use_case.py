"""Unit tests for TriageUseCase.

These tests use mock objects for both the classifier and repository,
verifying that the use case correctly:
  1. Calls the classifier with the HTTP request
  2. Applies the correct confidence-gated action logic
  3. Persists the entity through the repository interface
"""

import asyncio
from datetime import datetime, timedelta, timezone
import pytest
from unittest.mock import AsyncMock, MagicMock

from web_app.application import triage_use_case as triage_use_case_module
from web_app.application.triage_use_case import (
    ModelNotReadyError,
    TriageIngestCommand,
    TriageInProgressError,
    TriageProcessingStaleError,
    TriageResult,
    TriageUseCase,
)
from web_app.domain.interfaces import TrafficLogEntity


@pytest.fixture
def mock_classifier():
    """Create a mock classifier."""
    classifier = MagicMock()
    classifier.loaded = True
    classifier.model_version = "test-model-v1"
    return classifier


@pytest.fixture
def mock_repository():
    """Create a mock repository with async save."""
    repo = AsyncMock()
    repo.get_by_transaction_id.return_value = None
    repo.claim_processing.return_value = True

    async def save_side_effect(entity: TrafficLogEntity) -> TrafficLogEntity:
        entity.id = 1
        return entity

    async def complete_processing_side_effect(
        transaction_id: str,
        **kwargs,
    ) -> TrafficLogEntity:
        status = kwargs.get("status", "COMPLETED")
        entity.id = 1
        entity.transaction_id = transaction_id
        entity.prediction = kwargs["prediction"]
        entity.confidence = kwargs["confidence"]
        entity.confidence_level = kwargs["confidence_level"]
        entity.inference_latency_ms = kwargs["inference_latency_ms"]
        entity.model_version = kwargs["model_version"]
        entity.action_taken = kwargs["action_taken"]
        entity.status = status
        return entity

    entity = TrafficLogEntity(
        source_ip="127.0.0.1",
        http_request="test",
    )
    repo.save.side_effect = save_side_effect
    repo.complete_processing.side_effect = complete_processing_side_effect
    return repo


@pytest.mark.asyncio
async def test_triage_high_confidence_attack_is_blocked(mock_classifier, mock_repository):
    """HIGH confidence + non-Normal class → BLOCKED"""
    mock_classifier.predict.return_value = {
        "class": "SQL Injection",
        "confidence": 0.95,
        "confidence_level": "HIGH",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    result = await use_case.execute(
        http_request="SELECT * FROM users; DROP TABLE users;--",
        source_ip="192.168.1.1",
    )

    assert result.class_label == "SQL Injection"
    assert result.action_taken == "BLOCKED"
    assert result.confidence == 0.95
    mock_classifier.predict.assert_called_once()
    mock_repository.save.assert_called_once()


@pytest.mark.asyncio
async def test_triage_medium_confidence_is_throttled(mock_classifier, mock_repository):
    """MEDIUM confidence → THROTTLED regardless of class"""
    mock_classifier.predict.return_value = {
        "class": "Code Injection",
        "confidence": 0.65,
        "confidence_level": "MEDIUM",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    result = await use_case.execute(
        http_request="<script>alert(1)</script>",
        source_ip="10.0.0.1",
    )

    assert result.action_taken == "THROTTLED"
    mock_repository.save.assert_called_once()


@pytest.mark.asyncio
async def test_triage_normal_high_confidence_is_allowed(mock_classifier, mock_repository):
    """HIGH confidence + Normal class → ALLOWED (not BLOCKED)"""
    mock_classifier.predict.return_value = {
        "class": "Normal",
        "confidence": 0.95,
        "confidence_level": "HIGH",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    result = await use_case.execute(
        http_request="GET /index.html",
        source_ip="127.0.0.1",
    )

    assert result.class_label == "Normal"
    assert result.action_taken == "ALLOWED"


@pytest.mark.asyncio
async def test_triage_low_confidence_is_allowed(mock_classifier, mock_repository):
    """LOW confidence → ALLOWED"""
    mock_classifier.predict.return_value = {
        "class": "Other Attacks",
        "confidence": 0.3,
        "confidence_level": "LOW",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    result = await use_case.execute(
        http_request="GET /api/data",
        source_ip="10.0.0.1",
    )

    assert result.action_taken == "ALLOWED"


@pytest.mark.asyncio
async def test_triage_persists_correct_entity_fields(mock_classifier, mock_repository):
    """Verify the entity passed to repository.save has the correct fields."""
    mock_classifier.predict.return_value = {
        "class": "SQL Injection",
        "confidence": 0.88,
        "confidence_level": "HIGH",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    await use_case.execute(
        http_request="UNION SELECT password FROM admin",
        source_ip="192.168.1.100",
    )

    # Verify the entity passed to save
    saved_entity = mock_repository.save.call_args[0][0]
    assert isinstance(saved_entity, TrafficLogEntity)
    assert saved_entity.source_ip == "192.168.1.100"
    assert saved_entity.http_request == "UNION SELECT password FROM admin"
    assert saved_entity.prediction == "SQL Injection"
    assert saved_entity.confidence == 0.88
    assert saved_entity.action_taken == "BLOCKED"


@pytest.mark.asyncio
async def test_triage_offloads_sync_predict_via_threadpool(
    mock_classifier,
    mock_repository,
    monkeypatch: pytest.MonkeyPatch,
):
    """Async triage execution must offload sync ML inference."""
    expected_result = {
        "class": "Normal",
        "confidence": 0.42,
        "confidence_level": "LOW",
    }
    mock_classifier.predict.return_value = expected_result

    captured: dict[str, object] = {}

    async def fake_run_in_threadpool(func, *args, **kwargs):
        captured["func"] = func
        captured["args"] = args
        captured["kwargs"] = kwargs
        return func(*args, **kwargs)

    monkeypatch.setattr(
        triage_use_case_module,
        "run_in_threadpool",
        fake_run_in_threadpool,
    )

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    result = await use_case.execute(
        http_request="GET /health",
        source_ip="127.0.0.1",
    )

    assert captured["func"] is mock_classifier.predict
    assert captured["args"] == ("GET /health",)
    assert captured["kwargs"] == {}
    assert result == TriageResult(
        alert_id=1,
        prediction="Normal",
        confidence=0.42,
        confidence_level="LOW",
        action_taken="ALLOWED",
        model_version="test-model-v1",
    )


@pytest.mark.asyncio
async def test_ingest_returns_existing_alert_without_reinferring(
    mock_classifier,
    mock_repository,
):
    existing = TrafficLogEntity(
        id=7,
        transaction_id="txn-7",
        created_at=datetime.now(timezone.utc),
        source_ip="203.0.113.1",
        http_request="GET /triage",
        status="COMPLETED",
        prediction="SQL Injection",
        confidence=0.91,
        confidence_level="HIGH",
        model_version="stored-model-v1",
        action_taken="BLOCKED",
    )
    mock_repository.get_by_transaction_id.return_value = existing
    mock_repository.claim_processing.return_value = False

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    result = await use_case.ingest(
        TriageIngestCommand(
            transaction_id="txn-7",
            timestamp=triage_use_case_module.datetime.fromisoformat("2026-03-15T12:00:00"),
            source_ip="203.0.113.1",
            request_method="POST",
            request_uri="/login",
            request_headers={"Host": "example.test"},
            request_body="username=admin",
            http_request="POST /login HTTP/1.1",
            crs_score=7,
            crs_rule_ids=["942100"],
        )
    )

    mock_classifier.predict.assert_not_called()
    mock_repository.complete_processing.assert_not_called()
    assert result.alert_id == 7
    assert result.prediction == "SQL Injection"


@pytest.mark.asyncio
async def test_ingest_raises_model_not_ready_when_service_not_loaded(
    mock_repository,
):
    classifier = MagicMock()
    classifier.loaded = False

    use_case = TriageUseCase(classifier=classifier, repository=mock_repository)

    with pytest.raises(ModelNotReadyError):
        await use_case.ingest(
            TriageIngestCommand(
                transaction_id="txn-9",
                timestamp=triage_use_case_module.datetime.fromisoformat("2026-03-15T12:00:00"),
                source_ip="203.0.113.9",
                request_method="POST",
                request_uri="/login",
                request_headers={"Host": "example.test"},
                request_body="username=admin",
                http_request="POST /login HTTP/1.1",
                crs_score=7,
                crs_rule_ids=["942100"],
            )
        )


@pytest.mark.asyncio
async def test_ingest_folds_headers_and_body_into_persisted_http_request(
    mock_classifier,
    mock_repository,
):
    mock_classifier.predict.return_value = {
        "prediction": "SQL Injection",
        "confidence": 0.88,
        "confidence_tier": "HIGH",
        "inference_latency_ms": 5.5,
        "model_version": "test-model-v1",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    await use_case.ingest(
        TriageIngestCommand(
            transaction_id="txn-fold-1",
            timestamp=triage_use_case_module.datetime.fromisoformat("2026-03-15T12:00:00"),
            source_ip="192.168.1.100",
            request_method="POST",
            request_uri="/login",
            request_headers={"Host": "example.test", "User-Agent": "pytest"},
            request_body="username=admin",
            http_request="POST /login HTTP/1.1",
            crs_score=9,
            crs_rule_ids=["942100", "942110"],
        )
    )

    saved_entity = mock_repository.claim_processing.call_args[0][0]
    assert "Headers:" in saved_entity.http_request
    assert "Host: example.test" in saved_entity.http_request
    assert "Body:\nusername=admin" in saved_entity.http_request
    assert saved_entity.crs_rule_ids == ["942100", "942110"]


@pytest.mark.asyncio
async def test_ingest_loser_with_processing_row_returns_in_progress(
    mock_classifier,
    mock_repository,
):
    mock_repository.claim_processing.return_value = False
    mock_repository.get_by_transaction_id.return_value = TrafficLogEntity(
        id=11,
        transaction_id="txn-processing",
        created_at=datetime.now(timezone.utc),
        status="PROCESSING",
    )

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)

    with pytest.raises(TriageInProgressError):
        await use_case.ingest(
            TriageIngestCommand(
                transaction_id="txn-processing",
                timestamp=datetime.now(timezone.utc),
                source_ip="203.0.113.10",
                request_method="POST",
                request_uri="/login",
                request_headers={"Host": "example.test"},
                request_body="username=admin",
                http_request="POST /login HTTP/1.1",
                crs_score=8,
                crs_rule_ids=["942100"],
            )
        )

    mock_classifier.predict.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_loser_with_stale_processing_row_returns_stale_error(
    mock_classifier,
    mock_repository,
):
    mock_repository.claim_processing.return_value = False
    mock_repository.get_by_transaction_id.return_value = TrafficLogEntity(
        id=12,
        transaction_id="txn-stale",
        created_at=datetime.now(timezone.utc) - timedelta(seconds=31),
        status="PROCESSING",
    )

    use_case = TriageUseCase(
        classifier=mock_classifier,
        repository=mock_repository,
        stale_processing_timeout_seconds=30,
    )

    with pytest.raises(TriageProcessingStaleError):
        await use_case.ingest(
            TriageIngestCommand(
                transaction_id="txn-stale",
                timestamp=datetime.now(timezone.utc),
                source_ip="203.0.113.11",
                request_method="POST",
                request_uri="/login",
                request_headers={"Host": "example.test"},
                request_body="username=admin",
                http_request="POST /login HTTP/1.1",
                crs_score=8,
                crs_rule_ids=["942100"],
            )
        )

    mock_classifier.predict.assert_not_called()


@pytest.mark.asyncio
async def test_concurrent_duplicate_transaction_id_runs_inference_once():
    class FakeRepository:
        def __init__(self):
            self.claimed = False
            self.completed: TrafficLogEntity | None = None

        async def save(self, entity):
            entity.id = 1
            return entity

        async def save_if_absent(self, entity):
            entity.id = 1
            return entity, True

        async def claim_processing(self, entity):
            if self.claimed:
                return False
            self.claimed = True
            self.completed = TrafficLogEntity(
                id=1,
                transaction_id=entity.transaction_id,
                created_at=datetime.now(timezone.utc),
                status="PROCESSING",
                http_request=entity.http_request,
            )
            return True

        async def complete_processing(self, transaction_id: str, **kwargs):
            assert self.completed is not None
            self.completed.transaction_id = transaction_id
            self.completed.prediction = kwargs["prediction"]
            self.completed.confidence = kwargs["confidence"]
            self.completed.confidence_level = kwargs["confidence_level"]
            self.completed.inference_latency_ms = kwargs["inference_latency_ms"]
            self.completed.model_version = kwargs["model_version"]
            self.completed.action_taken = kwargs["action_taken"]
            self.completed.status = "COMPLETED"
            return self.completed

        async def get_by_id(self, traffic_id):
            return self.completed

        async def get_by_transaction_id(self, transaction_id):
            while self.completed is not None and self.completed.status == "PROCESSING":
                await asyncio.sleep(0.001)
            return self.completed

        async def get_stats_summary(self):
            raise NotImplementedError

        async def get_alert_list(self, page, page_size, severity=None, time_range=None, search=None):
            raise NotImplementedError

        async def list_recent(self, skip=0, limit=100):
            raise NotImplementedError

        async def update_feedback(self, traffic_id, analyst_label, analyst_email, labeled_at):
            raise NotImplementedError

    class FakeClassifier:
        def __init__(self):
            self.loaded = True
            self.model_version = "test-model-v1"
            self.calls = 0

        def predict(self, http_request: str):
            self.calls += 1
            import time
            time.sleep(0.01)
            return {
                "prediction": "SQL Injection",
                "confidence": 0.9,
                "confidence_tier": "HIGH",
                "inference_latency_ms": 1.2,
                "model_version": self.model_version,
            }

    repository = FakeRepository()
    classifier = FakeClassifier()
    use_case = TriageUseCase(classifier=classifier, repository=repository)
    command = TriageIngestCommand(
        transaction_id="txn-concurrent",
        timestamp=datetime.now(timezone.utc),
        source_ip="203.0.113.99",
        request_method="POST",
        request_uri="/login",
        request_headers={"Host": "example.test"},
        request_body="username=admin",
        http_request="POST /login HTTP/1.1",
        crs_score=9,
        crs_rule_ids=["942100"],
    )

    first, second = await asyncio.gather(
        use_case.ingest(command),
        use_case.ingest(command),
    )

    assert classifier.calls == 1
    assert first.alert_id == second.alert_id == 1
    assert first.prediction == second.prediction == "SQL Injection"
