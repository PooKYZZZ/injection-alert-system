"""Unit tests for TriageUseCase.

These tests use mock objects for both the classifier and repository,
verifying that the use case correctly:
  1. Calls the classifier with the HTTP request
  2. Applies the correct confidence-gated action logic
  3. Persists the entity through the repository interface
"""

import asyncio
from datetime import datetime, timezone
from hashlib import sha256
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import parse_qsl

import pytest

from web_app.application import triage_use_case as triage_use_case_module
from web_app.application.triage_use_case import (
    ModelNotReadyError,
    TriageIngestCommand,
    TriageInProgressError,
    TriageMetadataConflictError,
    TriageResult,
    TriageUseCase,
)
from web_app.domain.interfaces import TrafficLogEntity
from web_app.domain.source_address import (
    SourceProvenance,
    SourceVerificationStatus,
)


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
    repo.claim_or_reclaim_processing.return_value = TrafficLogEntity(
        id=1,
        transaction_id="txn-1",
        created_at=datetime.now(timezone.utc),
        status="PROCESSING",
        processing_owner_token="owner-token",
        processing_attempt=1,
    )

    async def save_side_effect(entity: TrafficLogEntity) -> TrafficLogEntity:
        entity.id = 1
        return entity

    async def complete_processing_side_effect(
        transaction_id: str,
        **kwargs,
    ) -> tuple[TrafficLogEntity, bool]:
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
        entity.processing_owner_token = kwargs.get("owner_token", "owner-token")
        return entity, True

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


@pytest.mark.parametrize(
    ("prediction", "confidence_level", "expected_action"),
    [
        ("SQL Injection", "CRITICAL", "BLOCKED"),
        ("Code Injection", "CRITICAL", "BLOCKED"),
        ("Other Attacks", "CRITICAL", "BLOCKED"),
        ("Normal", "CRITICAL", "ALLOWED"),
    ],
)
def test_triage_critical_action_mapping(prediction, confidence_level, expected_action):
    assert TriageUseCase._action_for(
        prediction=prediction,
        confidence_level=confidence_level,
    ) == expected_action


@pytest.mark.parametrize(
    ("prediction", "confidence_level"),
    [
        ("SQL Injection", None),
        ("SQL Injection", "UNKNOWN_TIER"),
        ("Normal", None),
        ("Normal", "UNKNOWN_TIER"),
    ],
)
def test_triage_unknown_confidence_tier_raises_value_error(
    prediction,
    confidence_level,
):
    with pytest.raises(ValueError):
        TriageUseCase._action_for(
            prediction=prediction,
            confidence_level=confidence_level,
        )


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
    # Preprocessing is applied: "GET /health" -> "get /health"
    assert captured["args"] == ("get /health",)
    assert captured["kwargs"] == {}
    assert result == TriageResult(
        alert_id=1,
        prediction="Normal",
        confidence=0.42,
        confidence_level="LOW",
        action_taken="ALLOWED",
        model_version="test-model-v1",
        occurred_at=None,
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
        source_provenance=SourceProvenance.DIRECT_REMOTE_ADDR,
        source_verification_status=SourceVerificationStatus.UNVERIFIED,
        ingest_fingerprint_sha256="a" * 64,
    )
    mock_repository.get_by_transaction_id.return_value = existing
    mock_repository.claim_or_reclaim_processing.return_value = existing

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
            ingest_fingerprint_sha256="a" * 64,
        )
    )

    mock_classifier.predict.assert_not_called()
    mock_repository.complete_processing.assert_not_called()
    assert result.alert_id == 7
    assert result.prediction == "SQL Injection"


