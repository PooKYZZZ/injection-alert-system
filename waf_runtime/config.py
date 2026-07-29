from __future__ import annotations

import math
import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class RuntimeConfig:
    snapshot_url: str
    sync_api_key: str
    mode: str = "off"
    state_dir: str = "/pr7-state"
    nginx_config: str = "/etc/nginx/nginx.conf"
    probe_url: str = "http://127.0.0.1:8080"
    poll_interval: float = 5.0
    subprocess_timeout: float = 5.0

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        url = os.environ.get("WAF_STATE_SNAPSHOT_URL", "")
        token = os.environ.get("WAF_STATE_SYNC_API_KEY", "")
        parsed = urlsplit(url)
        if (
            parsed.scheme != "http"
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or not parsed.hostname
            or parsed.port is None
            or parsed.path != "/api/internal/waf-enforcement/snapshot"
        ):
            raise ValueError("snapshot URL must be a fixed absolute HTTP origin")
        if len(token) < 32:
            raise ValueError("WAF_STATE_SYNC_API_KEY must be at least 32 characters")
        probe_url = os.environ.get("PR7_PROBE_URL", "http://127.0.0.1:8080")
        probe = urlsplit(probe_url)
        if (
            probe.scheme != "http"
            or probe.username
            or probe.password
            or probe.query
            or probe.fragment
            or probe.hostname != "127.0.0.1"
            or probe.port is None
            or probe.path not in {"", "/"}
        ):
            raise ValueError("probe URL must be a fixed local HTTP endpoint")
        mode = os.environ.get("PR7_WAF_MODE", "off").lower()
        if mode not in {"off", "dry_run", "enforce"}:
            raise ValueError("unsupported runtime mode")
        poll_interval = float(os.environ.get("PR7_POLL_INTERVAL", "5"))
        subprocess_timeout = float(os.environ.get("PR7_SUBPROCESS_TIMEOUT", "5"))
        if any(
            not math.isfinite(value) or value <= 0
            for value in (poll_interval, subprocess_timeout)
        ):
            raise ValueError("runtime intervals must be positive finite numbers")
        return cls(
            url,
            token,
            mode,
            os.environ.get("PR7_STATE_DIR", "/pr7-state"),
            os.environ.get("NGINX_CONFIG", "/etc/nginx/nginx.conf"),
            probe_url,
            poll_interval,
            subprocess_timeout,
        )
