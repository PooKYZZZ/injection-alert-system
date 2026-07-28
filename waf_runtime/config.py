from __future__ import annotations

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
        ):
            raise ValueError("snapshot URL must be a fixed absolute HTTP origin")
        if not token:
            raise ValueError("WAF_STATE_SYNC_API_KEY is required")
        mode = os.environ.get("PR7_WAF_MODE", "off").lower()
        if mode not in {"off", "dry_run", "enforce"}:
            raise ValueError("unsupported runtime mode")
        return cls(
            url,
            token,
            mode,
            os.environ.get("PR7_STATE_DIR", "/pr7-state"),
            os.environ.get("NGINX_CONFIG", "/etc/nginx/nginx.conf"),
            float(os.environ.get("PR7_POLL_INTERVAL", "5")),
            float(os.environ.get("PR7_SUBPROCESS_TIMEOUT", "5")),
        )
