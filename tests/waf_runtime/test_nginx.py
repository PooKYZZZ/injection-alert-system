from __future__ import annotations

from pathlib import Path

from waf_runtime.nginx import NginxController


def test_nginx_controller_uses_bounded_commands(monkeypatch, tmp_path):
    calls = []

    class Result:
        returncode = 0
        stdout = "master process started\nworker process started\n"
        stderr = ""

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return Result()

    monkeypatch.setattr("waf_runtime.nginx.subprocess.run", run)
    controller = NginxController(config_path=tmp_path / "nginx.conf", timeout=2)
    assert controller.validate_candidate(Path("/tmp/candidate.conf"))
    assert controller.reload_and_confirm()
    assert calls[0][0][:2] == ["nginx", "-t"]
    assert calls[0][1]["timeout"] == 2
