from __future__ import annotations

import pytest

from waf_runtime.config import RuntimeConfig


def test_config_requires_fixed_endpoint_and_known_mode(monkeypatch):
    monkeypatch.setenv(
        "WAF_STATE_SNAPSHOT_URL",
        "http://backend:8000/api/internal/waf-enforcement/snapshot",
    )
    monkeypatch.setenv("WAF_STATE_SYNC_API_KEY", "token")
    assert RuntimeConfig.from_env().mode == "off"
    monkeypatch.setenv("PR7_WAF_MODE", "production")
    with pytest.raises(ValueError, match="mode"):
        RuntimeConfig.from_env()
