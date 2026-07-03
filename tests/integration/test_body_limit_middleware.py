import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.types import Message

from web_app.presentation.app import create_app
from web_app.presentation.middleware.body_limit import (
    MAX_BODY_SIZE,
    BodySizeLimitMiddleware,
)


def test_body_limit_rejects_oversized_content_length() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/health",
            headers={"content-length": "2000000"},
            content="x",
        )

    assert response.status_code == 413
    assert response.headers["X-Request-ID"]
    assert response.json() == {
        "detail": "Request body too large. Maximum allowed size is 1 MB."
    }
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert response.headers["permissions-policy"] == (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )


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
    assert response.headers["permissions-policy"] == (
        "camera=(), microphone=(), geolocation=(), payment=()"
    )


def test_body_limit_rejects_negative_content_length_with_client_error() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.post(
            "/health",
            headers={"content-length": "-1"},
            content="x",
        )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid Content-Length header."}


def test_request_without_content_length_reaches_route_handler() -> None:
    app = create_app()

    with TestClient(app) as client:
        response = client.post("/health")

    assert response.status_code == 405


def test_request_context_middleware_is_the_outermost_custom_middleware() -> None:
    app = create_app()

    names = [mw.cls.__name__ for mw in app.user_middleware]

    assert names[:4] == [
        "RequestContextMiddleware",
        "SecurityHeadersMiddleware",
        "BodySizeLimitMiddleware",
        "CORSMiddleware",
    ]


@pytest.mark.asyncio
async def test_body_limit_rejects_streaming_body_without_content_length() -> None:
    async def read_body(request: Request) -> PlainTextResponse:
        await request.body()
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/upload", read_body, methods=["POST"])])
    wrapped = BodySizeLimitMiddleware(app)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/upload",
        "raw_path": b"/upload",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    receive_messages = [
        {
            "type": "http.request",
            "body": b"x" * (MAX_BODY_SIZE // 2),
            "more_body": True,
        },
        {
            "type": "http.request",
            "body": b"x" * (MAX_BODY_SIZE // 2 + 1),
            "more_body": False,
        },
    ]
    sent: list[Message] = []

    async def receive() -> Message:
        return receive_messages.pop(0)

    async def send(message: Message) -> None:
        sent.append(message)

    await wrapped(scope, receive, send)

    start = next(message for message in sent if message["type"] == "http.response.start")
    assert start["status"] == 413


@pytest.mark.asyncio
async def test_body_limit_rejects_streaming_body_before_route_processes_partial_json() -> None:
    route_called = False

    async def read_json(request: Request) -> PlainTextResponse:
        nonlocal route_called
        route_called = True
        await request.json()
        return PlainTextResponse("processed")

    app = Starlette(routes=[Route("/upload", read_json, methods=["POST"])])
    wrapped = BodySizeLimitMiddleware(app)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/upload",
        "raw_path": b"/upload",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    receive_messages = [
        {
            "type": "http.request",
            "body": b'{"ok": true}',
            "more_body": True,
        },
        {
            "type": "http.request",
            "body": b"x" * (MAX_BODY_SIZE + 1),
            "more_body": False,
        },
    ]
    sent: list[Message] = []

    async def receive() -> Message:
        return receive_messages.pop(0)

    async def send(message: Message) -> None:
        sent.append(message)

    await wrapped(scope, receive, send)

    start = next(message for message in sent if message["type"] == "http.response.start")
    assert start["status"] == 413
    assert route_called is False
    assert not any(
        message.get("body") == b"processed"
        for message in sent
        if message["type"] == "http.response.body"
    )


@pytest.mark.asyncio
async def test_body_limit_replays_under_limit_streaming_body_to_route() -> None:
    route_body = b""

    async def read_body(request: Request) -> PlainTextResponse:
        nonlocal route_body
        route_body = await request.body()
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/upload", read_body, methods=["POST"])])
    wrapped = BodySizeLimitMiddleware(app)
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/upload",
        "raw_path": b"/upload",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    receive_messages = [
        {
            "type": "http.request",
            "body": b'{"ok":',
            "more_body": True,
        },
        {
            "type": "http.request",
            "body": b" true}",
            "more_body": False,
        },
    ]
    sent: list[Message] = []

    async def receive() -> Message:
        return receive_messages.pop(0)

    async def send(message: Message) -> None:
        sent.append(message)

    await wrapped(scope, receive, send)

    start = next(message for message in sent if message["type"] == "http.response.start")
    assert start["status"] == 200
    assert route_body == b'{"ok": true}'
