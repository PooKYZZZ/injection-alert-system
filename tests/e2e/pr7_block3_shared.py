from __future__ import annotations

import json
import re
from dataclasses import dataclass

_EVIDENCE_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
_FIELDS = {"evidence_id", "stage", "method", "path", "timestamp"}
_STAGES = {"request_received", "protected_work_started"}


@dataclass(frozen=True, slots=True)
class PortalSentinelEvent:
    evidence_id: str
    stage: str
    method: str
    path: str
    timestamp: str


def parse_portal_events(
    raw: bytes, *, max_bytes: int = 256_000
) -> list[PortalSentinelEvent]:
    if len(raw) > max_bytes:
        raise AssertionError(f"portal sentinel exceeded {max_bytes} bytes")

    events: list[PortalSentinelEvent] = []
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        payload = json.loads(line)
        if not isinstance(payload, dict) or set(payload) != _FIELDS:
            raise AssertionError(f"unexpected sentinel fields on line {line_number}")
        if (
            payload["stage"] not in _STAGES
            or payload["method"] != "GET"
            or payload["path"] != "/records/search"
            or not _EVIDENCE_ID.fullmatch(payload["evidence_id"])
        ):
            raise AssertionError(f"invalid sentinel record on line {line_number}")
        if not isinstance(payload["timestamp"], str):
            raise AssertionError(f"invalid sentinel timestamp on line {line_number}")
        events.append(PortalSentinelEvent(**payload))
    return events


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
