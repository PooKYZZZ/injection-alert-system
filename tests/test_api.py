import pytest
from fastapi.testclient import TestClient
from web_app.app import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint returns status"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "database" in data


def test_predict_endpoint_sql_injection():
    """Test prediction endpoint with SQL injection payload"""
    response = client.post(
        "/api/predict",
        json={"http_request": "SELECT * FROM users WHERE id=1 OR 1=1"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "class_label" in data
    assert "confidence" in data
    assert "confidence_level" in data
    assert data["class_label"] == "SQL Injection"


def test_predict_endpoint_code_injection():
    """Test prediction endpoint with code injection payload"""
    response = client.post(
        "/api/predict",
        json={"http_request": "<script>alert('XSS')</script>"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["class_label"] == "Code Injection"


def test_predict_endpoint_normal_request():
    """Test prediction endpoint with normal request"""
    response = client.post(
        "/api/predict",
        json={"http_request": "GET /api/users?page=1&limit=10"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["class_label"] == "Normal"


def test_predict_endpoint_missing_request():
    """Test prediction endpoint with missing http_request"""
    response = client.post("/api/predict", json={})
    assert response.status_code == 422  # Validation error


def test_alerts_endpoint_empty():
    """Test alerts endpoint returns empty list when no data"""
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_alerts_endpoint_with_data():
    """Test alerts endpoint returns stored alerts"""
    # First make a prediction to create a log
    client.post(
        "/api/predict",
        json={"http_request": "SELECT * FROM users; DROP TABLE users;--"}
    )
    response = client.get("/api/alerts")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_feedback_endpoint():
    """Test feedback endpoint stores analyst correction"""
    # First create a prediction
    predict_response = client.post(
        "/api/predict",
        json={"http_request": "GET /api/test"}
    )

    # Get the traffic log id from alerts
    alerts_response = client.get("/api/alerts")
    alerts = alerts_response.json()

    if alerts:
        traffic_id = alerts[0]["id"]
        feedback_response = client.post(
            "/api/feedback",
            json={
                "traffic_id": traffic_id,
                "correct_label": "Normal",
                "analyst_email": "test@example.com"
            }
        )
        assert feedback_response.status_code == 200
