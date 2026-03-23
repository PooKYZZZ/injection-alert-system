"""
web_app/presentation/middleware/security_headers.py

Security headers middleware — stamps browser-hardening headers on every
outgoing FastAPI response, including early responses returned by inner
presentation-layer middleware.

Architectural role:
  - Presentation-layer middleware (Starlette BaseHTTPMiddleware)
  - Outermost custom middleware in the stack, wrapping body_limit and CORS

Dependency rule:
  - No imports from application/, infrastructure/, or domain layers
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to every outgoing response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=(), payment=()"
        )
        return response
