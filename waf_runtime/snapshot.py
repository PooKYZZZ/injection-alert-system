from __future__ import annotations

import hashlib
import ipaddress
import json
import signal
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

import httpx

MAX_BODY_BYTES = 1024 * 1024
MAX_ITEMS = 512
SCHEMA_VERSION = 1
POLICY_VERSION = "confidence-waf-enforcement-v1"
SCOPE = "RECORD_SEARCH"
PATH = "/records/search"
SNAPSHOT_ENDPOINT_PATH = "/api/internal/waf-enforcement/snapshot"
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class SnapshotRejected(ValueError):
    pass


@dataclass(frozen=True)
class Snapshot:
    schema_version: int
    policy_version: str
    revision: int
    scope: str
    generated_at: str
    state_checksum_sha256: str
    items: tuple[dict[str, Any], ...]


def _duplicate_rejecting_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SnapshotRejected("duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise SnapshotRejected(f"non-finite JSON number: {value}")


def _timestamp_epoch(value: str) -> int:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise SnapshotRejected("timestamp must be UTC with millisecond precision")
    try:
        parsed = datetime.strptime(value, TIMESTAMP_FORMAT)
    except ValueError as exc:
        raise SnapshotRejected(
            "timestamp must be UTC with millisecond precision"
        ) from exc
    if len(value) != 24:
        raise SnapshotRejected("timestamp must be UTC with millisecond precision")
    return int(parsed.replace(tzinfo=timezone.utc).timestamp() * 1000)


def _canonical_ip(value: Any) -> str:
    if not isinstance(value, str):
        raise SnapshotRejected("source IP must be a string")
    try:
        parsed = ipaddress.ip_address(value)
    except ValueError as exc:
        raise SnapshotRejected("invalid source IP") from exc
    if parsed.version != 4:
        raise SnapshotRejected("runtime IPv6 enforcement is unsupported")
    if str(parsed) != value:
        raise SnapshotRejected("source IP must be canonical")
    return value


def canonical_state_checksum(
    schema_version: int,
    policy_version: str,
    revision: int,
    scope: str,
    items: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> str:
    normalized = [dict(item) for item in items]
    normalized.sort(
        key=lambda item: (
            ipaddress.ip_address(item["source_ip"]).version,
            ipaddress.ip_address(item["source_ip"]).packed,
            item["request_path"],
            _timestamp_epoch(item["expires_at"]),
            item["recommendation_id"],
            item["entry_id"],
        )
    )
    encoded = json.dumps(
        {
            "schema_version": schema_version,
            "policy_version": policy_version,
            "revision": revision,
            "scope": scope,
            "items": normalized,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _validate_snapshot(value: Any) -> Snapshot:
    if not isinstance(value, dict):
        raise SnapshotRejected("snapshot root must be an object")
    expected = {
        "schema_version",
        "policy_version",
        "revision",
        "scope",
        "generated_at",
        "state_checksum_sha256",
        "items",
    }
    if set(value) != expected:
        raise SnapshotRejected("snapshot contains unknown or missing fields")
    if value["schema_version"] != SCHEMA_VERSION:
        raise SnapshotRejected("unsupported schema version")
    if value["policy_version"] != POLICY_VERSION:
        raise SnapshotRejected("unsupported policy version")
    if (
        isinstance(value["revision"], bool)
        or not isinstance(value["revision"], int)
        or value["revision"] < 0
    ):
        raise SnapshotRejected("invalid revision")
    if value["scope"] != SCOPE:
        raise SnapshotRejected("unsupported snapshot scope")
    _timestamp_epoch(value["generated_at"])
    checksum = value["state_checksum_sha256"]
    if (
        not isinstance(checksum, str)
        or len(checksum) != 64
        or any(c not in "0123456789abcdef" for c in checksum)
    ):
        raise SnapshotRejected("invalid state checksum")
    items = value["items"]
    if not isinstance(items, list) or len(items) > MAX_ITEMS:
        raise SnapshotRejected("snapshot item limit exceeded")
    normalized: list[dict[str, Any]] = []
    entry_ids: set[int] = set()
    recommendation_ids: set[int] = set()
    owners: set[tuple[str, str]] = set()
    item_fields = {
        "entry_id",
        "recommendation_id",
        "source_ip",
        "request_path",
        "expires_at",
    }
    for item in items:
        if not isinstance(item, dict) or set(item) != item_fields:
            raise SnapshotRejected("invalid snapshot item fields")
        for name in ("entry_id", "recommendation_id"):
            current = item[name]
            if isinstance(current, bool) or not isinstance(current, int) or current < 1:
                raise SnapshotRejected(f"invalid {name}")
        source_ip = _canonical_ip(item["source_ip"])
        if item["request_path"] != PATH or not isinstance(item["request_path"], str):
            raise SnapshotRejected("snapshot path is not approved")
        _timestamp_epoch(item["expires_at"])
        identity = (source_ip, item["request_path"])
        if (
            item["entry_id"] in entry_ids
            or item["recommendation_id"] in recommendation_ids
            or identity in owners
        ):
            raise SnapshotRejected("duplicate snapshot identity")
        entry_ids.add(item["entry_id"])
        recommendation_ids.add(item["recommendation_id"])
        owners.add(identity)
        normalized.append(dict(item))
    actual = canonical_state_checksum(
        value["schema_version"],
        value["policy_version"],
        value["revision"],
        value["scope"],
        normalized,
    )
    if actual != checksum:
        raise SnapshotRejected("snapshot checksum mismatch")
    return Snapshot(
        schema_version=value["schema_version"],
        policy_version=value["policy_version"],
        revision=value["revision"],
        scope=value["scope"],
        generated_at=value["generated_at"],
        state_checksum_sha256=checksum,
        items=tuple(normalized),
    )


class SnapshotClient:
    def __init__(
        self,
        endpoint: str,
        bearer_token: str,
        *,
        transport: httpx.BaseTransport | None = None,
        total_timeout: float = 5.0,
    ):
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme != "http"
            or parsed.username
            or parsed.password
            or parsed.fragment
            or parsed.query
            or not parsed.hostname
            or parsed.port is None
            or parsed.path != SNAPSHOT_ENDPOINT_PATH
        ):
            raise ValueError(
                "snapshot endpoint must be an absolute fixed-origin HTTP URL"
            )
        self.endpoint = endpoint
        self.bearer_token = bearer_token
        self.total_timeout = total_timeout
        self.client = httpx.Client(
            transport=transport,
            follow_redirects=False,
            trust_env=False,
            timeout=httpx.Timeout(
                total_timeout,
                connect=total_timeout,
                read=total_timeout,
                write=total_timeout,
                pool=total_timeout,
            ),
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "Accept": "application/json",
                "Accept-Encoding": "identity",
            },
        )

    def close(self) -> None:
        self.client.close()

    def fetch(self) -> Snapshot:
        started = time.monotonic()
        try:
            remaining = self.total_timeout
            with self._deadline(remaining):
                with self.client.stream(
                    "GET", self.endpoint, timeout=remaining
                ) as response:
                    if response.status_code != 200:
                        raise SnapshotRejected("snapshot response status rejected")
                    if response.headers.get("content-encoding", "").strip():
                        raise SnapshotRejected("compressed snapshot response rejected")
                    content_type = response.headers.get("content-type", "")
                    media, _, charset = content_type.partition(";")
                    if media.strip().lower() != "application/json" or (
                        charset and charset.strip().lower() != "charset=utf-8"
                    ):
                        raise SnapshotRejected("snapshot content type rejected")
                    length = response.headers.get("content-length")
                    if length is not None and (
                        not length.isdigit() or int(length) > MAX_BODY_BYTES
                    ):
                        raise SnapshotRejected("snapshot size rejected")
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes():
                        if time.monotonic() - started > self.total_timeout:
                            raise SnapshotRejected("snapshot total deadline exceeded")
                        size += len(chunk)
                        if size > MAX_BODY_BYTES:
                            raise SnapshotRejected("snapshot size rejected")
                        chunks.append(chunk)
                    raw = b"".join(chunks)
        except httpx.HTTPError as exc:
            raise SnapshotRejected("snapshot transport failed") from exc
        if time.monotonic() - started > self.total_timeout:
            raise SnapshotRejected("snapshot total deadline exceeded")
        if raw.startswith(b"\xef\xbb\xbf"):
            raise SnapshotRejected("UTF-8 BOM rejected")
        try:
            decoded = raw.decode("utf-8")
            value = json.loads(
                decoded,
                object_pairs_hook=_duplicate_rejecting_pairs,
                parse_constant=_reject_constant,
            )
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SnapshotRejected("invalid snapshot JSON") from exc
        return _validate_snapshot(value)

    @contextmanager
    def _deadline(self, seconds: float):
        if threading.current_thread() is not threading.main_thread() or not hasattr(
            signal, "setitimer"
        ):
            yield
            return
        previous_handler = signal.getsignal(signal.SIGALRM)
        previous_timer = signal.setitimer(signal.ITIMER_REAL, 0)
        started = time.monotonic()
        deadline = seconds
        if previous_timer[0] > 0:
            deadline = min(deadline, previous_timer[0])

        def timeout_handler(signum, frame):
            raise SnapshotRejected("snapshot total deadline exceeded")

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, deadline)
        try:
            yield
        finally:
            elapsed = time.monotonic() - started
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, previous_handler)
            remaining = previous_timer[0] - elapsed
            if remaining > 0:
                signal.setitimer(
                    signal.ITIMER_REAL, remaining, previous_timer[1]
                )
