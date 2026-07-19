from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from web_app.application.triage_use_case import ModelNotReadyError
import web_app.application.waf_ingest_use_case as waf_ingest_use_case_module
from web_app.application.waf_ingest_use_case import WafIngestUseCase
from web_app.domain.source_address import (
    SourceProvenance,
    SourceVerificationStatus,
)


def _completed(**kwargs):
    return Mock(**kwargs), True


@pytest.mark.asyncio
async def test_ingest_classifies_and_persists_waf_event():
    classifier = Mock()
    classifier.loaded = True
    classifier.model_version = "distilbert_test"
    classifier.predict.return_value = {
        "prediction": "SQL Injection",
        "confidence": 0.91,
        "confidence_level": "HIGH",
        "model_version": "distilbert_test",
    }

    repository = AsyncMock()
    repository.claim_or_reclaim_processing.return_value = Mock(
        id=1,
        status="PROCESSING",
        processing_owner_token="owner",
    )
    repository.complete_processing.return_value = _completed(
        id=1,
        prediction="SQL Injection",
        confidence=0.91,
        confidence_level="HIGH",
        action_taken="BLOCKED",
        model_version="distilbert_test",
    )

    use_case = WafIngestUseCase(classifier=classifier, repository=repository)

    result = await use_case.execute(
        transaction_id="tx-waf-001",
        timestamp=datetime(2026, 3, 24, 10, 0, 0, tzinfo=timezone.utc),
        source_ip="203.0.113.10",
        request_method="GET",
        request_path="/login",
        request_headers={"user-agent": "curl/8.0"},
        sanitized_body="",
        crs_score=8,
        crs_rule_ids=["942100"],
    )

    assert result.action_taken == "BLOCKED"
    assert result.prediction == "SQL Injection"
    assert result.confidence == pytest.approx(0.91)
    assert result.confidence_level == "HIGH"


@pytest.mark.asyncio
async def test_ingest_builds_http_request_from_structured_fields():
    classifier = Mock()
    classifier.loaded = True
    classifier.model_version = "test"
    classifier.predict.return_value = {
        "prediction": "Normal",
        "confidence": 0.3,
        "confidence_level": "LOW",
    }

    repository = AsyncMock()
    repository.claim_or_reclaim_processing.return_value = Mock(
        id=1, status="PROCESSING", processing_owner_token="owner"
    )
    repository.complete_processing.return_value = _completed(
        id=1,
        prediction="Normal",
        confidence=0.3,
        confidence_level="LOW",
        action_taken="ALLOWED",
        model_version="test",
    )

    use_case = WafIngestUseCase(classifier=classifier, repository=repository)

    await use_case.execute(
        transaction_id="tx-waf-002",
        timestamp=datetime(2026, 3, 24, 10, 0, 0, tzinfo=timezone.utc),
        source_ip="203.0.113.10",
        request_method="POST",
        request_path="/api/login",
        request_headers={"user-agent": "curl/8.0"},
        sanitized_body="user=admin&pass=test",
        crs_score=3,
        crs_rule_ids=["942100"],
        query_string="debug=true",
    )

    classifier.predict.assert_called_once()
    http_request_arg = classifier.predict.call_args[0][0]
    assert "post" in http_request_arg.lower()
    assert "/api/login" in http_request_arg
    saved_entity = repository.claim_or_reclaim_processing.call_args[0][0]
    assert "debug=true" not in saved_entity.http_request
    assert "POST /api/login HTTP/1.1" in saved_entity.http_request


@pytest.mark.asyncio
async def test_ingest_rejects_model_not_ready():
    classifier = Mock()
    classifier.loaded = False

    repository = AsyncMock()
    repository.claim_or_reclaim_processing.return_value = Mock(
        id=1, status="PROCESSING", processing_owner_token="owner"
    )

    use_case = WafIngestUseCase(classifier=classifier, repository=repository)

    with pytest.raises(ModelNotReadyError):
        await use_case.execute(
            transaction_id="tx-waf-003",
            timestamp=datetime(2026, 3, 24, 10, 0, 0, tzinfo=timezone.utc),
            source_ip="203.0.113.10",
            request_method="GET",
            request_path="/login",
            request_headers={},
            sanitized_body="",
            crs_score=5,
            crs_rule_ids=["942100"],
        )


