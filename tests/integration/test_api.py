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


def test_predict_endpoint_sql_injection(client):
    """Test prediction endpoint with SQL injection payload"""
    response = client.post(
        "/api/predict",
        json={"http_request": "SELECT * FROM users WHERE id=1 OR 1=1"},
        headers=INTERNAL_HEADERS,
    )
    assert response.status_code == 200
    data = response.json()
    assert "class_label" in data
    assert "confidence" in data
    assert "confidence_level" in data
    assert data["class_label"] == "SQL Injection"


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
