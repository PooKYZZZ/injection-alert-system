from __future__ import annotations

from waf_runtime.control_cli import main


def test_control_cli_status(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("PR7_STATE_DIR", str(tmp_path))
    monkeypatch.setenv(
        "WAF_STATE_SNAPSHOT_URL",
        "http://backend:8000/api/internal/waf-enforcement/snapshot",
    )
    monkeypatch.setenv("WAF_STATE_SYNC_API_KEY", "t" * 32)
    monkeypatch.setattr("sys.argv", ["pr7-waf-control", "status"])
    assert main() == 0
    assert '"disabled": false' in capsys.readouterr().out
