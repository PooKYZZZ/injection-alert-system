from __future__ import annotations

from waf_runtime.reconcile import Reconciler, RuntimeConfig
from waf_runtime.snapshot import Snapshot
from waf_runtime.state import CandidateStateStore


class FakeNginx:
    def __init__(self):
        self.validations = 0
        self.reloads = 0

    def validate_candidate(self, path):
        self.validations += 1
        return True

    def reload_and_confirm(self):
        self.reloads += 1
        return True

    def probe_candidate(self, candidate, *args):
        return True

    def probe_empty(self, candidate):
        return True


class Fetcher:
    def __init__(self, value):
        self.value = value
        self.calls = 0

    def fetch(self):
        self.calls += 1
        return self.value


def snap(revision=2):
    return Snapshot(
        1,
        "confidence-waf-enforcement-v1",
        revision,
        "RECORD_SEARCH",
        "2026-07-29T00:00:00.000Z",
        "0" * 64,
        (),
    )


def test_off_mode_selects_empty_without_fetching(tmp_path):
    fetcher = Fetcher(snap())
    runtime = Reconciler(
        CandidateStateStore(tmp_path), FakeNginx(), fetcher, RuntimeConfig(mode="off")
    )
    assert runtime.reconcile() == "mode_empty"
    assert fetcher.calls == 0


def test_repeated_off_mode_does_not_reload_after_empty_is_confirmed(tmp_path):
    nginx = FakeNginx()
    runtime = Reconciler(
        CandidateStateStore(tmp_path), nginx, Fetcher(snap()), RuntimeConfig(mode="off")
    )
    assert runtime.reconcile() == "mode_empty"
    assert runtime.reconcile() == "mode_empty"
    assert nginx.reloads == 1


def test_off_mode_rechecks_empty_file_integrity_each_cycle(tmp_path):
    store = CandidateStateStore(tmp_path)
    nginx = FakeNginx()
    runtime = Reconciler(store, nginx, Fetcher(snap()), RuntimeConfig(mode="off"))
    runtime.reconcile()
    store.selected_path.write_text("corrupt", encoding="ascii")
    assert runtime.reconcile() == "mode_empty"
    assert nginx.reloads == 2


def test_dry_run_fetches_but_does_not_reload(tmp_path):
    fetcher = Fetcher(snap())
    nginx = FakeNginx()
    runtime = Reconciler(
        CandidateStateStore(tmp_path), nginx, fetcher, RuntimeConfig(mode="dry_run")
    )
    assert runtime.reconcile() == "mode_empty"
    assert fetcher.calls == 1
    assert nginx.validations == 1
    assert nginx.reloads == 0


def test_repeated_authoritative_revision_is_no_change(tmp_path):
    fetcher = Fetcher(snap())
    runtime = Reconciler(
        CandidateStateStore(tmp_path),
        FakeNginx(),
        fetcher,
        RuntimeConfig(mode="enforce"),
    )
    runtime.reconcile()
    assert runtime.reconcile() == "no_change"
    assert fetcher.calls == 2


def test_lower_revision_is_ignored(tmp_path):
    store = CandidateStateStore(tmp_path)
    nginx = FakeNginx()
    fetcher = Fetcher(snap(4))
    runtime = Reconciler(store, nginx, fetcher, RuntimeConfig(mode="enforce"))
    runtime.reconcile()
    fetcher.value = snap(3)
    assert runtime.reconcile() == "stale_ignored"
    assert store.read_metadata()["selected_source_revision"] == 4


def test_equal_revision_conflicting_checksum_is_rejected(tmp_path):
    store = CandidateStateStore(tmp_path)
    nginx = FakeNginx()
    fetcher = Fetcher(snap(4))
    runtime = Reconciler(store, nginx, fetcher, RuntimeConfig(mode="enforce"))
    runtime.reconcile()
    conflicting = Snapshot(
        1,
        "confidence-waf-enforcement-v1",
        4,
        "RECORD_SEARCH",
        "2026-07-29T00:00:00.000Z",
        "1" * 64,
        (),
    )
    fetcher.value = conflicting
    assert runtime.reconcile() == "conflict_rejected"
    assert store.read_metadata()["selected_source_revision"] == 4


def test_near_expiry_snapshot_remains_pending_and_is_retried(tmp_path, monkeypatch):
    monkeypatch.setattr("waf_runtime.activation.time.time", lambda: 1000.0)
    near_expiry = Snapshot(
        1,
        "confidence-waf-enforcement-v1",
        50,
        "RECORD_SEARCH",
        "1970-01-01T00:00:00.000Z",
        "5" * 64,
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
    nginx = FakeNginx()
    runtime = Reconciler(
        CandidateStateStore(tmp_path),
        nginx,
        Fetcher(near_expiry),
        RuntimeConfig(mode="enforce"),
    )

    assert runtime.reconcile() == "pending_empty"
    assert runtime.reconcile() == "pending_empty"
    assert runtime.fetcher.calls == 2
    assert runtime.store.read_metadata()["selected_source_revision"] is None


def test_dry_run_prunes_previous_candidate_artifacts(tmp_path):
    fetcher = Fetcher(snap(2))
    runtime = Reconciler(
        CandidateStateStore(tmp_path),
        FakeNginx(),
        fetcher,
        RuntimeConfig(mode="dry_run"),
    )

    runtime.reconcile()
    fetcher.value = snap(3)
    runtime.reconcile()

    assert len(list(runtime.store.candidates_dir.glob("candidate-dry-run-*.conf"))) <= 1
