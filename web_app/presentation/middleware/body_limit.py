"""
web_app/presentation/middleware/body_limit.py

Body size limit middleware — rejects requests whose body exceeds 1 MB,
including streamed requests without Content-Length.

Architectural role:
  - Presentation-layer ASGI middleware
  - Inner presentation-layer middleware wrapped by security headers and CORS

Dependency rule:
  - No imports from application/, infrastructure/, or domain layers
"""

from collections.abc import Awaitable, Callable

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

MAX_BODY_SIZE = 1_048_576  # 1 MB


class BodySizeLimitMiddleware:
    """Reject requests whose body exceeds 1 MB with HTTP 413."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        content_length = headers.get("content-length")
        if content_length is not None:
            response = self._response_for_content_length(content_length)
            if response is not None:
                await response(scope, receive, send)
                return

        exceeded = False
        total_size = 0

        async def limited_receive() -> Message:
            nonlocal exceeded, total_size
            message = await receive()
            if message["type"] != "http.request" or exceeded:
                return message

            total_size += len(message.get("body", b""))
            if total_size <= MAX_BODY_SIZE:
                return message

            exceeded = True
            return {
                "type": "http.request",
                "body": b"",
                "more_body": False,
            }

        async def guarded_send(message: Message) -> None:
            if exceeded:
                return
            await send(message)

        await self.app(scope, limited_receive, guarded_send)
        if exceeded:
            await self._too_large_response()(scope, receive, send)

    @staticmethod
    def _response_for_content_length(
        content_length: str,
    ) -> Callable[[Scope, Receive, Send], Awaitable[None]] | None:
        try:
            parsed_content_length = int(content_length)
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header."},
            )

        if parsed_content_length < 0:
            return JSONResponse(
                status_code=400,
                content={"detail": "Invalid Content-Length header."},
            )

        if parsed_content_length > MAX_BODY_SIZE:
            return BodySizeLimitMiddleware._too_large_response()

        return None

    @staticmethod
    def _too_large_response() -> JSONResponse:
        return JSONResponse(
            status_code=413,
            content={
                "detail": "Request body too large. Maximum allowed size is 1 MB."
            },
        )
