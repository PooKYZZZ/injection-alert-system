"""Single-line JSON logging with request correlation and redaction."""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from web_app.observability.context import (
    get_request_id,
    get_span_id,
    get_trace_id,
)
from web_app.observability.redaction import redact_for_log

_SERVICE_NAME = "cybertrace-api"
_MAX_TEXT_LENGTH = 1024
_VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _safe_text(value: Any) -> str:
    try:
        return str(value)[:_MAX_TEXT_LENGTH]
    except Exception:
        return f"<unprintable {type(value).__name__}>"


def _resolve_level(level: str) -> tuple[str, int]:
    level_name = _safe_text(level).upper()
    if level_name not in _VALID_LEVELS:
        return "INFO", logging.INFO
    return level_name, getattr(logging, level_name)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def log_event(
    logger: logging.Logger,
    event: str,
    message: str,
    level: str = "INFO",
    component: str = "fastapi",
    **fields: Any,
) -> None:
    """Emit one safe JSON log record without affecting request flow on failure."""
    try:
        level_name, level_number = _resolve_level(level)
        payload = redact_for_log(fields)
        payload.update(
            {
                "timestamp": _timestamp(),
                "level": level_name,
                "event": _safe_text(event),
                "message": _safe_text(message),
                "service": _SERVICE_NAME,
                "component": _safe_text(component),
                "environment": os.getenv("APP_ENV", "development"),
            }
        )

        request_id = get_request_id()
        trace_id = get_trace_id()
        span_id = get_span_id()
        if request_id is not None:
            payload["request_id"] = request_id
        if trace_id is not None:
            payload["trace_id"] = trace_id
        if span_id is not None:
            payload["span_id"] = span_id

        try:
            serialized = json.dumps(
                payload,
                default=str,
                separators=(",", ":"),
            )
        except Exception:
            serialized = json.dumps(
                {
                    "timestamp": _timestamp(),
                    "level": level_name,
                    "event": "logging.serialization_failed",
                    "message": "Structured log serialization failed",
                    "service": _SERVICE_NAME,
                    "component": "logging",
                    "environment": os.getenv("APP_ENV", "development"),
                },
                separators=(",", ":"),
            )
        logger.log(level_number, serialized)
    except Exception:
        return
