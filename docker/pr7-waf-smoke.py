from __future__ import annotations

import ipaddress
import time
from datetime import datetime, timedelta, timezone

import httpx

from waf_runtime.activation import ActivationManager
from waf_runtime.nginx import NginxController
from waf_runtime.snapshot import Snapshot
from waf_runtime.state import CandidateStateStore


def snapshot(revision: int, count: int) -> Snapshot:
    expires = (
        datetime.now(timezone.utc) + timedelta(hours=1)
    ).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    base = ipaddress.IPv4Address("203.0.113.1")
    items = tuple(
        {
            "entry_id": index + 1,
            "recommendation_id": index + 1,
            "source_ip": str(base + index),
            "request_path": "/records/search",
            "expires_at": expires,
        }
        for index in range(count)
    )
    return Snapshot(
        1,
        "confidence-waf-enforcement-v1",
        revision,
        "RECORD_SEARCH",
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z"),
        f"{revision:064x}",
        items,
    )


def status(url: str, *, source_ip: str | None = None) -> int:
    headers = {"Accept-Encoding": "identity"}
    if source_ip:
        headers["X-PR7-Probe-Source"] = source_ip
    with httpx.Client(
        trust_env=False, follow_redirects=False, headers=headers
    ) as client:
        return client.get(url, timeout=3).status_code


def main() -> None:
    store = CandidateStateStore("/pr7-state")
    nginx = NginxController(
        config_path="/etc/nginx/nginx.conf",
        timeout=5,
        active_path="/pr7-state/selected.conf",
        probe_url="http://127.0.0.1:8081",
        audit_log_path="/var/log/modsecurity/modsec_audit.jsonl",
    )
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not nginx.wait_ready():
        time.sleep(0.25)
    if not nginx.wait_ready():
        raise SystemExit("PR7 NGINX readiness failed")

    manager = ActivationManager(store, nginx)
    for revision, count in enumerate((0, 1, 64, 128, 512), start=1):
        print(f"PR7 matrix candidate count={count}", flush=True)
        current = snapshot(revision, count)
        result = manager.activate(current)
        if result.selected_kind != "authoritative":
            raise SystemExit(
                f"unexpected selected kind for {count}: {result.selected_kind}"
            )
        if count == 0:
            if status("http://127.0.0.1:8081/records/search") != 204:
                raise SystemExit("empty candidate was not confirmed")
            continue
        for index in (0, count // 2, count - 1):
            source = current.items[index]["source_ip"]
            if status(
                "http://127.0.0.1:8081/records/search", source_ip=source
            ) != 403:
                raise SystemExit(f"representative rule failed for {count}/{index}")


if __name__ == "__main__":
    main()
