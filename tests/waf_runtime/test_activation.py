from __future__ import annotations

import pytest

from waf_runtime.activation import ActivationError, ActivationManager, RollbackError
from waf_runtime.snapshot import Snapshot
from waf_runtime.state import CandidateStateStore


class FakeNginx:
    def __init__(self, *, probes=None, reloads=None, validate=True, validates=None):
        self.probes = list(probes if probes is not None else [True])
        self.reloads = list(reloads if reloads is not None else [True])
        self.validates = list(validates if validates is not None else [validate])
        self.validate_result = validate
        self.validated = []
        self.reloaded = 0
        self.probe_sources = []

    def validate_candidate(self, path):
        self.validated.append(path)
        if getattr(self, "mutate_candidate", False):
            path.write_text("mutated", encoding="ascii")
        return self.validates.pop(0) if self.validates else self.validate_result

    def reload_and_confirm(self):
        self.reloaded += 1
        return self.reloads.pop(0) if self.reloads else True

    def probe_candidate(
        self, candidate, source_ip=None, revision=None, recommendation_id=None
    ):
        self.probe_sources.append(source_ip)
        return self.probes.pop(0) if self.probes else True

    def probe_empty(self, candidate):
        return self.probes.pop(0) if self.probes else True


def snapshot(revision=4):
    return blocking_snapshot(revision)


def blocking_snapshot(revision=4):
    return Snapshot(
        1,
        "confidence-waf-enforcement-v1",
        revision,
        "RECORD_SEARCH",
        "2026-07-29T00:00:00.000Z",
        "0" * 64,
        (
            {
                "entry_id": revision,
                "recommendation_id": revision,
                "source_ip": "203.0.113.7",
                "request_path": "/records/search",
                "expires_at": "2099-07-29T00:00:02.000Z",
            },
        ),
    )


def empty_snapshot(revision=4):
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
    result = manager.activate(blocking_snapshot())
    assert result.selected_kind == "authoritative"
    assert nginx.reloaded == 1
    assert store.read_metadata()["selected_source_revision"] == 4
    assert nginx.probe_sources == ["203.0.113.7"]


def test_authoritative_empty_revision_clears_previous_block(tmp_path):
    store = CandidateStateStore(tmp_path)
    first = ActivationManager(store, FakeNginx())
    first.activate(blocking_snapshot(10))

    second = ActivationManager(store, FakeNginx())
    result = second.activate(empty_snapshot(11))

    assert result.selected_kind == "authoritative"
    metadata = store.read_metadata()
    assert metadata["selected_source_revision"] == 11
    assert metadata["selected_source_state_checksum_sha256"] == "0" * 64
    assert store.read_candidate("selected.conf") == store.read_candidate("empty.conf")


def test_activation_rolls_back_when_probe_fails(tmp_path):
    store = CandidateStateStore(tmp_path)
    nginx = FakeNginx(probes=[False, True], reloads=[True, True])
    manager = ActivationManager(store, nginx)
    with pytest.raises(ActivationError, match="probe"):
        manager.activate(snapshot())
    assert nginx.reloaded == 2
    assert store.read_metadata()["selected_kind"] == "mode_empty"
    assert store.read_candidate("selected.conf") == store.read_candidate("empty.conf")


def test_validation_failure_keeps_previous_selection(tmp_path):
    store = CandidateStateStore(tmp_path)
    nginx = FakeNginx(validate=False)
    manager = ActivationManager(store, nginx)
    with pytest.raises(ActivationError, match="validation"):
        manager.activate(snapshot())
    assert nginx.reloaded == 0
    assert store.read_metadata()["selected_kind"] == "mode_empty"


def test_reload_confirmation_failure_reloads_previous_selection(tmp_path):
    store = CandidateStateStore(tmp_path)
    nginx = FakeNginx(reloads=[False, True])
    with pytest.raises(ActivationError, match="reload"):
        ActivationManager(store, nginx).activate(snapshot())
    assert nginx.reloaded == 2
    assert store.read_metadata()["selected_kind"] == "mode_empty"
    assert store.read_candidate("selected.conf") == store.read_candidate("empty.conf")


def test_candidate_mutation_after_validation_is_rejected(tmp_path):
    store = CandidateStateStore(tmp_path)
    nginx = FakeNginx()
    nginx.mutate_candidate = True
    with pytest.raises(ActivationError, match="changed"):
        ActivationManager(store, nginx).activate(blocking_snapshot())
    assert store.read_metadata()["selected_kind"] == "mode_empty"


def test_failed_activation_restores_previous_authoritative_metadata(tmp_path):
    store = CandidateStateStore(tmp_path)
    first = ActivationManager(store, FakeNginx())
    first.activate(snapshot(4))
    nginx = FakeNginx(probes=[False, True], reloads=[True, True])
    with pytest.raises(ActivationError, match="probe"):
        ActivationManager(store, nginx).activate(snapshot(5))
    metadata = store.read_metadata()
    assert metadata["selected_source_revision"] == 4
    assert metadata["selected_kind"] == "authoritative"


