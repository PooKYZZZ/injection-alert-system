from fastapi.testclient import TestClient

from web_app.presentation.app import create_app


def test_body_limit_rejects_oversized_content_length() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/health",
            headers={"content-length": "2000000"},
            content="x",
        )

    assert response.status_code == 413
    assert response.json() == {
        "detail": "Request body too large. Maximum allowed size is 1 MB."
    }
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"


def test_body_limit_rejects_non_numeric_content_length_with_client_error() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/health",
            headers={"content-length": "abc"},
            content="x",
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Content-Length header."}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"


def test_request_without_content_length_reaches_route_handler() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.post("/health")

    assert response.status_code == 405


def test_security_headers_middleware_is_the_outermost_custom_middleware() -> None:
    app = create_app()

    names = [mw.cls.__name__ for mw in app.user_middleware]

    assert names[:3] == [
        "SecurityHeadersMiddleware",
        "BodySizeLimitMiddleware",
        "CORSMiddleware",
    ]
