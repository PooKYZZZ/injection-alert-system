"""Framework-level exception responses for presentation-layer failures."""

from fastapi import Request
from starlette.responses import PlainTextResponse

from web_app.observability.context import generate_request_id
from web_app.presentation.middleware.request_context import REQUEST_ID_HEADER


async def unhandled_exception_handler(
    request: Request,
    _exc: Exception,
) -> PlainTextResponse:
    """Return a generic correlated response for an unhandled exception."""
    request_id = getattr(request.state, "request_id", None) or generate_request_id()
    return PlainTextResponse(
        "Internal Server Error",
        status_code=500,
        headers={REQUEST_ID_HEADER: request_id},
    )
