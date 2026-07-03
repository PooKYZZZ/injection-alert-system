import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient

from web_app.observability.context import (
    get_request_id,
    get_span_id,
    get_trace_id,
    is_valid_request_id,
)
from web_app.presentation.app import create_app
from web_app.presentation.exception_handlers import unhandled_exception_handler
from web_app.presentation.middleware.request_context import RequestContextMiddleware


def _log_payloads(caplog):
    return [
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    ]


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)

    @app.get("/ok")
    async def ok():
        return {
            "request_id": get_request_id(),
            "trace_id": get_trace_id(),
            "span_id": get_span_id(),
        }

    @app.get("/failed")
    async def failed():
        raise RuntimeError("unsafe request failure")

    return app


def _create_unhandled_error_app(*, error_message: str = "unsafe request failure"):
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/test-unhandled-error")
    async def unhandled_error():
        raise RuntimeError(error_message)

    return app


def test_app_registers_unhandled_exception_handler():
    app = create_app()

    assert app.exception_handlers[Exception] is unhandled_exception_handler


def test_middleware_preserves_safe_request_id_and_traceparent(caplog):
    app = _create_test_app()
    trace_id = "4bf92f3577b34da6a3ce929d0e0e4736"
    span_id = "00f067aa0ba902b7"

    with caplog.at_level(logging.INFO), TestClient(app) as client:
        response = client.get(
            "/ok?secret=must-not-be-logged",
            headers={
                "X-Request-ID": "request.safe-123",
                "traceparent": f"00-{trace_id}-{span_id}-01",
            },
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request.safe-123"
    assert response.json() == {
        "request_id": "request.safe-123",
        "trace_id": trace_id,
        "span_id": span_id,
    }
    completed = next(
        payload
        for payload in _log_payloads(caplog)
        if payload["event"] == "request.completed"
    )
    assert completed["request_id"] == "request.safe-123"
    assert completed["trace_id"] == trace_id
    assert completed["span_id"] == span_id
    assert completed["route"] == "/ok"
    assert completed["method"] == "GET"
    assert completed["status_code"] == 200
    assert completed["duration_ms"] >= 0
    assert "must-not-be-logged" not in json.dumps(completed)


def test_middleware_replaces_invalid_request_id_and_generates_trace_id():
    app = _create_test_app()

    with TestClient(app) as client:
        response = client.get("/ok", headers={"X-Request-ID": "forged\nrequest"})

    generated_request_id = response.headers["X-Request-ID"]
    assert generated_request_id != "forged\nrequest"
    assert response.json()["request_id"] == generated_request_id
    assert len(response.json()["trace_id"]) == 32
    assert response.json()["span_id"] is None


def test_middleware_logs_failure_safely_and_resets_context(caplog):
    app = _create_test_app()

    with (
        caplog.at_level(logging.ERROR),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.get("/failed", headers={"X-Request-ID": "request-failed"})

    assert response.status_code == 500
    failed = next(
        payload
        for payload in _log_payloads(caplog)
        if payload["event"] == "request.failed"
    )
    assert failed["request_id"] == "request-failed"
    assert failed["error_type"] == "RuntimeError"
    assert failed["error_message"] == "Request failed"
    assert "unsafe request failure" not in json.dumps(failed)
    assert get_request_id() is None
    assert get_trace_id() is None
    assert get_span_id() is None


def test_unhandled_500_preserves_valid_incoming_request_id():
    app = _create_unhandled_error_app()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/test-unhandled-error",
            headers={"X-Request-ID": "req-test-500"},
        )

    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "req-test-500"
    assert response.text == "Internal Server Error"


def test_unhandled_500_generates_safe_request_id_when_missing():
    app = _create_unhandled_error_app()

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-unhandled-error")

    request_id = response.headers["X-Request-ID"]
    assert response.status_code == 500
    assert request_id
    assert is_valid_request_id(request_id)


def test_unhandled_500_does_not_reflect_invalid_request_id():
    app = _create_unhandled_error_app()
    invalid_request_id = "forged\nrequest"

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/test-unhandled-error",
            headers={"X-Request-ID": invalid_request_id},
        )

    request_id = response.headers["X-Request-ID"]
    assert response.status_code == 500
    assert request_id != invalid_request_id
    assert is_valid_request_id(request_id)


def test_unhandled_500_failure_log_keeps_request_and_trace_ids(caplog):
    app = _create_unhandled_error_app()

    with (
        caplog.at_level(logging.ERROR),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.get(
            "/test-unhandled-error",
            headers={"X-Request-ID": "req-log-500"},
        )

    assert response.status_code == 500
    failed = next(
        payload
        for payload in _log_payloads(caplog)
        if payload["event"] == "request.failed"
    )
    assert failed["request_id"] == "req-log-500"
    assert len(failed["trace_id"]) == 32


def test_unhandled_500_does_not_leak_exception_secret(caplog):
    secret = "super-secret-value"
    app = _create_unhandled_error_app(error_message=f"boom token={secret}")

    with (
        caplog.at_level(logging.ERROR),
        TestClient(app, raise_server_exceptions=False) as client,
    ):
        response = client.get("/test-unhandled-error")

    assert response.status_code == 500
    assert secret not in response.text
    assert secret not in caplog.text
