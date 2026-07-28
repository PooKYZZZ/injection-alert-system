from __future__ import annotations

from waf_runtime.controls import WafControls
from waf_runtime.state import CandidateStateStore


def test_disable_sets_latch_and_selects_empty(tmp_path):
    controls = WafControls(CandidateStateStore(tmp_path))
    assert controls.disable().startswith("Disable completed")
    assert controls.status()["disabled"] is True
    assert controls.enable().startswith("Enable completed")
    assert controls.status()["disabled"] is False