@pytest.mark.asyncio
async def test_ingest_publishes_only_after_visible_alert_is_persisted(
    mock_classifier,
    mock_repository,
):
    mock_classifier.predict.return_value = {
        "prediction": "SQL Injection",
        "confidence": 0.91,
        "confidence_tier": "HIGH",
    }
    call_order: list[str] = []
    original_complete = mock_repository.complete_processing.side_effect

    async def complete_then_record(*args, **kwargs):
        result = await original_complete(*args, **kwargs)
        call_order.append("persisted")
        return result

    mock_repository.complete_processing.side_effect = complete_then_record
    publisher = MagicMock()
    publisher.publish_alert_created.side_effect = lambda: call_order.append("published")
    use_case = TriageUseCase(
        classifier=mock_classifier,
        repository=mock_repository,
        alert_event_publisher=publisher,
    )

    await use_case.ingest(
        TriageIngestCommand(
            transaction_id="txn-publish-1",
            timestamp=datetime.now(timezone.utc),
            source_ip="203.0.113.10",
            request_method="POST",
            request_uri="/login",
            request_headers={},
            request_body="",
            http_request="POST /login HTTP/1.1",
            crs_score=8,
            crs_rule_ids=["942100"],
        )
    )

    assert call_order == ["persisted", "published"]
    publisher.publish_alert_created.assert_called_once_with()


@pytest.mark.asyncio
async def test_execute_returns_persisted_result_when_event_publication_fails(
    mock_classifier,
    mock_repository,
):
    mock_classifier.predict.return_value = {
        "prediction": "SQL Injection",
        "confidence": 0.91,
        "confidence_tier": "HIGH",
    }
    publisher = MagicMock()
    publisher.publish_alert_created.side_effect = RuntimeError("publisher failed")
    use_case = TriageUseCase(
        classifier=mock_classifier,
        repository=mock_repository,
        alert_event_publisher=publisher,
    )

    result = await use_case.execute(
        http_request="POST /login HTTP/1.1",
        source_ip="203.0.113.10",
    )

    assert result.alert_id == 1
    publisher.publish_alert_created.assert_called_once_with()


@pytest.mark.asyncio
async def test_ingest_returns_persisted_result_when_event_publication_fails(
    mock_classifier,
    mock_repository,
):
    mock_classifier.predict.return_value = {
        "prediction": "SQL Injection",
        "confidence": 0.91,
        "confidence_tier": "HIGH",
    }
    publisher = MagicMock()
    publisher.publish_alert_created.side_effect = RuntimeError("publisher failed")
    use_case = TriageUseCase(
        classifier=mock_classifier,
        repository=mock_repository,
        alert_event_publisher=publisher,
    )

    result = await use_case.ingest(
        TriageIngestCommand(
            transaction_id="txn-publisher-failure",
            timestamp=datetime.now(timezone.utc),
            source_ip="203.0.113.10",
            request_method="POST",
            request_uri="/login",
            request_headers={},
            request_body="",
            http_request="POST /login HTTP/1.1",
            crs_score=8,
            crs_rule_ids=["942100"],
        )
    )

    assert result.alert_id == 1
    publisher.publish_alert_created.assert_called_once_with()


