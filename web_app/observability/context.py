"""Request-scoped correlation identifiers."""

import re
from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import uuid4

_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_TRACEPARENT_PATTERN = re.compile(
    r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$"
)

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_id_var: ContextVar[str | None] = ContextVar("span_id", default=None)


@dataclass(frozen=True)
class RequestContextTokens:
    """Tokens required to restore the previous request context."""

    request_id: Token[str | None]
    trace_id: Token[str | None]
    span_id: Token[str | None]


def get_request_id() -> str | None:
    return _request_id_var.get()


def get_trace_id() -> str | None:
    return _trace_id_var.get()


def get_span_id() -> str | None:
    return _span_id_var.get()


def set_request_context(
    *,
    request_id: str,
    trace_id: str,
    span_id: str | None = None,
) -> RequestContextTokens:
    """Set correlation IDs and return tokens for deterministic cleanup."""
    return RequestContextTokens(
        request_id=_request_id_var.set(request_id),
        trace_id=_trace_id_var.set(trace_id),
        span_id=_span_id_var.set(span_id),
    )


def reset_request_context(tokens: RequestContextTokens) -> None:
    """Restore the context that existed before ``set_request_context``."""
    _span_id_var.reset(tokens.span_id)
    _trace_id_var.reset(tokens.trace_id)
    _request_id_var.reset(tokens.request_id)


def is_valid_request_id(value: str | None) -> bool:
    """Return whether an incoming request ID is safe to reflect and log."""
    return bool(value and _REQUEST_ID_PATTERN.fullmatch(value))


def generate_request_id() -> str:
    return f"req_{uuid4().hex}"


def generate_trace_id() -> str:
    return uuid4().hex


def parse_traceparent(value: str | None) -> tuple[str, str] | None:
    """Extract IDs from a W3C version-00 traceparent header."""
    if not value:
        return None

    match = _TRACEPARENT_PATTERN.fullmatch(value)
    if match is None:
        return None

    trace_id, span_id, _flags = match.groups()
    if trace_id == "0" * 32 or span_id == "0" * 16:
        return None
    return trace_id, span_id
