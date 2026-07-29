from __future__ import annotations

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
    generations = iter([("worker-1",), ("worker-2",)])
    monkeypatch.setattr(
        NginxController,
        "worker_generation",
        lambda self: next(generations),
    )
    active = tmp_path / "selected.conf"
    active.write_text("old", encoding="ascii")
    candidate = tmp_path / "candidate.conf"
    candidate.write_text("new", encoding="ascii")
    controller = NginxController(
        config_path=tmp_path / "nginx.conf", timeout=2, active_path=active
    )
    assert controller.validate_candidate(candidate)
    assert controller.reload_and_confirm()
    assert calls[0][0][:2] == ["nginx", "-t"]
    assert calls[0][1]["timeout"] == 2


def test_probe_uses_a_fresh_http_connection(monkeypatch, tmp_path):
    requests = []

    class Response:
        status_code = 403

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, **kwargs):
            requests.append((url, kwargs))
            return Response()

    monkeypatch.setattr("waf_runtime.nginx.httpx.Client", lambda **kwargs: Client())
    active = tmp_path / "selected.conf"
    active.write_text("candidate", encoding="ascii")
    candidate = tmp_path / "candidate.conf"
    candidate.write_text("candidate", encoding="ascii")
    controller = NginxController(
        config_path=tmp_path / "nginx.conf",
        active_path=active,
        probe_url="http://127.0.0.1:8080",
    )
    assert controller.probe_candidate(candidate)
    assert requests == [("http://127.0.0.1:8080/records/search", {"timeout": 2.0})]


def test_probe_rejects_candidate_that_is_not_selected(monkeypatch, tmp_path):
    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("waf_runtime.nginx.httpx.Client", lambda **kwargs: Client())
    active = tmp_path / "selected.conf"
    active.write_text("active", encoding="ascii")
    candidate = tmp_path / "candidate.conf"
    candidate.write_text("different", encoding="ascii")
    controller = NginxController(
        config_path=tmp_path / "nginx.conf", active_path=active
    )
    assert not controller.probe_candidate(candidate)