def test_failed_previous_rollback_falls_back_to_pending_empty(tmp_path):
    store = CandidateStateStore(tmp_path)
    ActivationManager(store, FakeNginx()).activate(blocking_snapshot(4))
    nginx = FakeNginx(
        probes=[False, True],
        reloads=[True, True],
        validates=[True, False, True],
    )

    with pytest.raises(ActivationError, match="probe"):
        ActivationManager(store, nginx).activate(blocking_snapshot(5))

    assert store.read_metadata()["selected_kind"] == "pending_empty"
    assert store.read_candidate("selected.conf") == store.read_candidate("empty.conf")


def test_disabled_store_never_activates_nonempty_snapshot(tmp_path):
    store = CandidateStateStore(tmp_path)
    store.set_disabled(True)
    manager = ActivationManager(store, FakeNginx())
    result = manager.activate(snapshot())
    assert result.selected_kind == "disabled_empty"


def test_disable_retries_empty_without_restoring_previous_candidate(tmp_path):
    store = CandidateStateStore(tmp_path)
    ActivationManager(store, FakeNginx()).activate(blocking_snapshot(4))
    nginx = FakeNginx(reloads=[False, True])

    result = ActivationManager(store, nginx).deactivate_empty("disabled_empty")

    assert result.selected_kind == "disabled_empty"
    assert store.read_metadata()["selected_kind"] == "disabled_empty"
    assert store.read_candidate("selected.conf") == store.read_candidate("empty.conf")
    assert nginx.reloaded == 2


def test_disable_retries_empty_after_probe_failure(tmp_path):
    store = CandidateStateStore(tmp_path)
    ActivationManager(store, FakeNginx()).activate(blocking_snapshot(4))
    nginx = FakeNginx(probes=[False, True], reloads=[True, True])

    result = ActivationManager(store, nginx).deactivate_empty("disabled_empty")

    assert result.selected_kind == "disabled_empty"
    assert store.read_metadata()["selected_kind"] == "disabled_empty"
    assert store.read_candidate("selected.conf") == store.read_candidate("empty.conf")


def test_empty_transition_is_fatal_when_empty_cannot_be_confirmed(tmp_path):
    store = CandidateStateStore(tmp_path)
    ActivationManager(store, FakeNginx()).activate(blocking_snapshot(4))
    nginx = FakeNginx(reloads=[False, False])

    with pytest.raises(RollbackError, match="empty transition"):
        ActivationManager(store, nginx).deactivate_empty("disabled_empty")

    assert store.read_candidate("selected.conf") == store.read_candidate("empty.conf")


def test_probe_uses_latest_unexpired_item_not_first_item(tmp_path, monkeypatch):
    monkeypatch.setattr("waf_runtime.activation.time.time", lambda: 1000.0)
    store = CandidateStateStore(tmp_path)
    nginx = FakeNginx()
    candidate = Snapshot(
        1,
        "confidence-waf-enforcement-v1",
        8,
        "RECORD_SEARCH",
        "1970-01-01T00:00:00.000Z",
        "8" * 64,
        (
            {
                "entry_id": 1,
                "recommendation_id": 1,
                "source_ip": "203.0.113.7",
                "request_path": "/records/search",
                "expires_at": "1970-01-01T00:15:00.000Z",
            },
            {
                "entry_id": 2,
                "recommendation_id": 2,
                "source_ip": "203.0.113.8",
                "request_path": "/records/search",
                "expires_at": "1970-01-01T00:40:00.000Z",
            },
        ),
    )

    ActivationManager(store, nginx).activate(candidate)

    assert nginx.probe_sources == ["203.0.113.8"]


def test_all_near_expiry_items_remain_pending_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("waf_runtime.activation.time.time", lambda: 1000.0)
    store = CandidateStateStore(tmp_path)
    candidate = Snapshot(
        1,
        "confidence-waf-enforcement-v1",
        9,
        "RECORD_SEARCH",
        "1970-01-01T00:00:00.000Z",
        "9" * 64,
        (
            {
                "entry_id": 1,
                "recommendation_id": 1,
                "source_ip": "203.0.113.7",
                "request_path": "/records/search",
                "expires_at": "1970-01-01T00:16:00.000Z",
            },
        ),
    )

    result = ActivationManager(store, FakeNginx()).activate(candidate)

    assert result.selected_kind == "pending_empty"
    assert store.read_metadata()["selected_source_revision"] is None
    assert store.read_candidate("selected.conf") == store.read_candidate("empty.conf")


def test_activation_rechecks_revision_after_fetch_race(tmp_path):
    store = CandidateStateStore(tmp_path)
    ActivationManager(store, FakeNginx()).activate(blocking_snapshot(5))
    nginx = FakeNginx()

    result = ActivationManager(store, nginx).activate(blocking_snapshot(4))

    assert result.selected_kind == "stale_ignored"
    assert nginx.reloaded == 0
    assert store.read_metadata()["selected_source_revision"] == 5