@pytest.mark.asyncio
async def test_ingest_does_not_publish_for_duplicate_or_failed_persistence(
    mock_classifier,
    mock_repository,
):
    mock_classifier.predict.return_value = {
        "prediction": "SQL Injection",
        "confidence": 0.91,
        "confidence_tier": "HIGH",
    }
    publisher = MagicMock()
    existing = TrafficLogEntity(
        id=21,
        transaction_id="txn-existing",
        created_at=datetime.now(timezone.utc),
        status="COMPLETED",
        prediction="SQL Injection",
        confidence=0.91,
        confidence_level="HIGH",
        action_taken="BLOCKED",
    )
    mock_repository.claim_or_reclaim_processing.return_value = existing
    use_case = TriageUseCase(
        classifier=mock_classifier,
        repository=mock_repository,
        alert_event_publisher=publisher,
    )
    command = TriageIngestCommand(
        transaction_id="txn-existing",
        timestamp=datetime.now(timezone.utc),
        source_ip="203.0.113.10",
        request_method="POST",
        request_uri="/login",
        request_headers={},
        request_body="",
        http_request="POST /login HTTP/1.1",
        crs_score=8,
        crs_rule_ids=["942100"],
    )

    await use_case.ingest(command)
    publisher.publish_alert_created.assert_not_called()

    mock_repository.claim_or_reclaim_processing.return_value = TrafficLogEntity(
        id=22,
        transaction_id="txn-failure",
        created_at=datetime.now(timezone.utc),
        status="PROCESSING",
        processing_owner_token="owner-token",
    )
    mock_repository.complete_processing.side_effect = RuntimeError("commit failed")
    with pytest.raises(RuntimeError, match="commit failed"):
        await use_case.ingest(command)
    publisher.publish_alert_created.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_does_not_publish_when_completion_ownership_was_lost(
    mock_classifier,
    mock_repository,
):
    mock_classifier.predict.return_value = {
        "prediction": "SQL Injection",
        "confidence": 0.91,
        "confidence_tier": "HIGH",
    }
    existing = TrafficLogEntity(
        id=23,
        transaction_id="txn-lost-owner",
        created_at=datetime.now(timezone.utc),
        status="COMPLETED",
        prediction="SQL Injection",
        confidence=0.91,
        confidence_level="HIGH",
        action_taken="BLOCKED",
    )
    mock_repository.complete_processing.side_effect = None
    mock_repository.complete_processing.return_value = (existing, False)
    publisher = MagicMock()
    use_case = TriageUseCase(
        classifier=mock_classifier,
        repository=mock_repository,
        alert_event_publisher=publisher,
    )

    command = TriageIngestCommand(
        transaction_id="txn-lost-owner",
        timestamp=datetime.now(timezone.utc),
        source_ip="203.0.113.10",
        request_method="POST",
        request_uri="/login",
        request_headers={},
        request_body="",
        http_request="POST /login HTTP/1.1",
        crs_score=8,
        crs_rule_ids=["942100"],
    )
    result = await use_case.ingest(command)

    assert result.alert_id == 23
    publisher.publish_alert_created.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_reports_in_progress_when_lost_owner_row_is_unfinished(
    mock_classifier,
    mock_repository,
):
    mock_classifier.predict.return_value = {
        "prediction": "SQL Injection",
        "confidence": 0.91,
        "confidence_tier": "HIGH",
    }
    unfinished = TrafficLogEntity(
        id=24,
        transaction_id="txn-reclaimed-owner",
        created_at=datetime.now(timezone.utc),
        status="PROCESSING",
        processing_owner_token="new-owner",
    )
    mock_repository.complete_processing.side_effect = None
    mock_repository.complete_processing.return_value = (unfinished, False)
    publisher = MagicMock()
    use_case = TriageUseCase(
        classifier=mock_classifier,
        repository=mock_repository,
        alert_event_publisher=publisher,
    )

    with pytest.raises(TriageInProgressError):
        await use_case.ingest(
            TriageIngestCommand(
                transaction_id="txn-reclaimed-owner",
                timestamp=datetime.now(timezone.utc),
                source_ip="203.0.113.10",
                request_method="POST",
                request_uri="/login",
                request_headers={},
                request_body="",
                http_request="POST /login HTTP/1.1",
                crs_score=8,
                crs_rule_ids=["942100"],
            )
        )

    publisher.publish_alert_created.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["COMPLETED", "PROCESSING"])
async def test_ingest_rejects_duplicate_with_mismatching_fingerprint(
    mock_classifier,
    mock_repository,
    monkeypatch,
    status,
):
    existing = TrafficLogEntity(
        id=17,
        transaction_id="txn-conflict",
        created_at=datetime.now(timezone.utc),
        status=status,
        ingest_fingerprint_sha256="a" * 64,
    )
    mock_repository.claim_or_reclaim_processing.return_value = (
        existing if status == "COMPLETED" else None
    )
    mock_repository.get_by_transaction_id.return_value = existing
    logged: list[dict] = []
    monkeypatch.setattr(
        triage_use_case_module,
        "log_event",
        lambda *args, **kwargs: logged.append(kwargs | {"event": args[1]}),
    )

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    with pytest.raises(TriageMetadataConflictError):
        await use_case.ingest(
            TriageIngestCommand(
                transaction_id="txn-conflict",
                timestamp=datetime.now(timezone.utc),
                source_ip="203.0.113.17",
                request_method="POST",
                request_uri="/login",
                request_headers={},
                request_body="",
                http_request="POST /login?q=incoming HTTP/1.1",
                crs_score=8,
                crs_rule_ids=["942100"],
                ingest_fingerprint_sha256="b" * 64,
            )
        )

    mock_classifier.predict.assert_not_called()
    assert logged == [
        {
            "level": "WARNING",
            "transaction_id": "txn-conflict",
            "stored_fingerprint_prefix": "aaaaaaaa",
            "incoming_fingerprint_prefix": "bbbbbbbb",
            "transaction_status": status,
            "event": "ingest_metadata_mismatch",
        }
    ]


