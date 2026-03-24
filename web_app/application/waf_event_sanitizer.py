import re

_SENSITIVE_HEADER_KEYS = {"authorization", "cookie", "set-cookie"}
_SENSITIVE_HEADER_PATTERNS = re.compile(r"token|secret|key|credential", re.IGNORECASE)

MAX_BODY_LENGTH = 1024


def _is_sensitive_header(key: str) -> bool:
    if key.lower() in _SENSITIVE_HEADER_KEYS:
        return True
    return bool(_SENSITIVE_HEADER_PATTERNS.search(key))


def sanitize_waf_event(payload: dict) -> dict:
    result = dict(payload)

    if "request_headers" in payload and payload["request_headers"] is not None:
        result["request_headers"] = {
            k: "[REDACTED]" if _is_sensitive_header(k) else v
            for k, v in payload["request_headers"].items()
        }

    if "sanitized_body" in payload and payload["sanitized_body"] is not None:
        body = payload["sanitized_body"]
        if len(body) > MAX_BODY_LENGTH:
            result["sanitized_body"] = body[:MAX_BODY_LENGTH]

    return result
