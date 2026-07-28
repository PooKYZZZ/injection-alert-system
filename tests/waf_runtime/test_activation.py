from __future__ import annotations

import pytest

from waf_runtime.activation import ActivationError, ActivationManager
from waf_runtime.snapshot import Snapshot
from waf_runtime.state import CandidateStateStore


class FakeNginx:
    def __init__(self, *, probe=True, reload=True):
        self.probe_result = probe
        self.reload_result = reload
        self.validated = []
        self.reloaded = 0

    def validate_candidate(self, path):
        self.validated.append(path)
        return True

    def reload_and_confirm(self):
        self.reloaded += 1
        return self.reload_result

    def probe_candidate(self, candidate):
        return self.probe_result


def snapshot(revision=4):
    return Snapshot(
        1,
        "confidence-waf-enforcement-v1",
        revision,
        "RECORD_SEARCH",
        "2026-07-29T00:00:00.000Z",
        "0" * 64,
        (),
    )


def test_activation_commits_metadata_after_reload_and_probe(tmp_path):
    store = CandidateStateStore(tmp_path)
    nginx = FakeNginx()
    manager = ActivationManager(store, nginx)
    result = manager.activate(snapshot())
    assert result.selected_kind == "authoritative"
    assert nginx.reloaded == 1
    assert store.read_metadata()["selected_source_revision"] == 4


def test_activation_rolls_back_when_probe_fails(tmp_path):
    store = CandidateStateStore(tmp_path)
    nginx = FakeNginx(probe=False)
    manager = ActivationManager(store, nginx)
    with pytest.raises(ActivationError, match="probe"):
        manager.activate(snapshot())
    assert store.read_metadata()["selected_kind"] == "pending_empty"
    assert store.read_candidate("selected.conf") == store.read_candidate("empty.conf")


def test_disabled_store_never_activates_nonempty_snapshot(tmp_path):
    store = CandidateStateStore(tmp_path)
    store.set_disabled(True)
    manager = ActivationManager(store, FakeNginx())
    result = manager.activate(snapshot())
    assert result.selected_kind == "disabled_empty"
