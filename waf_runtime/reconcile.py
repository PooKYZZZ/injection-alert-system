from __future__ import annotations

from dataclasses import dataclass

from .activation import ActivationManager
from .render import render_snapshot
from .snapshot import Snapshot
from .state import CandidateStateStore


@dataclass(frozen=True)
class RuntimeConfig:
    mode: str = "off"


class Reconciler:
    def __init__(
        self, store: CandidateStateStore, nginx, fetcher, config: RuntimeConfig
    ):
        self.store = store
        self.nginx = nginx
        self.fetcher = fetcher
        self.config = config

    def reconcile(self) -> str:
        if self.config.mode == "off":
            with self.store.locked():
                self.store.select_candidate(self.store.canonical_empty_path)
                self.store.write_metadata(self._empty_metadata("mode_empty"))
            return "mode_empty"
        if self.config.mode == "enforce" and self.store.is_disabled():
            with self.store.locked():
                self.store.select_candidate(self.store.canonical_empty_path)
                self.store.write_metadata(self._empty_metadata("disabled_empty"))
            return "disabled_empty"
        snapshot: Snapshot = self.fetcher.fetch()
        metadata = self.store.read_metadata()
        if (
            metadata.get("selected_kind") == "authoritative"
            and metadata.get("selected_source_revision") == snapshot.revision
            and metadata.get("selected_source_state_checksum_sha256")
            == snapshot.state_checksum_sha256
        ):
            return "no_change"
        if self.config.mode == "dry_run":
            render_snapshot(snapshot)
            with self.store.locked():
                self.store.select_candidate(self.store.canonical_empty_path)
                self.store.write_metadata(self._empty_metadata("mode_empty"))
            return "mode_empty"
        return (
            ActivationManager(self.store, self.nginx).activate(snapshot).selected_kind
        )

    def _empty_metadata(self, kind: str) -> dict:
        content = self.store.canonical_empty_path.read_bytes()
        return {
            "metadata_schema_version": 1,
            "selected_kind": kind,
            "selected_source_revision": None,
            "selected_source_state_checksum_sha256": None,
            "selected_file_checksum_sha256": self.store.checksum(content),
            "selected_at": None,
        }
