from __future__ import annotations

import json

import pytest

from tests.e2e.pr7_block3_shared import (
    assert_portal_stages,
    parse_portal_events,
)


def test_parse_portal_events_accepts_only_bounded_safe_contract() -> None:
    raw = json.dumps(
        {
            "evidence_id": "request_123",
            "stage": "request_received",
            "method": "GET",
            "path": "/records/search",
            "timestamp": "2026-07-31T00:00:00.000Z",
        }
    ).encode()

    events = parse_portal_events(raw)

    assert events[0].evidence_id == "request_123"
    assert_portal_stages(events, "request_123", expected={"request_received"})


@pytest.mark.parametrize(
    "change",
    [
        {"stage": "unknown"},
        {"method": "POST"},
        {"path": "/other"},
        {"evidence_id": "line\nbreak"},
        {"secret": "must-not-be-accepted"},
    ],
)
def test_parse_portal_events_rejects_untrusted_records(change: dict[str, str]) -> None:
    payload = {
        "evidence_id": "request_123",
        "stage": "request_received",
        "method": "GET",
        "path": "/records/search",
        "timestamp": "2026-07-31T00:00:00.000Z",
    }
    payload.update(change)

    with pytest.raises(AssertionError):
        parse_portal_events((json.dumps(payload) + "\n").encode())


def test_parse_portal_events_rejects_oversized_artifact() -> None:
    with pytest.raises(AssertionError, match="exceeded"):
        parse_portal_events(b"x" * 33, max_bytes=32)


@pytest.mark.parametrize(
    "raw",
    [
        b"not-json\n",
        b"\xff\n",
        b'{"evidence_id": [], "stage": "request_received", "method": "GET", "path": "/records/search", "timestamp": "2026-07-31T00:00:00Z"}\n',
        b'{"evidence_id": "safe", "stage": [], "method": "GET", "path": "/records/search", "timestamp": "2026-07-31T00:00:00Z"}\n',
    ],
)
def test_parse_portal_events_rejects_malformed_types_as_assertions(raw: bytes) -> None:
    with pytest.raises(AssertionError):
        parse_portal_events(raw)
