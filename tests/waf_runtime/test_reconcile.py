from __future__ import annotations

from waf_runtime.reconcile import Reconciler, RuntimeConfig
from waf_runtime.snapshot import Snapshot
from waf_runtime.state import CandidateStateStore


class FakeNginx:
    def validate_candidate(self, path):
        return True

    def reload_and_confirm(self):
        return True

    def probe_candidate(self, candidate):
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


def test_dry_run_fetches_but_does_not_reload(tmp_path):
    fetcher = Fetcher(snap())
    nginx = FakeNginx()
    runtime = Reconciler(
        CandidateStateStore(tmp_path), nginx, fetcher, RuntimeConfig(mode="dry_run")
    )
    assert runtime.reconcile() == "mode_empty"
    assert fetcher.calls == 1


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
