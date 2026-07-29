from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .render import render_snapshot
from .snapshot import Snapshot
from .state import CandidateStateStore


class NginxActivation(Protocol):
    def validate_candidate(self, path: Path) -> bool: ...
    def reload_and_confirm(self) -> bool: ...
    def probe_candidate(self, candidate: Path) -> bool: ...
    def probe_empty(self, candidate: Path) -> bool: ...


class ActivationError(RuntimeError):
    pass


class RollbackError(ActivationError):
    pass


class ActivationResult:
    def __init__(self, selected_kind: str):
        self.selected_kind = selected_kind


class ActivationManager:
    def __init__(self, store: CandidateStateStore, nginx: NginxActivation):
        self.store = store
        self.nginx = nginx

    def activate(self, snapshot: Snapshot) -> ActivationResult:
        with self.store.locked():
            if self.store.is_disabled():
                return self.deactivate_empty("disabled_empty")
            previous_metadata = self.store.read_metadata()
            candidate = render_snapshot(snapshot)
            candidate_path = self.store.write_candidate(
                f"candidate-{snapshot.revision}-{snapshot.state_checksum_sha256[:12]}.conf",
                candidate.content.encode("ascii"),
            )
            if not self.nginx.validate_candidate(candidate_path):
                raise ActivationError("candidate validation failed")
            if (
                self.store.checksum(candidate_path.read_bytes())
                != candidate.checksum_sha256
            ):
                raise ActivationError("candidate changed after validation")
            self.store.select_candidate(candidate_path, candidate.checksum_sha256)
            if not self.nginx.reload_and_confirm():
                self._restore_previous(previous_metadata, reload=True)
                raise ActivationError("reload confirmation failed")
            if not self.nginx.probe_candidate(candidate_path):
                self._restore_previous(previous_metadata, reload=True)
                raise ActivationError("candidate probe failed")
            self.store.write_metadata(
                {
                    "metadata_schema_version": 1,
                    "selected_kind": "authoritative",
                    "selected_source_revision": snapshot.revision,
                    "selected_source_state_checksum_sha256": (
                        snapshot.state_checksum_sha256
                    ),
                    "selected_file_checksum_sha256": candidate.checksum_sha256,
                    "selected_at": datetime.now(timezone.utc)
                    .isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z"),
                }
            )
            self.store.prune_candidates()
            return ActivationResult("authoritative")

    def deactivate_empty(self, kind: str) -> ActivationResult:
        previous_metadata = self.store.read_metadata()
        self.store.select_candidate(self.store.canonical_empty_path)
        if not self.nginx.validate_candidate(self.store.selected_path):
            self._restore_previous(previous_metadata)
            raise ActivationError("empty candidate validation failed")
        if not self.nginx.reload_and_confirm():
            self._restore_previous(previous_metadata, reload=True)
            raise ActivationError("empty candidate reload failed")
        if not self.nginx.probe_empty(self.store.selected_path):
            self._restore_previous(previous_metadata, reload=True)
            raise ActivationError("empty candidate probe failed")
        self._write_empty_metadata(kind)
        return ActivationResult(kind)

    def _write_empty_metadata(self, kind: str) -> None:
        content = self.store.canonical_empty_path.read_bytes()
        self.store.write_metadata(
            {
                "metadata_schema_version": 1,
                "selected_kind": kind,
                "selected_source_revision": None,
                "selected_source_state_checksum_sha256": None,
                "selected_file_checksum_sha256": self.store.checksum(content),
                "selected_at": datetime.now(timezone.utc)
                .isoformat(timespec="milliseconds")
                .replace("+00:00", "Z"),
            }
        )

    def _restore_previous(self, metadata: dict, *, reload: bool = False) -> None:
        try:
            self.store.restore_previous()
            self.store.write_metadata(metadata)
            if reload:
                if not self.nginx.validate_candidate(self.store.selected_path):
                    raise ActivationError("previous candidate validation failed")
                if not self.nginx.reload_and_confirm():
                    raise ActivationError("previous candidate reload failed")
                probe = (
                    self.nginx.probe_candidate
                    if metadata.get("selected_kind") == "authoritative"
                    else self.nginx.probe_empty
                )
                if not probe(self.store.selected_path):
                    raise ActivationError("previous candidate probe failed")
        except (ActivationError, OSError, ValueError) as exc:
            raise RollbackError("rollback failed") from exc