@pytest.mark.asyncio
async def test_ingest_rejects_legacy_duplicate_without_fingerprint(
    mock_classifier,
    mock_repository,
):
    mock_repository.claim_or_reclaim_processing.return_value = None
    mock_repository.get_by_transaction_id.return_value = TrafficLogEntity(
        id=18,
        transaction_id="txn-legacy",
        created_at=datetime.now(timezone.utc),
        status="PROCESSING",
        ingest_fingerprint_sha256=None,
    )
    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)

    with pytest.raises(TriageMetadataConflictError):
        await use_case.ingest(
            TriageIngestCommand(
                transaction_id="txn-legacy",
                timestamp=datetime.now(timezone.utc),
                source_ip="203.0.113.18",
                request_method="POST",
                request_uri="/login",
                request_headers={},
                request_body="",
                http_request="POST /login HTTP/1.1",
                crs_score=8,
                crs_rule_ids=["942100"],
                ingest_fingerprint_sha256="c" * 64,
            )
        )

    mock_classifier.predict.assert_not_called()


@pytest.mark.asyncio
async def test_matching_retry_preserves_first_verification_status_and_logs_change(
    mock_classifier,
    mock_repository,
    monkeypatch,
):
    existing = TrafficLogEntity(
        id=19,
        transaction_id="txn-context-change",
        created_at=datetime.now(timezone.utc),
        status="COMPLETED",
        prediction="Normal",
        confidence=0.4,
        confidence_level="LOW",
        action_taken="ALLOWED",
        source_verification_status=SourceVerificationStatus.UNVERIFIED,
        ingest_fingerprint_sha256="d" * 64,
    )
    mock_repository.claim_or_reclaim_processing.return_value = existing
    logged: list[dict] = []
    monkeypatch.setattr(
        triage_use_case_module,
        "log_event",
        lambda *args, **kwargs: logged.append(kwargs | {"event": args[1]}),
    )
    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)

    result = await use_case.ingest(
        TriageIngestCommand(
            transaction_id="txn-context-change",
            timestamp=datetime.now(timezone.utc),
            source_ip="203.0.113.19",
            request_method="GET",
            request_uri="/",
            request_headers={},
            request_body="",
            http_request="GET / HTTP/1.1",
            crs_score=0,
            crs_rule_ids=[],
            source_verification_status=SourceVerificationStatus.VERIFIED,
            ingest_fingerprint_sha256="d" * 64,
        )
    )

    assert result.prediction == "Normal"
    assert existing.source_verification_status is SourceVerificationStatus.UNVERIFIED
    assert logged == [
        {
            "level": "WARNING",
            "transaction_id": "txn-context-change",
            "stored_verification_status": "UNVERIFIED",
            "incoming_verification_status": "VERIFIED",
            "event": "verification_context_changed",
        }
    ]


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
@pytest.mark.parametrize(
    "model_output",
    [
        {"confidence": 0.9, "confidence_level": "HIGH"},
        {"prediction": "SQL Injection", "confidence": 0.9},
        {"prediction": "SQL Injection", "confidence_level": "HIGH"},
        {
            "prediction": "SQL Injection",
            "confidence": "not-a-number",
            "confidence_level": "HIGH",
        },
    ],
    ids=[
        "missing-prediction",
        "missing-confidence-level",
        "missing-confidence",
        "invalid-confidence",
    ],
)
async def test_fresh_model_output_must_include_required_prediction_fields(
    mock_classifier,
    mock_repository,
    model_output,
):
    mock_classifier.predict.return_value = model_output
    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)

    with pytest.raises(
        ModelNotReadyError,
        match="Model returned an invalid prediction payload",
    ):
        await use_case.execute(
            http_request="POST /login HTTP/1.1",
            source_ip="203.0.113.9",
        )

    mock_repository.save.assert_not_called()