@pytest.mark.asyncio
async def test_ingest_applies_action_policy():
    classifier = Mock()
    classifier.loaded = True
    classifier.model_version = "test"

    repository = AsyncMock()
    repository.claim_or_reclaim_processing.return_value = Mock(
        id=1, status="PROCESSING", processing_owner_token="owner"
    )

    use_case = WafIngestUseCase(classifier=classifier, repository=repository)

    for confidence_level, expected_action in [
        ("HIGH", "BLOCKED"),
        ("MEDIUM", "THROTTLED"),
        ("LOW", "ALLOWED"),
    ]:
        classifier.predict.return_value = {
            "prediction": "SQL Injection",
            "confidence": 0.9
            if confidence_level == "HIGH"
            else 0.6
            if confidence_level == "MEDIUM"
            else 0.3,
            "confidence_level": confidence_level,
        }

        repository.complete_processing.return_value = _completed(
            id=1,
            prediction="SQL Injection",
            confidence=0.9,
            confidence_level=confidence_level,
            action_taken=expected_action,
            model_version="test",
        )

        result = await use_case.execute(
            transaction_id=f"tx-waf-policy-{confidence_level}",
            timestamp=datetime(2026, 3, 24, 10, 0, 0, tzinfo=timezone.utc),
            source_ip="203.0.113.10",
            request_method="GET",
            request_path="/login",
            request_headers={},
            sanitized_body="",
            crs_score=10,
            crs_rule_ids=["942100"],
        )

        assert result.action_taken == expected_action


@pytest.mark.asyncio
async def test_ingest_derives_status_and_fingerprints_sanitized_factual_input():
    classifier = Mock()
    classifier.loaded = True
    classifier.model_version = "test"
    classifier.predict.return_value = {
        "prediction": "Normal",
        "confidence": 0.3,
        "confidence_level": "LOW",
    }
    repository = AsyncMock()

    async def _claim(entity, *, owner_token, **_kwargs):
        entity.id = 1
        entity.processing_owner_token = owner_token
        return entity

    repository.claim_or_reclaim_processing.side_effect = _claim
    repository.complete_processing.return_value = _completed(
        id=1,
        prediction="Normal",
        confidence=0.3,
        confidence_level="LOW",
        action_taken="ALLOWED",
        model_version="test",
    )
    use_case = WafIngestUseCase(
        classifier=classifier,
        repository=repository,
        source_verification_mode="cloudflare_tunnel",
    )

    await use_case.execute(
        transaction_id="tx-source-evidence",
        timestamp=None,
        source_ip="203.0.113.10",
        source_provenance=SourceProvenance.CLOUDFLARE_CONNECTING_IP,
        cf_connecting_ip_matches_client_ip=True,
        request_method="POST",
        request_path="/login",
        request_headers={"Authorization": "Bearer secret", "X-Test": " one "},
        sanitized_body="password=secret",
        crs_score=8,
        crs_rule_ids=["949110", "942100"],
    )

    entity = repository.claim_or_reclaim_processing.call_args.args[0]
    assert entity.source_verification_status is SourceVerificationStatus.VERIFIED
    assert entity.source_provenance is SourceProvenance.CLOUDFLARE_CONNECTING_IP
    assert entity.ingest_fingerprint_sha256 is not None
    assert len(entity.ingest_fingerprint_sha256) == 64
    assert "secret" not in entity.http_request


@pytest.mark.asyncio
async def test_cloudflare_mode_accepts_direct_evidence_as_unverified_and_warns(
    monkeypatch,
):
    classifier = Mock()
    classifier.loaded = True
    classifier.model_version = "test"
    classifier.predict.return_value = {
        "prediction": "Normal",
        "confidence": 0.3,
        "confidence_level": "LOW",
    }
    repository = AsyncMock()

    async def _claim(entity, *, owner_token, **_kwargs):
        entity.id = 1
        entity.processing_owner_token = owner_token
        return entity

    repository.claim_or_reclaim_processing.side_effect = _claim
    repository.complete_processing.return_value = _completed(
        id=1,
        prediction="Normal",
        confidence=0.3,
        confidence_level="LOW",
        action_taken="ALLOWED",
        model_version="test",
    )
    logged: list[dict[str, object]] = []
    monkeypatch.setattr(
        waf_ingest_use_case_module,
        "log_event",
        lambda *args, **kwargs: logged.append(kwargs | {"event": args[1]}),
    )
    use_case = WafIngestUseCase(
        classifier=classifier,
        repository=repository,
        source_verification_mode="cloudflare_tunnel",
    )

    await use_case.execute(
        transaction_id="tx-incompatible-provenance",
        timestamp=None,
        source_ip="203.0.113.10",
        source_provenance=SourceProvenance.DIRECT_REMOTE_ADDR,
        cf_connecting_ip_matches_client_ip=None,
        request_method="GET",
        request_path="/",
        request_headers={"Authorization": "Bearer must-not-log"},
        sanitized_body="password=must-not-log",
        crs_score=0,
        crs_rule_ids=["unknown-rule"],
    )

    entity = repository.claim_or_reclaim_processing.call_args.args[0]
    assert entity.source_provenance is SourceProvenance.DIRECT_REMOTE_ADDR
    assert entity.source_verification_status is SourceVerificationStatus.UNVERIFIED
    assert logged == [
        {
            "level": "WARNING",
            "transaction_id": "tx-incompatible-provenance",
            "verification_mode": "cloudflare_tunnel",
            "source_provenance": "DIRECT_REMOTE_ADDR",
            "event": "source_provenance_mode_mismatch",
        }
    ]
    assert "must-not-log" not in repr(logged)
