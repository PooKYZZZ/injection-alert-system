"""Dependency-light, shared training/serving model-input contract.

This module is intentionally independent of the web application.  It is the
single source of truth for the text presented to the classifier and for its
provenance hash.
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
import urllib.parse
from hashlib import sha256
from typing import Any

MODEL_INPUT_VERSION = "model-input-v2-redacted"
MODEL_INPUT_FALLBACK_VERSION = "model-input-v2-redacted-raw-fallback"
LEGACY_MODEL_INPUT_VERSION = "http-preprocessor-v1"
MODEL_INPUT_HASH_POLICY = "sha256(model_input_text)"
MODEL_INPUT_TEXT_COLUMN = "combined_payload"
MODEL_INPUT_BUILDER = "ml_model.preprocessing.model_input.build_model_input_text"

_SENSITIVE_HEADER_KEYS = {"authorization", "cookie", "set-cookie"}
_SENSITIVE_KEY_PATTERN = re.compile(r"token|secret|key|credential", re.IGNORECASE)
_SENSITIVE_VALUE_KEYS = {
    "access_token", "api_key", "apikey", "auth", "authorization", "bearer",
    "client_secret", "code", "cookie", "credential", "id_token", "jwt",
    "password", "passwd", "private_key", "pwd", "refresh_token", "secret",
    "secret_key", "session", "session_id", "set-cookie", "sid", "token", "otp",
}
_PII_QUERY_KEYS = {"account", "customer", "email", "name", "phone", "student_id", "user_id"}
_HEADER_LINE_PATTERN = re.compile(r"^(?P<key>[A-Za-z0-9_-]+):(?P<value>.*)$", re.MULTILINE)
_KEY_VALUE_SECRET_PATTERN = re.compile(
    r"(?P<key>password|token|secret|api_key|apikey|authorization|cookie|credential)"
    r"=(?P<value>[^&\s;]+)", re.IGNORECASE
)
MAX_BODY_LENGTH = 1024

_INJECTION_INDICATOR_PATTERNS = (
    (
        "sql",
        re.compile(
            r"(?:\bunion\b\s+\bselect\b|\b(?:or|and)\b\s+['\"]?\s*\d+\s*['\"]?\s*=\s*['\"]?\s*\d+|\b(?:sleep|benchmark)\s*\(|--|/\*|\*/|#)",
            re.IGNORECASE,
        ),
    ),
    (
        "command",
        re.compile(
            r"(?:[;|]{1,2}\s*(?:cat|bash|sh|cmd|powershell|whoami|curl|wget|python|nc)\b|&&\s*(?:cat|bash|sh|cmd|powershell|whoami|curl|wget|python|nc)\b|`[^`]+`|\$\([^)]*\))",
            re.IGNORECASE,
        ),
    ),
    (
        "xss",
        re.compile(r"<\s*script\b|javascript:|\bon\w+\s*=", re.IGNORECASE),
    ),
    (
        "traversal",
        re.compile(r"(?:\.\.[/\\]){1,}|%2e%2e(?:%2f|%5c)", re.IGNORECASE),
    ),
)


def _is_sensitive_key(key: str) -> bool:
    normalized = str(key).lower().replace("-", "_")
    return (
        normalized in _SENSITIVE_VALUE_KEYS
        or normalized in _PII_QUERY_KEYS
        or bool(_SENSITIVE_KEY_PATTERN.search(str(key)))
    )


def _sensitive_value_indicators(value: Any) -> tuple[str, ...]:
    """Extract non-secret attack indicators from a value being redacted."""

    if isinstance(value, (dict, list, tuple, set)):
        return ()
    normalized = html.unescape(urllib.parse.unquote_plus(str(value)))
    return tuple(
        name
        for name, pattern in _INJECTION_INDICATOR_PATTERNS
        if pattern.search(normalized)
    )


def _redacted_sensitive_value(value: Any) -> str:
    """Replace a sensitive value without discarding safe attack evidence."""

    indicators = _sensitive_value_indicators(value)
    suffix = " ".join(f"[INDICATOR:{indicator}]" for indicator in indicators)
    return "[REDACTED]" + (f" {suffix}" if suffix else "")


def _redact_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _redacted_sensitive_value(item)
            if _is_sensitive_key(str(key))
            else _redact_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_json_value(item) for item in value]
    return value


def _redact_json(value: str) -> str | None:
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(parsed, (dict, list)):
        return None
    def contains_sensitive(item: Any) -> bool:
        if isinstance(item, dict):
            return any(_is_sensitive_key(key) or contains_sensitive(child) for key, child in item.items())
        if isinstance(item, list):
            return any(contains_sensitive(child) for child in item)
        return False
    if not contains_sensitive(parsed):
        return None
    return json.dumps(_redact_json_value(parsed), separators=(",", ":"))


def _redact_form(value: str) -> str | None:
    parts = value.split("&")
    if not any(
        _is_sensitive_key(urllib.parse.unquote_plus(part.split("=", 1)[0]))
        for part in parts
    ):
        return None
    redacted_parts = []
    for part in parts:
        key, separator, raw_value = part.partition("=")
        if _is_sensitive_key(urllib.parse.unquote_plus(key)) and separator:
            redacted_parts.append(f"{key}={_redacted_sensitive_value(raw_value)}")
        else:
            redacted_parts.append(part)
    return "&".join(redacted_parts)


def redact_sensitive_text(value: str) -> str:
    """Redact secrets and PII from a model-input body or malformed envelope."""

    if not isinstance(value, str) or not value:
        return value if isinstance(value, str) else ""
    redacted = _redact_json(value)
    if redacted is not None:
        return redacted[:MAX_BODY_LENGTH]
    redacted = _redact_form(value)
    if redacted is not None:
        return redacted[:MAX_BODY_LENGTH]

    def redact_header(match: re.Match[str]) -> str:
        key = match.group("key")
        return f"{key}: [REDACTED]" if (
            key.lower() in _SENSITIVE_HEADER_KEYS or _SENSITIVE_KEY_PATTERN.search(key)
        ) else match.group(0)

    redacted = _HEADER_LINE_PATTERN.sub(redact_header, value)
    redacted = _KEY_VALUE_SECRET_PATTERN.sub(
        lambda match: (
            f"{match.group('key')}="
            f"{_redacted_sensitive_value(match.group('value'))}"
        ),
        redacted,
    )
    return redacted[:MAX_BODY_LENGTH]


def redact_query_string(value: str | None) -> str | None:
    """Redact sensitive query values while preserving attack-bearing fields."""

    if not value:
        return value
    parts = value.split("&")
    if not any(
        _is_sensitive_key(urllib.parse.unquote_plus(part.split("=", 1)[0]))
        for part in parts
    ):
        return value
    redacted_parts = []
    for part in parts:
        key, separator, raw_value = part.partition("=")
        if _is_sensitive_key(urllib.parse.unquote_plus(key)) and separator:
            redacted_parts.append(f"{key}={_redacted_sensitive_value(raw_value)}")
        else:
            redacted_parts.append(part)
    return "&".join(redacted_parts)


def canonicalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = urllib.parse.unquote(text)
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\x00", "")
    return " ".join(text.split()).lower()


def parse_raw_http(raw_http: str) -> tuple[str, str, str]:
    if not raw_http or not isinstance(raw_http, str):
        return "", "", ""
    text = raw_http.replace("\r\n", "\n").replace("\r", "\n")
    if "\n\n" in text:
        header_section, body = text.split("\n\n", 1)
    else:
        header_section, body = text, ""
    lines = header_section.strip().splitlines()
    if not lines:
        return "", "", ""
    request_line = re.sub(
        r"\s+HTTP/[\d.]+\s*$", "", lines[0].strip(), flags=re.IGNORECASE
    )
    parts = request_line.split(" ", 1)
    if len(parts) < 2 or not parts[0].strip() or not parts[1].strip():
        return "", "", ""
    return parts[0].strip(), parts[1].strip(), body.strip()


def _redacted_target(path: str, query: str | None = None) -> str:
    parsed = urllib.parse.urlsplit(path)
    redacted_query = redact_query_string(parsed.query if query is None else query) or ""
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, redacted_query, parsed.fragment)
    )


def build_model_input_text(
    method: str,
    path: str,
    *,
    query: str | None = None,
    body: str | None = None,
) -> str:
    """Build the exact redacted/canonical text used by training and serving."""

    safe_method = canonicalize_text(method)
    safe_path = canonicalize_text(_redacted_target(path, query))
    safe_body = canonicalize_text(redact_sensitive_text(body or ""))
    return " ".join(part for part in (safe_method, safe_path, safe_body) if part)


def sanitize_model_input_request(raw_http: str) -> str:
    method, path, body = parse_raw_http(raw_http)
    if not method or not path:
        return redact_sensitive_text(raw_http)
    return f"{method} {_redacted_target(path)} HTTP/1.1\r\n\r\n{redact_sensitive_text(body)}"


def preprocess_http_request(raw_http: str) -> str:
    method, path, body = parse_raw_http(raw_http)
    if not method or not path:
        return ""
    return build_model_input_text(method, path, body=body)


def preprocess_legacy_http_request(raw_http: str) -> str:
    """Reproduce the v1 dataset contract for the explicitly supported legacy model."""

    method, path, body = parse_raw_http(raw_http)
    if not method or not path:
        return ""
    return " ".join(
        part
        for part in (
            canonicalize_text(method),
            canonicalize_text(path),
            canonicalize_text(body),
        )
        if part
    )


def prepare_legacy_model_input(raw_http: str) -> tuple[str, str, str]:
    model_input = preprocess_legacy_http_request(raw_http)
    if not model_input:
        model_input = raw_http if isinstance(raw_http, str) else ""
    return model_input, sha256(model_input.encode("utf-8")).hexdigest(), LEGACY_MODEL_INPUT_VERSION


def prepare_model_input(raw_http: str) -> tuple[str, str, str]:
    """Return v2 model text, SHA-256(model text), and the contract version."""

    model_input = preprocess_http_request(raw_http)
    preprocessing_version = MODEL_INPUT_VERSION
    if not model_input:
        model_input = redact_sensitive_text(raw_http)
        preprocessing_version = MODEL_INPUT_FALLBACK_VERSION
    return model_input, sha256(model_input.encode("utf-8")).hexdigest(), preprocessing_version


def validate_model_input_version(actual: object, *, context: str = "model artifact") -> None:
    if actual != MODEL_INPUT_VERSION:
        raise ValueError(
            f"{context} preprocessing_version={actual!r} is incompatible with "
            f"runtime {MODEL_INPUT_VERSION!r}"
        )


def validate_supported_model_input_version(
    actual: object, *, context: str = "model artifact"
) -> str:
    if actual not in {MODEL_INPUT_VERSION, LEGACY_MODEL_INPUT_VERSION}:
        raise ValueError(
            f"{context} preprocessing_version={actual!r} is unsupported; "
            f"expected {MODEL_INPUT_VERSION!r} or explicit legacy {LEGACY_MODEL_INPUT_VERSION!r}"
        )
    return str(actual)
