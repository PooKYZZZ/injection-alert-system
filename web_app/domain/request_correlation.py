"""Validation helpers for trusted request-correlation identifiers."""

from __future__ import annotations

import re

_REQUEST_CORRELATION_ID = re.compile(
    r"^(?:[0-9a-f]{32}|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$",
    re.IGNORECASE,
)


def normalize_request_correlation_id(value: object) -> str | None:
    """Return a normalized NGINX request ID or UUID, otherwise ``None``."""

    if not isinstance(value, str):
        return None
    candidate = value.strip().lower()
    if not _REQUEST_CORRELATION_ID.fullmatch(candidate):
        return None
    return candidate