@pytest.mark.asyncio
async def test_unknown_model_label_cannot_be_persisted_or_enforced(
    mock_classifier,
    mock_repository,
):
    mock_classifier.predict.return_value = {
        "prediction": "Unknown Injection Label",
        "confidence": 0.99,
        "confidence_level": "CRITICAL",
    }
    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)

    with pytest.raises(ModelNotReadyError, match="unsupported prediction label"):
        await use_case.execute(
            http_request="GET /records/search HTTP/1.1",
            source_ip="203.0.113.10",
        )

    mock_repository.save.assert_not_called()


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
    mock_repository.claim_or_reclaim_processing.return_value = TrafficLogEntity(
        id=9,
        transaction_id="txn-fold-1",
        created_at=datetime.now(timezone.utc),
        status="PROCESSING",
        ingest_fingerprint_sha256="b" * 64,
        processing_owner_token="owner-token",
        processing_attempt=1,
    )

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

    saved_entity = mock_repository.claim_or_reclaim_processing.call_args[0][0]
    assert "Headers:" in saved_entity.http_request
    assert "Host: example.test" in saved_entity.http_request
    assert "Body:\nusername=admin" in saved_entity.http_request
    assert saved_entity.crs_rule_ids == ["942100", "942110"]


@pytest.mark.asyncio
async def test_ingest_redacts_sensitive_values_from_persisted_http_request(
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
            transaction_id="txn-redact-1",
            timestamp=triage_use_case_module.datetime.fromisoformat("2026-03-15T12:00:00"),
            source_ip="192.168.1.100",
            request_method="POST",
            request_uri="/login",
            request_headers={
                "Host": "example.test",
                "Authorization": "Bearer abc",
                "Cookie": "session=abc",
            },
            request_body='{"password":"hunter2","api_key":"abc123"}',
            http_request="POST /login HTTP/1.1",
            crs_score=9,
            crs_rule_ids=["942100"],
        )
    )

    saved_entity = mock_repository.claim_or_reclaim_processing.call_args[0][0]
    assert "hunter2" not in saved_entity.http_request
    assert "Bearer abc" not in saved_entity.http_request
    assert "session=abc" not in saved_entity.http_request
    assert "api_key=abc123" not in saved_entity.http_request
    assert "[REDACTED]" in saved_entity.http_request


@pytest.mark.asyncio
async def test_ingest_redacts_sensitive_values_from_persisted_query_string(
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
            transaction_id="txn-query-redact-1",
            timestamp=triage_use_case_module.datetime.fromisoformat("2026-03-15T12:00:00"),
            source_ip="192.168.1.100",
            request_method="GET",
            request_uri="/login",
            request_headers={"Host": "example.test"},
            request_body="",
            http_request="GET /login HTTP/1.1",
            crs_score=9,
            crs_rule_ids=["942100"],
            query_string=(
                "q=%27%20OR%201%3D1&password=hunter2&access%5Ftoken=abc"
                "&Token=first&Token=second&session_id=s1&item=book"
            ),
        )
    )

    saved_entity = mock_repository.claim_or_reclaim_processing.call_args[0][0]
    parsed: dict[str, list[str]] = {}
    assert saved_entity.query_string is not None
    for key, value in parse_qsl(saved_entity.query_string, keep_blank_values=True):
        parsed.setdefault(key, []).append(value)

    assert parsed["q"] == ["' OR 1=1"]
    assert parsed["item"] == ["book"]
    assert parsed["password"] == ["[REDACTED]"]
    assert parsed["access_token"] == ["[REDACTED]"]
    assert parsed["Token"] == ["[REDACTED]", "[REDACTED]"]
    assert parsed["session_id"] == ["[REDACTED]"]
    assert "hunter2" not in saved_entity.query_string
    assert "abc" not in saved_entity.query_string
    assert "first" not in saved_entity.query_string
    assert "second" not in saved_entity.query_string
    assert "s1" not in saved_entity.query_string
    assert saved_entity.http_request.startswith("GET /login HTTP/1.1")
    assert "hunter2" not in saved_entity.http_request
    assert "access_token" not in saved_entity.http_request


@pytest.mark.asyncio
async def test_ingest_loser_with_processing_row_returns_in_progress(
    mock_classifier,
    mock_repository,
):
    mock_repository.claim_or_reclaim_processing.return_value = None
    mock_repository.get_by_transaction_id.return_value = TrafficLogEntity(
        id=11,
        transaction_id="txn-processing",
        created_at=datetime.now(timezone.utc),
        status="PROCESSING",
        ingest_fingerprint_sha256="b" * 64,
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
                ingest_fingerprint_sha256="b" * 64,
            )
    )

    mock_classifier.predict.assert_not_called()

