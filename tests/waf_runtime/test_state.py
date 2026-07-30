from __future__ import annotations

import json

from waf_runtime.render import render_candidate
from waf_runtime.state import CandidateStateStore


def test_lock_file_is_permanent_and_metadata_is_atomic(tmp_path) -> None:
    store = CandidateStateStore(tmp_path)
    first = store.lock_inode()
    store.write_candidate("candidate-4.conf", render_candidate(4, []).content.encode())
    store.write_metadata({"selected_kind": "mode_empty"})
    assert store.lock_inode() == first
    assert json.loads(store.metadata_path.read_text()) == {
        "selected_kind": "mode_empty"
    }
    assert store.read_candidate("candidate-4.conf") == b"# PR7 dynamic WAF candidate\n"


def test_disabled_latch_survives_store_reopen(tmp_path) -> None:
    CandidateStateStore(tmp_path).set_disabled(True)
    reopened = CandidateStateStore(tmp_path)
    assert reopened.is_disabled()
    reopened.set_disabled(False)
    assert not reopened.is_disabled()


def test_pruning_keeps_protected_files(tmp_path) -> None:
    store = CandidateStateStore(tmp_path)
    store.write_candidate("candidate-1.conf", b"one")
    store.write_candidate("candidate-2.conf", b"two")
    store.write_candidate("candidate-3.conf", b"three")
    store.write_metadata({"selected_kind": "mode_empty"})
    store.prune_candidates(keep=1)
    assert store.metadata_path.exists()
    assert store.lock_path.exists()
    assert store.canonical_empty_path.exists()
    assert len(list(store.candidates_dir.glob("candidate-*.conf"))) == 1


def test_corrupt_canonical_empty_is_restored(tmp_path) -> None:
    (tmp_path / "empty.conf").write_bytes(b"malicious rules")

    CandidateStateStore(tmp_path)

    assert (tmp_path / "empty.conf").read_bytes() == b"# PR7 dynamic WAF candidate\n"
