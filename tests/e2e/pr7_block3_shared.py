from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime

_EVIDENCE_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_FIELDS = {"evidence_id", "stage", "method", "path", "timestamp"}
PORTAL_SENTINEL_MAX_BYTES = 256 * 1024
_STAGES = {"request_received", "protected_work_started"}


@dataclass(frozen=True, slots=True)
class PortalSentinelEvent:
    evidence_id: str
    stage: str
    method: str
    path: str
    timestamp: str


def parse_portal_events(
    raw: bytes, *, max_bytes: int = PORTAL_SENTINEL_MAX_BYTES
) -> list[PortalSentinelEvent]:
    if len(raw) > max_bytes:
        raise AssertionError(f"portal sentinel exceeded {max_bytes} bytes")

    events: list[PortalSentinelEvent] = []
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise AssertionError("portal sentinel is not valid UTF-8") from exc
    for line_number, line in enumerate(lines, start=1):
        try:
            payload = json.loads(line)
        except (TypeError, ValueError) as exc:
            raise AssertionError(f"invalid JSON on line {line_number}") from exc
        if not isinstance(payload, dict) or set(payload) != _FIELDS:
            raise AssertionError(f"unexpected sentinel fields on line {line_number}")
        if (
            not isinstance(payload["evidence_id"], str)
            or not isinstance(payload["stage"], str)
            or not isinstance(payload["method"], str)
            or not isinstance(payload["path"], str)
            or not isinstance(payload["timestamp"], str)
            or payload["stage"] not in _STAGES
            or payload["method"] != "GET"
            or payload["path"] != "/records/search"
            or not _EVIDENCE_ID.fullmatch(payload["evidence_id"])
        ):
            raise AssertionError(f"invalid sentinel record on line {line_number}")
        try:
            if not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z",
                payload["timestamp"],
            ):
                raise ValueError("timestamp must be UTC milliseconds")
            parsed_timestamp = datetime.fromisoformat(
                payload["timestamp"].replace("Z", "+00:00")
            )
        except ValueError as exc:
            raise AssertionError(
                f"invalid sentinel timestamp on line {line_number}"
            ) from exc
        if parsed_timestamp.tzinfo is None:
            raise AssertionError(f"invalid sentinel timestamp on line {line_number}")
        events.append(PortalSentinelEvent(**payload))
    return events


def assert_portal_stage_sequence(
    events: list[PortalSentinelEvent],
    evidence_id: str,
    expected: tuple[str, ...],
) -> None:
    actual = tuple(
        event.stage for event in events if event.evidence_id == evidence_id
    )
    if actual != expected:
        raise AssertionError(
            f"portal stages for {evidence_id}: {actual!r} != {expected!r}"
        )


def assert_portal_stages(
    events: list[PortalSentinelEvent],
    evidence_id: str,
    *,
    expected: set[str],
) -> None:
    actual = {event.stage for event in events if event.evidence_id == evidence_id}
    if actual != expected:
        raise AssertionError(
            f"portal stages for {evidence_id}: {actual!r} != {expected!r}"
        )
