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


def test_enable_preserves_configured_runtime_mode(monkeypatch, tmp_path):
    import waf_runtime.control_cli as module

    class Config:
        mode = "dry_run"
        state_dir = tmp_path
        nginx_config = tmp_path / "nginx.conf"
        selected_path = tmp_path / "selected.conf"
        snapshot_url = "http://backend:8000/api/internal/waf-enforcement/snapshot"
        sync_api_key = "t" * 32
        probe_url = "http://127.0.0.1:8081"
        audit_log_path = tmp_path / "audit.jsonl"
        subprocess_timeout = 2.0

    captured = {}
    monkeypatch.setattr(
        module.RuntimeConfig, "from_env", staticmethod(lambda: Config())
    )
    monkeypatch.setattr(module, "CandidateStateStore", lambda path: object())
    monkeypatch.setattr(module, "NginxController", lambda **kwargs: object())
    monkeypatch.setattr(module, "SnapshotClient", lambda *args, **kwargs: object())

    class Reconciler:
        def __init__(self, *args, **kwargs):
            captured["mode"] = kwargs["config"].mode

        def reconcile(self):
            return "mode_empty"

    monkeypatch.setattr(module, "Reconciler", Reconciler)
    monkeypatch.setattr(
        module,
        "WafControls",
        lambda *args, **kwargs: type(
            "Controls", (), {"enable": lambda self: "enabled"}
        )(),
    )
    monkeypatch.setattr("sys.argv", ["pr7-waf-control", "enable"])

    assert module.main() == 0
    assert captured["mode"] == "dry_run"
