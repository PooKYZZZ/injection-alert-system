from fastapi.testclient import TestClient

from web_app.presentation.app import create_app


def test_production_preflight_allows_request_and_trace_headers(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "ALLOWED_ORIGINS", '["https://dashboard.example.test"]'
    )
    from web_app.config import get_settings

    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        response = client.options(
            "/api/health",
            headers={
                "Origin": "https://dashboard.example.test",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": (
                    "x-request-id, traceparent, tracestate"
                ),
            },
        )
    finally:
        get_settings.cache_clear()

    assert response.status_code == 200
    allowed = {
        value.strip().lower()
        for value in response.headers["access-control-allow-headers"].split(",")
    }
    assert {"x-request-id", "traceparent", "tracestate"} <= allowed
    assert (
        response.headers["access-control-allow-origin"]
        == "https://dashboard.example.test"
    )
    assert response.headers["access-control-allow-origin"] != "*"


def test_request_id_is_exposed_to_allowed_browser_origin(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "ALLOWED_ORIGINS", '["https://dashboard.example.test"]'
    )
    from web_app.config import get_settings

    get_settings.cache_clear()
    try:
        client = TestClient(create_app())
        response = client.get(
            "/api/health",
            headers={
                "Origin": "https://dashboard.example.test",
                "X-Request-ID": "cors-request-id",
            },
        )
    finally:
        get_settings.cache_clear()

    exposed = {
        value.strip().lower()
        for value in response.headers["access-control-expose-headers"].split(",")
    }
    assert "x-request-id" in exposed
    assert response.headers["X-Request-ID"] == "cors-request-id"
