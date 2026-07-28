from __future__ import annotations

from waf_runtime.supervisor import Supervisor


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
