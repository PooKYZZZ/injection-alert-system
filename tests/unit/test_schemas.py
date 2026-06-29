from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from web_app.presentation.schemas import (
    AlertDetailResponse,
    AlertResponse,
    FeedbackRequest,
    HealthResponse,
    PredictionRequest,
    PredictionResponse,
    TriageIngestRequest,
    TriageIngestResponse,
)


def test_prediction_request_validation():
    """Test PredictionRequest schema validation"""
    request = PredictionRequest(http_request="SELECT * FROM users")
    assert request.http_request == "SELECT * FROM users"


def test_prediction_request_empty_string():
    """Test PredictionRequest rejects empty strings"""
    with pytest.raises(Exception):
        PredictionRequest(http_request="")


def test_prediction_response_structure():
    """Test PredictionResponse has correct structure"""
    response = PredictionResponse(
        class_label="SQL Injection",
        confidence=0.92,
        confidence_level="HIGH",
        action_taken="BLOCKED",
    )
    assert response.class_label == "SQL Injection"
    assert response.confidence == 0.92
    assert response.confidence_level == "HIGH"
    assert response.action_taken == "BLOCKED"


def test_prediction_response_accepts_critical_confidence_level():
    response = PredictionResponse(
        class_label="SQL Injection",
        confidence=0.95,
        confidence_level="CRITICAL",
        action_taken="BLOCKED",
    )

    assert response.confidence_level == "CRITICAL"


def test_prediction_response_confidence_range():
    """Test that confidence must be in valid range"""
    # Valid confidence
    response = PredictionResponse(
        class_label="Normal",
        confidence=0.5,
        confidence_level="MEDIUM",
        action_taken="ALLOWED",
    )
    assert response.confidence == 0.5

    # Negative confidence should fail
    with pytest.raises(ValidationError):
        PredictionResponse(
            class_label="Normal",
            confidence=-0.1,
            confidence_level="LOW",
            action_taken="ALLOWED",
        )

    # Confidence > 1 should fail
    with pytest.raises(ValidationError):
        PredictionResponse(
            class_label="Normal",
            confidence=1.5,
            confidence_level="HIGH",
            action_taken="ALLOWED",
        )


def test_feedback_request_validation():
    """Test FeedbackRequest schema"""
    feedback = FeedbackRequest(
        traffic_id=1, correct_label="Normal", analyst_email="security@example.com"
    )
    assert feedback.traffic_id == 1
    assert feedback.correct_label == "Normal"


def test_alert_response_structure():
    """Test AlertResponse includes all traffic log fields"""
    from datetime import datetime

    alert = AlertResponse(
        id=1,
        timestamp=datetime.now(),
        source_ip="192.168.1.1",
        http_request="GET /api/test",
        prediction="SQL Injection",
        confidence=0.88,
        confidence_level="HIGH",
        action_taken="BLOCKED",
    )
    assert alert.id == 1
    assert alert.source_ip == "192.168.1.1"


def test_alert_response_accepts_critical_confidence_level():
    alert = AlertResponse(
        id=1,
        timestamp=datetime.now(),
        source_ip="192.168.1.1",
        http_request="GET /api/test",
        prediction="SQL Injection",
        confidence=0.95,
        confidence_level="CRITICAL",
        action_taken="BLOCKED",
    )
    assert alert.confidence_level == "CRITICAL"


def test_health_response():
    """Test HealthResponse schema"""
    health = HealthResponse(status="healthy", database="connected")
    assert health.status == "healthy"


