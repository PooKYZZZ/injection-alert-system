import json
import logging

import pytest
from fastapi.testclient import TestClient
from web_app.presentation.app import create_app

INTERNAL_HEADERS = {"Authorization": "Bearer test-secret-key"}


@pytest.fixture
def client():
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_auth_health_endpoint_is_public(client):
    """Test canonical health check endpoint returns status"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data


def test_alert_stream_requires_internal_auth_and_is_not_shadowed_by_alert_id(client):
    response = client.get("/api/alerts/stream")

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_label_review_requires_trusted_internal_auth_and_reviewer_context(client):
    response = client.post(
        "/api/alerts/1/label-review",
        json={
            "verified_label": "Normal",
            "approval_state": "approved_for_training",
        },
    )
    assert response.status_code == 401

    response = client.post(
        "/api/alerts/1/label-review",
        json={
            "verified_label": "Normal",
            "approval_state": "approved_for_training",
        },
        headers=INTERNAL_HEADERS,
    )
    assert response.status_code == 403


def test_response_includes_preserved_request_id(client):
    response = client.get(
        "/health",
        headers={"X-Request-ID": "integration-request-123"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "integration-request-123"


def test_predict_endpoint_sql_injection(client, caplog):
    """Test prediction endpoint with SQL injection payload"""
    raw_request = "SELECT * FROM users WHERE id=1 OR 1=1 /* log-secret */"
    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/predict",
            json={"http_request": raw_request},
            headers={
                **INTERNAL_HEADERS,
                "X-Request-ID": "prediction-request-001",
            },
        )
    assert response.status_code == 200
    data = response.json()
    assert "class_label" in data
    assert "confidence" in data
    assert "confidence_level" in data
    assert data["class_label"] == "SQL Injection"
    event = next(
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
        and json.loads(record.getMessage()).get("event") == "prediction.completed"
    )
    assert event["request_id"] == "prediction-request-001"
    assert event["prediction"] == "SQL Injection"
    assert event["confidence_tier"] == data["confidence_level"]
    assert event["action_taken"] == data["action_taken"]
    assert event["status_code"] == 200
    assert raw_request not in caplog.text


def test_predict_endpoint_code_injection(client):
    """Test prediction endpoint with code injection payload"""
    response = client.post(
        "/api/predict",
        json={"http_request": "<script>alert('XSS')</script>"},
        headers=INTERNAL_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["class_label"] == "Code Injection"


def test_predict_endpoint_normal_request(client):
    """Test prediction endpoint with normal request"""
    response = client.post(
        "/api/predict",
        json={"http_request": "GET /api/users?page=1&limit=10"},
        headers=INTERNAL_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["class_label"] == "Normal"


def test_predict_endpoint_missing_request(client):
    """Test prediction endpoint with missing http_request"""
    response = client.post("/api/predict", json={}, headers=INTERNAL_HEADERS)
    assert response.status_code == 422  # Validation error


def test_predict_response_has_action_taken(client):
    """Test prediction response includes action_taken field"""
    response = client.post(
        "/api/predict",
        json={"http_request": "SELECT * FROM users; DROP TABLE users;--"},
        headers=INTERNAL_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert "action_taken" in data
    assert data["action_taken"] in ["BLOCKED", "THROTTLED", "ALLOWED"]


def test_alerts_endpoint_empty(client):
    """Test alerts endpoint returns empty list when no data"""
    response = client.get(
        "/api/alerts?search=__no_matching_alert__",
        headers=INTERNAL_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 20,
    }


def test_alerts_endpoint_accepts_matching_legacy_and_preferred_confidence_tier(
    client,
):
    response = client.get(
        "/api/alerts?severity=HIGH&confidence_tier=HIGH",
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200


def test_alerts_endpoint_accepts_critical_legacy_and_preferred_confidence_tier(
    client,
):
    response = client.get(
        "/api/alerts?severity=CRITICAL&confidence_tier=CRITICAL",
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200


@pytest.mark.parametrize(
    "query_string",
    [
        "confidence_tier=EXTREME",
        "severity=EXTREME",
    ],
)
def test_alerts_endpoint_rejects_invalid_confidence_tier_aliases(
    client,
    query_string,
):
    response = client.get(
        f"/api/alerts?{query_string}",
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 422
    assert response.json()["detail"]


def test_alerts_endpoint_rejects_conflicting_legacy_and_preferred_confidence_tier(
    client,
):
    response = client.get(
        "/api/alerts?severity=LOW&confidence_tier=HIGH",
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 422
    assert "severity and confidence_tier" in response.text


def test_alerts_endpoint_accepts_confidence_tier_sort_alias(client):
    response = client.get(
        "/api/alerts?sort_by=confidence_tier&sort_dir=desc",
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200


def test_ml_health_exposes_critical_threshold(client):
    response = client.get("/api/ml-health", headers=INTERNAL_HEADERS)

    assert response.status_code == 200
    data = response.json()
    assert data["confidence_thresholds"]["low"] == 0.5
    assert data["confidence_thresholds"]["high"] == 0.8
    assert data["confidence_thresholds"]["critical"] == 0.9


def test_alerts_endpoint_with_data(client):
    """Test alerts endpoint returns stored alerts"""
    # First make a prediction to create a log
    client.post(
        "/api/predict",
        json={"http_request": "SELECT * FROM users; DROP TABLE users;--"},
        headers=INTERNAL_HEADERS,
    )
    response = client.get("/api/alerts", headers=INTERNAL_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 1
    assert isinstance(data["items"], list)


def test_feedback_endpoint(client):
    """Test feedback endpoint stores analyst correction"""
    # First create a prediction
    client.post(
        "/api/predict",
        json={"http_request": "GET /api/test"},
        headers=INTERNAL_HEADERS,
    )

    # Get the traffic log id from alerts
    alerts_response = client.get("/api/alerts", headers=INTERNAL_HEADERS)
    alerts = alerts_response.json()["items"]

    if alerts:
        traffic_id = alerts[0]["id"]
        feedback_response = client.post(
            "/api/feedback",
            json={
                "traffic_id": traffic_id,
                "correct_label": "Normal",
                "analyst_email": "test@example.com",
            },
            headers=INTERNAL_HEADERS,
        )
        assert feedback_response.status_code == 200


def test_model_singleton_injection(client):
    """Test that the model service is injected from app.state, not instantiated per-request."""
    app_instance = client.app
    assert hasattr(app_instance.state, "model_service"), (
        "Model service should be loaded on app.state during lifespan"
    )


def test_update_alert_action_returns_404_for_missing_alert(client):
    """PATCH action route should map missing alert result to HTTP 404."""
    response = client.patch(
        "/api/alerts/999999/action",
        json={"action_taken": "BLOCKED"},
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 404


def test_update_alert_action_rejects_invalid_action_value(client):
    """PATCH action route should reject invalid action enum values."""
    client.post(
        "/api/predict",
        json={"http_request": "GET /api/test"},
        headers=INTERNAL_HEADERS,
    )
    alerts_response = client.get("/api/alerts", headers=INTERNAL_HEADERS)
    alert_id = alerts_response.json()["items"][0]["id"]

    response = client.patch(
        f"/api/alerts/{alert_id}/action",
        json={"action_taken": "INVALID_ACTION"},
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 422


def test_update_alert_action_updates_existing_alert(client):
    """PATCH action route should update action_taken for an existing alert."""
    client.post(
        "/api/predict",
        json={"http_request": "GET /api/profile"},
        headers=INTERNAL_HEADERS,
    )
    alerts_response = client.get("/api/alerts", headers=INTERNAL_HEADERS)
    alert_id = alerts_response.json()["items"][0]["id"]

    response = client.patch(
        f"/api/alerts/{alert_id}/action",
        json={"action_taken": "ALLOWED"},
        headers=INTERNAL_HEADERS,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == alert_id
    assert payload["action_taken"] == "ALLOWED"
