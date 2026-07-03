"""Safe, non-mutating redaction for structured log fields."""

from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"
_MAX_VALUE_LENGTH = 1024
_MAX_DEPTH = 10
_SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "set_cookie",
    "x_api_key",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "password",
    "passwd",
    "pwd",
    "secret",
    "credential",
    "private_key",
    "session",
    "session_id",
    "database_url",
    "db_url",
    "connection_string",
    "auth_secret",
    "nextauth_secret",
    "api_secret_key",
    "groq_api_key",
}


def _bounded_string(value: Any) -> str:
    try:
        text = str(value)
    except Exception:
        text = f"<unprintable {type(value).__name__}>"
    return text[:_MAX_VALUE_LENGTH]


def _normalize_key(key: Any) -> str:
    return _bounded_string(key).strip().lower().replace("-", "_")


def _is_sensitive_key(key: Any) -> bool:
    return _normalize_key(key) in _SENSITIVE_KEYS


def redact_value(key: Any, value: Any) -> Any:
    """Redact a value when its key is sensitive; otherwise sanitize it."""
    if _is_sensitive_key(key):
        return REDACTED
    return redact_for_log(value)


def redact_mapping(mapping: Mapping[Any, Any]) -> dict[Any, Any]:
    """Return a redacted copy of a mapping."""
    return {
        key: REDACTED if _is_sensitive_key(key) else redact_for_log(value)
        for key, value in mapping.items()
    }


def redact_for_log(value: Any, *, _depth: int = 0) -> Any:
    """Convert arbitrary values into bounded, JSON-friendly log values."""
    if _depth >= _MAX_DEPTH:
        return "<maximum depth exceeded>"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:_MAX_VALUE_LENGTH]
    if isinstance(value, Mapping):
        return {
            key: (
                REDACTED
                if _is_sensitive_key(key)
                else redact_for_log(item, _depth=_depth + 1)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_for_log(item, _depth=_depth + 1) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_for_log(item, _depth=_depth + 1) for item in value)
    return _bounded_string(value)
