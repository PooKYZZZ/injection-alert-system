import pytest
from pydantic import ValidationError
from web_app.presentation.schemas import (
    PredictionRequest,
    PredictionResponse,
    FeedbackRequest,
    AlertResponse,
    HealthResponse,
    TriageIngestRequest,
    TriageIngestResponse,
)


def test_prediction_request_validation():
    """Test PredictionRequest schema validation"""
    request = PredictionRequest(http_request="SELECT * FROM users")
    assert request.http_request == "SELECT * FROM users"


def test_prediction_request_empty_string():
    """Test PredictionRequest accepts empty strings"""
    request = PredictionRequest(http_request="")
    assert request.http_request == ""


def test_prediction_response_structure():
    """Test PredictionResponse has correct structure"""
    response = PredictionResponse(
        class_label="SQL Injection",
        confidence=0.92,
        confidence_level="HIGH",
        action_taken="BLOCKED"
    )
    assert response.class_label == "SQL Injection"
    assert response.confidence == 0.92
    assert response.confidence_level == "HIGH"
    assert response.action_taken == "BLOCKED"


def test_prediction_response_confidence_range():
    """Test that confidence must be in valid range"""
    # Valid confidence
    response = PredictionResponse(
        class_label="Normal",
        confidence=0.5,
        confidence_level="MEDIUM",
        action_taken="ALLOWED"
    )
    assert response.confidence == 0.5

    # Negative confidence should fail
    with pytest.raises(ValidationError):
        PredictionResponse(
            class_label="Normal",
            confidence=-0.1,
            confidence_level="LOW",
            action_taken="ALLOWED"
        )

    # Confidence > 1 should fail
    with pytest.raises(ValidationError):
        PredictionResponse(
            class_label="Normal",
            confidence=1.5,
            confidence_level="HIGH",
            action_taken="ALLOWED"
        )


def test_feedback_request_validation():
    """Test FeedbackRequest schema"""
    feedback = FeedbackRequest(
        traffic_id=1,
        correct_label="Normal",
        analyst_email="security@example.com"
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
        action_taken="BLOCKED"
    )
    assert alert.id == 1
    assert alert.source_ip == "192.168.1.1"


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
