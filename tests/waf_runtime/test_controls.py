from __future__ import annotations

from waf_runtime.controls import WafControls
from waf_runtime.state import CandidateStateStore


class FakeNginx:
    def __init__(self):
        self.reloads = 0

    def validate_candidate(self, path):
        return True

    def reload_and_confirm(self):
        self.reloads += 1
        return True

    def probe_candidate(self, path):
        return True

    def probe_empty(self, path):
        return True


def test_disable_sets_latch_and_selects_empty(tmp_path):
    nginx = FakeNginx()
    controls = WafControls(CandidateStateStore(tmp_path), nginx)
    assert controls.disable().startswith("Disable completed")
    assert nginx.reloads == 1
    assert controls.status()["disabled"] is True
    assert controls.enable().startswith("Enable completed")
    assert controls.status()["disabled"] is False


def test_enable_reports_actual_pending_state_and_reconciles_when_available(tmp_path):
    store = CandidateStateStore(tmp_path)
    nginx = FakeNginx()
    calls = []
    controls = WafControls(
        store, nginx, reconcile=lambda: calls.append("reconcile") or "authoritative"
    )
    store.set_disabled(True)
    assert "authoritative" in controls.enable()
    assert calls == ["reconcile"]
