from __future__ import annotations

import signal

from waf_runtime.entrypoint import prepare_startup_state
from waf_runtime.state import CandidateStateStore
from waf_runtime.supervisor import SIGQUIT, Supervisor


def test_supervisor_returns_nonzero_for_unexpected_child_exit(monkeypatch):
    class Child:
        pid = 42
        returncode = 7

        def poll(self):
            return self.returncode

        def terminate(self):
            pass

        def wait(self, timeout=None):
            return self.returncode

    monkeypatch.setattr(
        "waf_runtime.supervisor.subprocess.Popen", lambda *a, **k: Child()
    )
    supervisor = Supervisor(["nginx", "-g", "daemon off;"], ["python", "-c", "pass"])
    assert supervisor.run_once() == 7


def test_sigquit_is_forwarded_to_nginx_and_term_to_sync(monkeypatch):
    sent = []

    class Child:
        def __init__(self, code=None):
            self.code = code

        def poll(self):
            return self.code

        def send_signal(self, signum):
            sent.append(signum)

        def wait(self, timeout=None):
            self.code = 0
            return 0

        def terminate(self):
            sent.append("terminate")

        def kill(self):
            sent.append("kill")

    children = [Child(), Child()]
    monkeypatch.setattr(
        "waf_runtime.supervisor.subprocess.Popen",
        lambda *a, **k: children.pop(0),
    )
    supervisor = Supervisor(["nginx"], ["sync"])
    supervisor.request_shutdown(SIGQUIT, None)
    assert supervisor.run_once() == 0
    assert sent == [SIGQUIT, signal.SIGTERM]


def test_startup_forces_persisted_authoritative_state_to_empty(tmp_path):
    store = CandidateStateStore(tmp_path)
    store.selected_path.write_text("non-empty", encoding="ascii")
    store.write_metadata(
        {
            "metadata_schema_version": 1,
            "selected_kind": "authoritative",
            "selected_source_revision": 9,
            "selected_source_state_checksum_sha256": "0" * 64,
            "selected_file_checksum_sha256": "0" * 64,
            "selected_at": "2026-07-29T00:00:00.000Z",
        }
    )

    assert prepare_startup_state(store, "off") == "mode_empty"
    assert store.read_candidate("selected.conf") == store.read_candidate("empty.conf")
    assert store.read_metadata()["selected_kind"] == "mode_empty"
