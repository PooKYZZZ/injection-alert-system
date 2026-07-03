"""Request and trace correlation middleware."""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from web_app.observability.context import (
    generate_request_id,
    generate_trace_id,
    is_valid_request_id,
    parse_traceparent,
    reset_request_context,
    set_request_context,
)
from web_app.observability.structured_logging import log_event

logger = logging.getLogger(__name__)
REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach correlation IDs to request execution, responses, and logs."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        incoming_request_id = request.headers.get(REQUEST_ID_HEADER)
        request_id = (
            incoming_request_id
            if is_valid_request_id(incoming_request_id)
            else generate_request_id()
        )
        parsed_traceparent = parse_traceparent(request.headers.get("traceparent"))
        if parsed_traceparent is None:
            trace_id = generate_trace_id()
            span_id = None
        else:
            trace_id, span_id = parsed_traceparent

        request.state.request_id = request_id
        request.state.trace_id = trace_id
        if span_id is not None:
            request.state.span_id = span_id

        tokens = set_request_context(
            request_id=request_id,
            trace_id=trace_id,
            span_id=span_id,
        )
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers[REQUEST_ID_HEADER] = request_id
            log_event(
                logger,
                "request.completed",
                "Request completed",
                route=_route_path(request),
                method=request.method,
                status_code=response.status_code,
                duration_ms=_duration_ms(started_at),
            )
            return response
        except Exception as exc:
            log_event(
                logger,
                "request.failed",
                "Request failed",
                level="ERROR",
                route=_route_path(request),
                method=request.method,
                status_code=500,
                duration_ms=_duration_ms(started_at),
                error_type=type(exc).__name__,
                error_message="Request failed",
            )
            raise
        finally:
            reset_request_context(tokens)


def _route_path(request: Request) -> str:
    return request.url.path


def _duration_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 3)
