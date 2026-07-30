from __future__ import annotations

import json

import httpx
import pytest

import waf_runtime.snapshot as snapshot_module
from waf_runtime.snapshot import (
    SnapshotClient,
    SnapshotRejected,
    canonical_state_checksum,
)


def _payload(items=None) -> dict:
    items = items or []
    return {
        "schema_version": 1,
        "policy_version": "confidence-waf-enforcement-v1",
        "revision": 3,
        "scope": "RECORD_SEARCH",
        "generated_at": "2026-07-29T00:00:00.000Z",
        "state_checksum_sha256": canonical_state_checksum(
            1, "confidence-waf-enforcement-v1", 3, "RECORD_SEARCH", items
        ),
        "items": items,
    }


def _client(handler):
    transport = httpx.MockTransport(handler)
    return SnapshotClient(
        "http://backend:8000/api/internal/waf-enforcement/snapshot",
        "canary-token",
        transport=transport,
    )


def test_rejects_duplicate_keys_at_nested_depth() -> None:
    body = (
        b'{"schema_version":1,"policy_version":"confidence-waf-enforcement-v1","revision":3,"scope":"RECORD_SEARCH","generated_at":"2026-07-29T00:00:00.000Z","state_checksum_sha256":"'
        + b"0" * 64
        + b'","items":[{"entry_id":1,"entry_id":2}]}'
    )

    def handler(request):
        return httpx.Response(
            200, headers={"content-type": "application/json"}, content=body
        )

    with pytest.raises(SnapshotRejected, match="duplicate"):
        _client(handler).fetch()


def test_rejects_proxy_redirect_and_non_json() -> None:
    def handler(request):
        assert request.url == httpx.URL(
            "http://backend:8000/api/internal/waf-enforcement/snapshot"
        )
        assert request.headers["authorization"] == "Bearer canary-token"
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(302, headers={"location": "http://evil.invalid"})

    with pytest.raises(SnapshotRejected, match="status"):
        _client(handler).fetch()

    def non_json(request):
        return httpx.Response(
            200, headers={"content-type": "text/plain"}, content=b"no"
        )

    with pytest.raises(SnapshotRejected, match="content type"):
        _client(non_json).fetch()


def test_rejects_unapproved_snapshot_path() -> None:
    with pytest.raises(ValueError, match="endpoint"):
        SnapshotClient("http://backend:8000/api/other", "canary-token")


def test_rejects_body_that_crosses_one_mib() -> None:
    def handler(request):
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"{" + b"x" * (1024 * 1024) + b"}",
        )

    with pytest.raises(SnapshotRejected, match="size"):
        _client(handler).fetch()


def test_rejects_coercive_types_and_nan() -> None:
    def handler(request):
        body = (
            json.dumps(_payload()).replace('"revision": 3', '"revision": true').encode()
        )
        return httpx.Response(
            200, headers={"content-type": "application/json"}, content=body
        )

    with pytest.raises(SnapshotRejected, match="revision"):
        _client(handler).fetch()


def test_accepts_valid_empty_snapshot_and_rejects_bom() -> None:
    def valid(request):
        return httpx.Response(
            200,
            headers={"content-type": "application/json; charset=utf-8"},
            content=json.dumps(_payload(), separators=(",", ":")).encode(),
        )

    assert _client(valid).fetch().revision == 3

    def bom(request):
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            content=b"\xef\xbb\xbf{}",
        )

    with pytest.raises(SnapshotRejected, match="BOM"):
        _client(bom).fetch()


def test_fetch_passes_a_remaining_deadline_to_httpx():
    calls = []

    class Response:
        status_code = 200
        headers = {"content-type": "application/json"}

        def iter_bytes(self):
            yield json.dumps(_payload(), separators=(",", ":")).encode()

    class Stream:
        def __enter__(self):
            return Response()

        def __exit__(self, *args):
            return False

    class Client:
        def stream(self, *args, **kwargs):
            calls.append(kwargs)
            return Stream()

    client = _client(lambda request: httpx.Response(500))
    client.client = Client()
    assert client.fetch().revision == 3
    assert 0 < calls[0]["timeout"] <= client.total_timeout


def test_deadline_preserves_shorter_outer_alarm_after_elapsed_time(monkeypatch):
    calls = []
    clock = iter((100.0, 100.25))

    monkeypatch.setattr(snapshot_module.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(snapshot_module.signal, "SIGALRM", 14, raising=False)
    monkeypatch.setattr(snapshot_module.signal, "ITIMER_REAL", 0, raising=False)
    monkeypatch.setattr(snapshot_module.signal, "getsignal", lambda signum: "old")
    monkeypatch.setattr(snapshot_module.signal, "signal", lambda *args: None)

    def fake_setitimer(which, seconds, interval=0.0):
        calls.append((seconds, interval))
        if len(calls) == 1:
            return (2.0, 0.0)
        return (0.0, 0.0)

    monkeypatch.setattr(
        snapshot_module.signal, "setitimer", fake_setitimer, raising=False
    )
    client = SnapshotClient(
        "http://backend:8000/api/internal/waf-enforcement/snapshot",
        "canary-token",
    )

    with client._deadline(5.0):
        pass

    assert calls[1][0] == 2.0
    assert calls[3][0] == pytest.approx(1.75)
