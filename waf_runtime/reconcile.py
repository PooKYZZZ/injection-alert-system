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
        self._empty_confirmed = False

    def reconcile(self) -> str:
        if self.config.mode == "off":
            if self._empty_confirmed:
                return "mode_empty"
            with self.store.locked():
                result = ActivationManager(self.store, self.nginx).deactivate_empty(
                    "mode_empty"
                )
            self._empty_confirmed = True
            return result.selected_kind
        if self.config.mode == "enforce" and self.store.is_disabled():
            if self._empty_confirmed:
                return "disabled_empty"
            with self.store.locked():
                result = ActivationManager(
                    self.store, self.nginx
                ).deactivate_empty("disabled_empty")
            self._empty_confirmed = True
            return result.selected_kind
        snapshot: Snapshot = self.fetcher.fetch()
        metadata = self.store.read_metadata()
        selected_revision = metadata.get("selected_source_revision")
        if metadata.get("selected_kind") == "authoritative" and isinstance(
            selected_revision, int
        ):
            if snapshot.revision < selected_revision:
                return "stale_ignored"
            if snapshot.revision == selected_revision:
                if (
                    metadata.get("selected_source_state_checksum_sha256")
                    != snapshot.state_checksum_sha256
                ):
                    return "conflict_rejected"
                if self.store.selected_checksum_matches(
                    metadata.get("selected_file_checksum_sha256")
                ):
                    return "no_change"
        if self.config.mode == "dry_run":
            candidate = render_snapshot(snapshot)
            candidate_path = self.store.write_candidate(
                (
                    f"candidate-dry-run-{snapshot.revision}-"
                    f"{candidate.checksum_sha256[:12]}.conf"
                ),
                candidate.content.encode("ascii"),
            )
            if not self.nginx.validate_candidate(candidate_path):
                raise RuntimeError("dry-run candidate validation failed")
            with self.store.locked():
                self.store.select_candidate(self.store.canonical_empty_path)
                self.store.write_metadata(self._empty_metadata("mode_empty"))
            self._empty_confirmed = True
            return "mode_empty"
        result = ActivationManager(self.store, self.nginx).activate(snapshot)
        self._empty_confirmed = False
        return result.selected_kind

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