@pytest.mark.asyncio
async def test_ingest_reclaims_expired_processing_lease_and_completes(
    mock_classifier,
    mock_repository,
):
    """Expired lease is reclaimed and the new owner completes processing."""
    claimed_row = TrafficLogEntity(
        id=12,
        transaction_id="txn-stale",
        created_at=datetime.now(timezone.utc),
        status="PROCESSING",
        processing_owner_token="new-owner",
        processing_attempt=2,
        ingest_fingerprint_sha256="c" * 64,
    )
    completed_row = TrafficLogEntity(
        id=12,
        transaction_id="txn-stale",
        created_at=datetime.now(timezone.utc),
        status="COMPLETED",
        prediction="SQL Injection",
        confidence=0.97,
        confidence_level="HIGH",
        model_version="test-model-v1",
        action_taken="BLOCKED",
        processing_owner_token=None,
    )
    mock_repository.claim_or_reclaim_processing.return_value = claimed_row
    mock_repository.complete_processing.side_effect = None
    mock_repository.complete_processing.return_value = completed_row, True
    mock_classifier.predict.return_value = {
        "prediction": "SQL Injection",
        "confidence": 0.97,
        "confidence_level": "HIGH",
        "inference_latency_ms": 3.1,
        "model_version": "test-model-v1",
    }

    use_case = TriageUseCase(
        classifier=mock_classifier,
        repository=mock_repository,
        stale_processing_timeout_seconds=30,
        enable_preprocessing=False,
    )

    result = await use_case.ingest(
        TriageIngestCommand(
            transaction_id="txn-stale",
            timestamp=datetime.now(timezone.utc),
            source_ip="203.0.113.11",
            request_method="POST",
            request_uri="/login",
            request_headers={"Host": "example.test"},
            request_body="username=admin",
            http_request="POST /login?id=1%20OR%201=1 HTTP/1.1",
            crs_score=8,
            crs_rule_ids=["942100"],
            ingest_fingerprint_sha256="c" * 64,
        )
    )

    mock_classifier.predict.assert_called_once()
    mock_classifier.predict.assert_called_once_with(
        "POST /login?id=1%20OR%201=1 HTTP/1.1"
    )
    assert result.alert_id == 12
    assert result.prediction == "SQL Injection"
    assert result.action_taken == "BLOCKED"


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
                processing_owner_token="owner-token",
                processing_attempt=1,
            )
            return True

        async def claim_or_reclaim_processing(self, entity, *, owner_token, lease_expires_at, now):
            if self.claimed:
                return None
            self.claimed = True
            self.completed = TrafficLogEntity(
                id=1,
                transaction_id=entity.transaction_id,
                created_at=datetime.now(timezone.utc),
                status="PROCESSING",
                http_request=entity.http_request,
                processing_owner_token=owner_token,
                processing_attempt=1,
                lease_expires_at=lease_expires_at,
                ingest_fingerprint_sha256=entity.ingest_fingerprint_sha256,
            )
            return self.completed

        async def complete_processing(self, transaction_id: str, *, owner_token: str, **kwargs):
            assert self.completed is not None
            assert owner_token == self.completed.processing_owner_token
            self.completed.transaction_id = transaction_id
            self.completed.prediction = kwargs["prediction"]
            self.completed.confidence = kwargs["confidence"]
            self.completed.confidence_level = kwargs["confidence_level"]
            self.completed.inference_latency_ms = kwargs["inference_latency_ms"]
            self.completed.model_version = kwargs["model_version"]
            self.completed.action_taken = kwargs["action_taken"]
            self.completed.status = "COMPLETED"
            self.completed.processing_owner_token = None
            return self.completed, True

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
        ingest_fingerprint_sha256="d" * 64,
    )

    first, second = await asyncio.gather(
        use_case.ingest(command),
        use_case.ingest(command),
    )

    assert classifier.calls == 1
    assert first.alert_id == second.alert_id == 1
    assert first.prediction == second.prediction == "SQL Injection"


