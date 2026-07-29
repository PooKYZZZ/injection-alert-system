from __future__ import annotations

import pytest

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
    monkeypatch.setattr(controller, "_request_status", lambda *args, **kwargs: 204)
    assert controller.validate_candidate(candidate)
    assert controller.reload_and_confirm()
    assert calls[0][0][:2] == ["nginx", "-t"]
    assert calls[0][1]["timeout"] == 2


def test_probe_uses_a_fresh_http_connection(monkeypatch, tmp_path):
    requests = []

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, **kwargs):
            requests.append((url, kwargs))
            response = type("Response", (), {})()
            response.status_code = [403, 204, 204, 403][len(requests) - 1]
            return response

    monkeypatch.setattr("waf_runtime.nginx.httpx.Client", lambda **kwargs: Client())
    active = tmp_path / "selected.conf"
    candidate = tmp_path / "candidate.conf"
    candidate.write_text(
        'SecRule REMOTE_ADDR "@ipMatch 203.0.113.7" "id:10000"',
        encoding="ascii",
    )
    active.write_text(candidate.read_text(encoding="ascii"), encoding="ascii")
    controller = NginxController(
        config_path=tmp_path / "nginx.conf",
        active_path=active,
        probe_url="http://127.0.0.1:8081",
    )
    assert controller.probe_candidate(candidate)
    assert requests[0][0].startswith("http://127.0.0.1:8081/records/search?")
    assert requests[0][1]["timeout"] == 2.0


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


def test_empty_probe_requires_exact_204(monkeypatch, tmp_path):
    class Response:
        status_code = 500

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def get(self, url, **kwargs):
            return Response()

    monkeypatch.setattr("waf_runtime.nginx.httpx.Client", lambda **kwargs: Client())
    active = tmp_path / "selected.conf"
    active.write_text("empty", encoding="ascii")
    controller = NginxController(
        config_path=tmp_path / "nginx.conf", active_path=active
    )
    assert not controller.probe_empty(active)


def test_audit_probe_requires_exact_revision_and_recommendation(tmp_path):
    audit = tmp_path / "audit.jsonl"
    audit.write_text(
        '{"marker":"probe-1","tags":["pr7","revision-42",'
        '"recommendation-123"]}\n',
        encoding="utf-8",
    )
    controller = NginxController(
        config_path=tmp_path / "nginx.conf",
        active_path=tmp_path / "selected.conf",
        audit_log_path=audit,
    )

    assert controller._audit_contains_all(
        "probe-1", '"pr7"', '"revision-42"', '"recommendation-123"'
    )
    assert not controller._audit_contains_all(
        "probe-1", '"pr7"', '"revision-41"', '"recommendation-123"'
    )


def test_candidate_tag_parser_rejects_missing_identity(tmp_path):
    candidate = tmp_path / "candidate.conf"
    candidate.write_text("tag:'pr7'\n", encoding="ascii")
    controller = NginxController(
        config_path=tmp_path / "nginx.conf", active_path=tmp_path / "selected.conf"
    )

    with pytest.raises(ValueError, match="revision"):
        controller._candidate_tag(candidate, "revision")
