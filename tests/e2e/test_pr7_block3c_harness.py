from __future__ import annotations

import json

import pytest

from tests.e2e.pr7_block3c_harness import (
    ComposeProfile,
    FaultMode,
    FaultResponse,
    SnapshotFaultServer,
)
from waf_runtime.snapshot import SnapshotClient, SnapshotRejected


def _valid_payload() -> dict:
    from waf_runtime.snapshot import canonical_state_checksum

    return {
        "schema_version": 1,
        "policy_version": "confidence-waf-enforcement-v1",
        "revision": 1,
        "scope": "RECORD_SEARCH",
        "generated_at": "2026-07-31T00:00:00.000Z",
        "state_checksum_sha256": canonical_state_checksum(
            1, "confidence-waf-enforcement-v1", 1, "RECORD_SEARCH", []
        ),
        "items": [],
    }


@pytest.mark.parametrize(
    "mode,match",
    [
        (FaultMode.UNAUTHORIZED, "status"),
        (FaultMode.SERVER_ERROR, "status"),
        (FaultMode.REDIRECT, "status"),
        (FaultMode.WRONG_CONTENT_TYPE, "content type"),
        (FaultMode.MALFORMED_JSON, "JSON"),
        (FaultMode.OVERSIZED, "size"),
    ],
)
def test_fault_server_exercises_snapshot_rejection_classes(mode, match) -> None:
    with SnapshotFaultServer(FaultResponse(mode=mode)) as server:
        client = SnapshotClient(server.endpoint, "x" * 32, total_timeout=0.5)
        try:
            with pytest.raises(SnapshotRejected, match=match):
                client.fetch()
        finally:
            client.close()


def test_fault_server_serves_valid_snapshot() -> None:
    with SnapshotFaultServer(
        FaultResponse(payload=_valid_payload())
    ) as server:
        client = SnapshotClient(server.endpoint, "x" * 32)
        try:
            assert client.fetch().revision == 1
        finally:
            client.close()


def test_fault_server_timeout_is_bounded() -> None:
    with SnapshotFaultServer(FaultResponse(mode=FaultMode.TIMEOUT)) as server:
        client = SnapshotClient(server.endpoint, "x" * 32, total_timeout=0.2)
        try:
            with pytest.raises(SnapshotRejected, match="transport|deadline"):
                client.fetch()
        finally:
            client.close()


def test_compose_profile_controls_are_bounded_and_explicit(monkeypatch, tmp_path) -> None:
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return type("Result", (), {"returncode": 0, "stdout": "ok\n"})()

    monkeypatch.setattr("tests.e2e.pr7_block3c_harness.subprocess.run", fake_run)
    profile = ComposeProfile(
        "pr7-test",
        ("docker-compose.yml", "docker-compose.pr7-block3c.yml"),
        str(tmp_path),
    )
    assert profile.disconnect("pr7-test_default", "backend") == "ok"
    assert profile.recreate("pr7-block3-waf") == "ok"
    assert calls[0][0][-4:] == [
        "network",
        "disconnect",
        "pr7-test_default",
        "pr7-test-backend-1",
    ]
    assert calls[1][0][-4:] == [
        "up",
        "--detach",
        "--force-recreate",
        "pr7-block3-waf",
    ]
    assert calls[1][1]["timeout"] == 420
