"""
web_app/presentation/middleware/body_limit.py

Body size limit middleware — rejects requests with Content-Length exceeding 1 MB
before the request body is read, returning HTTP 413 with a JSON error body.
Requests without Content-Length are allowed through and must rely on edge-layer
body-size enforcement for complete protection.

Architectural role:
  - Presentation-layer middleware (Starlette BaseHTTPMiddleware)
  - Inner presentation-layer middleware wrapped by security headers and CORS

Dependency rule:
  - No imports from application/, infrastructure/, or domain layers
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

MAX_BODY_SIZE = 1_048_576  # 1 MB


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds 1 MB with HTTP 413."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is None:
            return await call_next(request)

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
            return JSONResponse(
                status_code=413,
                content={
                    "detail": "Request body too large. Maximum allowed size is 1 MB."
                },
            )

        return await call_next(request)
