"""Safe, bounded evidence primitives for PR7 Block 3 operator scripts."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EVIDENCE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
MAX_ARTIFACT_BYTES = 256 * 1024
FORBIDDEN_KEYS = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "prompt",
    "query_value",
    "request_body",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def validate_id(value: str, *, label: str = "evidence ID") -> str:
    if not EVIDENCE_ID_RE.fullmatch(value):
        raise ValueError(f"invalid {label}")
    return value


def assert_safe_fields(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in FORBIDDEN_KEYS or any(
                marker in normalized
                for marker in ("authorization", "cookie", "password", "secret")
            ):
                raise ValueError(f"unsafe evidence field: {key}")
            assert_safe_fields(child)
    elif isinstance(value, list):
        for child in value:
            assert_safe_fields(child)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    assert_safe_fields(payload)
    encoded = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if len(encoded.encode("utf-8")) > MAX_ARTIFACT_BYTES:
        raise ValueError("evidence artifact exceeds bounded size")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(encoded, encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("evidence root must be an object")
    assert_safe_fields(payload)
    return payload