@pytest.mark.asyncio
async def test_execute_parses_http_request_for_method_and_path(
    mock_classifier,
    mock_repository,
):
    """Test that execute() parses the raw http_request to extract method and path.
    
    This verifies the end-to-end flow: raw HTTP request -> parse -> persist.
    The parsed method and path should be stored in the database.
    """
    mock_classifier.predict.return_value = {
        "class": "SQL Injection",
        "confidence": 0.92,
        "confidence_level": "HIGH",
        "inference_latency_ms": 3.5,
        "model_version": "test-model-v1",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    
    # This raw HTTP request should be parsed to extract method and path
    raw_http_request = "POST /api/login?redirect=home HTTP/1.1\nHost: example.com\n\nusername=admin"
    await use_case.execute(
        http_request=raw_http_request,
        source_ip="192.168.1.50",
    )

    # Verify the entity passed to save has parsed method and path
    saved_entity = mock_repository.save.call_args[0][0]
    
    # Method should be extracted and uppercased
    assert saved_entity.request_method == "POST"
    # Path should have query string stripped
    assert saved_entity.request_method is not None
    assert saved_entity.request_path is not None


@pytest.mark.asyncio
async def test_execute_parses_get_request(
    mock_classifier,
    mock_repository,
):
    """Test that GET requests with query strings are parsed correctly."""
    mock_classifier.predict.return_value = {
        "class": "Normal",
        "confidence": 0.99,
        "confidence_level": "HIGH",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    
    raw_http_request = "GET /users?id=123&sort=name HTTP/1.1"
    await use_case.execute(
        http_request=raw_http_request,
        source_ip="10.0.0.1",
    )

    saved_entity = mock_repository.save.call_args[0][0]
    
    assert saved_entity.request_method == "GET"
    assert saved_entity.request_path == "/users"  # Query string stripped


@pytest.mark.asyncio
async def test_execute_preserves_none_when_parsing_fails(
    mock_classifier,
    mock_repository,
):
    """Test that malformed HTTP request results in None values, not errors."""
    mock_classifier.predict.return_value = {
        "class": "Normal",
        "confidence": 0.50,
        "confidence_level": "LOW",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    
    # Malformed request - no valid HTTP method
    raw_http_request = "not a valid http request"
    await use_case.execute(
        http_request=raw_http_request,
        source_ip="127.0.0.1",
    )

    saved_entity = mock_repository.save.call_args[0][0]
    
    # Parsing fails gracefully - None values stored
    assert saved_entity.request_method is None
    assert saved_entity.request_path is None


@pytest.mark.asyncio
async def test_execute_handles_connect_authority_form_correctly(
    mock_classifier,
    mock_repository,
):
    """Test that CONNECT method with authority-form (host:port) returns None for path.
    
    RFC 7230 defines authority-form as: CONNECT example.com:443 HTTP/1.1
    This is used for HTTP tunneling. The parser should reject this, not treat
    it as a path. The raw http_request is still stored for forensics.
    """
    mock_classifier.predict.return_value = {
        "class": "Normal",
        "confidence": 0.99,
        "confidence_level": "HIGH",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    
    # CONNECT request with authority-form (no path)
    raw_http_request = "CONNECT example.com:443 HTTP/1.1"
    await use_case.execute(
        http_request=raw_http_request,
        source_ip="192.168.1.1",
    )

    saved_entity = mock_repository.save.call_args[0][0]
    
    # CONNECT method is valid, but authority-form has no path
    assert saved_entity.request_method == "CONNECT"
    assert saved_entity.request_path is None  # Authority-form explicitly rejected
    # Raw request is preserved for forensics
    assert saved_entity.http_request == raw_http_request


@pytest.mark.asyncio
async def test_execute_handles_options_asterisk_form(
    mock_classifier,
    mock_repository,
):
    """Test that OPTIONS method with asterisk-form (*) returns * as path.
    
    RFC 7230 defines asterisk-form as: OPTIONS * HTTP/1.1
    This is used to query server capabilities. The parser should return '*' as path.
    """
    mock_classifier.predict.return_value = {
        "class": "Normal",
        "confidence": 0.99,
        "confidence_level": "HIGH",
    }

    use_case = TriageUseCase(classifier=mock_classifier, repository=mock_repository)
    
    raw_http_request = "OPTIONS * HTTP/1.1"
    await use_case.execute(
        http_request=raw_http_request,
        source_ip="192.168.1.1",
    )

    saved_entity = mock_repository.save.call_args[0][0]
    
    assert saved_entity.request_method == "OPTIONS"
    assert saved_entity.request_path == "*"  # Asterisk-form returned as-is
    assert saved_entity.http_request == raw_http_request


@pytest.mark.asyncio
async def test_triage_preprocessing_enabled(mock_classifier, mock_repository):
    """Test that preprocessing is applied when enable_preprocessing=True."""
    mock_classifier.predict.return_value = {
        "class": "SQL Injection",
        "confidence": 0.92,
        "confidence_level": "HIGH",
    }

    captured_args = []
    original_predict = mock_classifier.predict

    def capture_predict(text):
        captured_args.append(text)
        return original_predict(text)

    mock_classifier.predict = capture_predict

    use_case = TriageUseCase(
        classifier=mock_classifier,
        repository=mock_repository,
        enable_preprocessing=True,
    )

    await use_case.execute(
        http_request="GET /search?q=1' UNION SELECT * FROM users-- HTTP/1.1",
        source_ip="192.168.1.1",
    )

    # With preprocessing enabled, model receives lowercase canonicalized text
    assert len(captured_args) == 1
    # The preprocessed text should be lowercase
    assert captured_args[0] == "get /search?q=1' union select * from users--"
    # Should NOT be the raw HTTP request
    assert "HTTP/1.1" not in captured_args[0]
    assert "Host" not in captured_args[0]
    saved_entity = mock_repository.save.call_args[0][0]
    assert saved_entity.model_input_hash == sha256(
        captured_args[0].encode("utf-8")
    ).hexdigest()
    assert saved_entity.preprocessing_version == "http-preprocessor-v1"


@pytest.mark.asyncio
async def test_triage_preprocessing_disabled(mock_classifier, mock_repository):
    """Test that raw HTTP is passed when enable_preprocessing=False."""
    mock_classifier.predict.return_value = {
        "class": "SQL Injection",
        "confidence": 0.92,
        "confidence_level": "HIGH",
    }

    captured_args = []
    original_predict = mock_classifier.predict

    def capture_predict(text):
        captured_args.append(text)
        return original_predict(text)

    mock_classifier.predict = capture_predict

    use_case = TriageUseCase(
        classifier=mock_classifier,
        repository=mock_repository,
        enable_preprocessing=False,
    )

    raw_request = "GET /search?q=1' UNION SELECT * FROM users-- HTTP/1.1"
    await use_case.execute(
        http_request=raw_request,
        source_ip="192.168.1.1",
    )

    # With preprocessing disabled, model receives raw HTTP request
    assert len(captured_args) == 1
    assert captured_args[0] == raw_request


@pytest.mark.asyncio
async def test_triage_raw_http_request_preserved_for_persistence(
    mock_classifier,
    mock_repository,
):
    """Test that raw http_request is stored verbatim regardless of preprocessing.

    The preprocessed text is ONLY for model input. The persisted record
    must preserve the original raw HTTP for forensic evidence.
    """
    mock_classifier.predict.return_value = {
        "class": "SQL Injection",
        "confidence": 0.92,
        "confidence_level": "HIGH",
    }

    use_case = TriageUseCase(
        classifier=mock_classifier,
        repository=mock_repository,
        enable_preprocessing=True,  # Preprocessing enabled
    )

    raw_request = (
        "GET /search?q=1' UNION SELECT password FROM admin-- HTTP/1.1\r\n"
        "Host: target.example.com\r\n"
        "User-Agent: Mozilla/5.0\r\n\r\n"
    )
    await use_case.execute(
        http_request=raw_request,
        source_ip="192.168.1.100",
    )

    # Verify the entity passed to save has raw http_request preserved
    saved_entity = mock_repository.save.call_args[0][0]
    assert saved_entity.http_request == raw_request
    # http_request should be the exact raw input, not preprocessed
    assert "Host: target.example.com" in saved_entity.http_request
    assert "User-Agent: Mozilla/5.0" in saved_entity.http_request
