import json
import re
from urllib.parse import parse_qsl, urlencode

_SENSITIVE_HEADER_KEYS = {"authorization", "cookie", "set-cookie"}
_SENSITIVE_HEADER_PATTERNS = re.compile(r"token|secret|key|credential", re.IGNORECASE)
_SENSITIVE_BODY_KEYS = {
    "password",
    "token",
    "secret",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
}
_HEADER_LINE_PATTERN = re.compile(
    r"^(?P<key>[A-Za-z0-9_-]+):(?P<value>.*)$",
    re.MULTILINE,
)
_KEY_VALUE_SECRET_PATTERN = re.compile(
    r"(?P<key>password|token|secret|api_key|apikey|authorization|cookie|credential)"
    r"=(?P<value>[^&\s;]+)",
    re.IGNORECASE,
)

MAX_BODY_LENGTH = 1024


def _is_sensitive_header(key: str) -> bool:
    if key.lower() in _SENSITIVE_HEADER_KEYS:
        return True
    return bool(_SENSITIVE_HEADER_PATTERNS.search(key))


def _is_sensitive_body_key(key: str) -> bool:
    return key.lower() in _SENSITIVE_BODY_KEYS or bool(
        _SENSITIVE_HEADER_PATTERNS.search(key)
    )


def _redact_json(value: str) -> str | None:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, dict):
        return None

    redacted = {
        key: "[REDACTED]" if _is_sensitive_body_key(str(key)) else item
        for key, item in parsed.items()
    }
    return json.dumps(redacted)


def _redact_form(value: str) -> str | None:
    pairs = parse_qsl(value, keep_blank_values=True)
    if not pairs:
        return None
    if not any(_is_sensitive_body_key(key) for key, _ in pairs):
        return None
    return urlencode(
        [
            (key, "[REDACTED]" if _is_sensitive_body_key(key) else item)
            for key, item in pairs
        ]
    )


def _redact_header_lines(value: str) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group("key")
        if _is_sensitive_header(key):
            return f"{key}: [REDACTED]"
        return match.group(0)

    return _HEADER_LINE_PATTERN.sub(replace, value)


def redact_sensitive_text(value: str) -> str:
    if not value:
        return value

    redacted = _redact_json(value)
    if redacted is not None:
        return redacted[:MAX_BODY_LENGTH]

    redacted = _redact_form(value)
    if redacted is not None:
        return redacted[:MAX_BODY_LENGTH]

    redacted = _redact_header_lines(value)
    redacted = _KEY_VALUE_SECRET_PATTERN.sub(
        lambda match: f"{match.group('key')}=[REDACTED]",
        redacted,
    )
    return redacted[:MAX_BODY_LENGTH]


def sanitize_waf_event(payload: dict) -> dict:
    result = dict(payload)

    if "request_headers" in payload and payload["request_headers"] is not None:
        result["request_headers"] = {
            k: "[REDACTED]" if _is_sensitive_header(k) else v
            for k, v in payload["request_headers"].items()
        }

    if "sanitized_body" in payload and payload["sanitized_body"] is not None:
        result["sanitized_body"] = redact_sensitive_text(payload["sanitized_body"])

    return result