def test_triage_ingest_request_structure():
    request = TriageIngestRequest(
        transaction_id="txn-123",
        timestamp="2026-03-15T10:00:00Z",
        source_ip="203.0.113.10",
        request_method="POST",
        request_uri="/login",
        request_headers={"Host": "example.test"},
        request_body="username=admin",
        http_request="POST /login HTTP/1.1",
        crs_score=7,
        crs_rule_ids=["942100"],
    )
    assert request.transaction_id == "txn-123"
    assert request.request_headers["Host"] == "example.test"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_ip", "x" * 46),
        ("request_method", ""),
        ("request_uri", "/" + ("x" * 2048)),
        ("request_body", "x" * 65537),
        ("http_request", "x" * 65537),
        ("crs_score", -1),
        ("crs_rule_ids", []),
        ("crs_rule_ids", ["942100"] * 33),
        ("crs_rule_ids", [""]),
        ("crs_rule_ids", ["9" * 129]),
    ],
    ids=[
        "source-ip-too-long",
        "empty-method",
        "uri-too-long",
        "body-too-long",
        "http-request-too-long",
        "negative-crs-score",
        "empty-rule-list",
        "too-many-rules",
        "empty-rule-id",
        "rule-id-too-long",
    ],
)
def test_triage_ingest_request_rejects_weak_legacy_fields(field, value):
    payload = {
        "transaction_id": "txn-123",
        "timestamp": "2026-03-15T10:00:00Z",
        "source_ip": "203.0.113.10",
        "request_method": "POST",
        "request_uri": "/login",
        "request_headers": {"Host": "example.test"},
        "request_body": "username=admin",
        "http_request": "POST /login HTTP/1.1",
        "crs_score": 7,
        "crs_rule_ids": ["942100"],
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        TriageIngestRequest(**payload)


def test_triage_ingest_response_structure():
    response = TriageIngestResponse(
        alert_id=1,
        prediction="SQL Injection",
        confidence=0.92,
        confidence_level="HIGH",
        action_taken="BLOCKED",
        model_version="distilbert_v1",
    )
    assert response.alert_id == 1
    assert response.prediction == "SQL Injection"


def test_triage_ingest_response_accepts_critical_confidence_level():
    response = TriageIngestResponse(
        alert_id=1,
        prediction="SQL Injection",
        confidence=0.95,
        confidence_level="CRITICAL",
        action_taken="BLOCKED",
        model_version="distilbert_v1",
    )
    assert response.confidence_level == "CRITICAL"


def test_alert_detail_response_supports_optional_crs_and_review_fields():
    alert = AlertDetailResponse(
        id=1,
        timestamp="2026-03-15T10:00:00Z",
        source_ip="203.0.113.10",
        request_path="/login",
        request_method="POST",
        payload_snippet="payload",
        prediction="SQL Injection",
        confidence=0.92,
        confidence_level="HIGH",
        action_taken="BLOCKED",
        crs_score=9,
        crs_rule_ids=["942100", "942110"],
        analyst_label="Normal",
        labeled_at="2026-03-15T10:05:00Z",
        labeled_by="analyst@example.com",
    )
    assert alert.crs_rule_ids == ["942100", "942110"]
    assert alert.analyst_label == "Normal"
    assert alert.labeled_by == "analyst@example.com"


def test_alert_detail_response_serializes_labeled_at_as_utc_rfc3339():
    alert = AlertDetailResponse(
        id=1,
        timestamp="2026-03-15T10:00:00Z",
        payload_snippet="payload",
        prediction="SQL Injection",
        confidence=0.92,
        confidence_level="HIGH",
        labeled_at=datetime(2026, 3, 15, 10, 5),
    )

    assert alert.model_dump(mode="json")["labeled_at"] == "2026-03-15T10:05:00Z"


def test_alert_detail_response_converts_aware_labeled_at_to_utc_rfc3339():
    alert = AlertDetailResponse(
        id=1,
        timestamp="2026-03-15T10:00:00Z",
        payload_snippet="payload",
        prediction="SQL Injection",
        confidence=0.92,
        confidence_level="HIGH",
        labeled_at=datetime(2026, 3, 15, 18, 5, tzinfo=timezone(timedelta(hours=8))),
    )

    assert alert.model_dump(mode="json")["labeled_at"] == "2026-03-15T10:05:00Z"
