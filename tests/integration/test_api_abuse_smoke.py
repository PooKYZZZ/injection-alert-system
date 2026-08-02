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


def test_malformed_json_returns_controlled_error_with_request_id(client):
    response = client.post(
        "/api/predict",
        content="{",
        headers={
            **INTERNAL_HEADERS,
            "Content-Type": "application/json",
            "X-Request-ID": "abuse-malformed-json",
        },
    )

    assert response.status_code in {400, 422}
    assert response.headers["X-Request-ID"] == "abuse-malformed-json"
    assert response.json()["detail"]


def test_missing_auth_returns_401_with_request_id(client):
    response = client.get(
        "/api/stats",
        headers={"X-Request-ID": "abuse-missing-auth"},
    )

    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == "abuse-missing-auth"
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_auth_is_not_logged_or_returned(client, caplog):
    invalid_token = "invalid-token-must-not-leak"

    with caplog.at_level(logging.INFO):
        response = client.get(
            "/api/stats",
            headers={
                "Authorization": f"Bearer {invalid_token}",
                "X-Request-ID": "abuse-invalid-auth",
            },
        )

    assert response.status_code == 401
    assert response.headers["X-Request-ID"] == "abuse-invalid-auth"
    assert invalid_token not in response.text
    assert invalid_token not in caplog.text
    assert "Authorization" not in caplog.text
    assert "API_SECRET_KEY" not in caplog.text


def test_invalid_triage_update_returns_422_with_request_id(client):
    response = client.patch(
        "/api/alerts/1/triage",
        json={"triage_status": "not-a-valid-status"},
        headers={
            **INTERNAL_HEADERS,
            "X-Request-ID": "abuse-invalid-triage",
        },
    )

    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == "abuse-invalid-triage"
    assert response.json()["detail"]


def test_label_review_rejects_superseded_client_action_and_unknown_fields(client):
    response = client.post(
        "/api/alerts/1/label-review",
        json={
            "verified_label": "Normal",
            "approval_state": "superseded",
            "reviewer_id": "spoofed@example.com",
        },
        headers={
            **INTERNAL_HEADERS,
            "X-Request-ID": "abuse-label-review",
            "X-Reviewer-Id": "analyst-1",
            "X-Reviewer-Role": "ANALYST",
        },
    )
    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == "abuse-label-review"


def test_label_review_rejects_superseded_as_invalid_request(client):
    response = client.post(
        "/api/alerts/1/label-review",
        json={
            "verified_label": "Normal",
            "approval_state": "superseded",
        },
        headers={
            **INTERNAL_HEADERS,
            "X-Reviewer-Id": "analyst-1",
            "X-Reviewer-Role": "ANALYST",
        },
    )

    assert response.status_code == 422
