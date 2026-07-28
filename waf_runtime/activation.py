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


class ActivationError(RuntimeError):
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
                self._select_empty("disabled_empty")
                return ActivationResult("disabled_empty")
            candidate = render_snapshot(snapshot)
            candidate_path = self.store.write_candidate(
                f"candidate-{snapshot.revision}-{snapshot.state_checksum_sha256[:12]}.conf",
                candidate.content.encode("ascii"),
            )
            if not self.nginx.validate_candidate(candidate_path):
                self._select_empty("pending_empty")
                raise ActivationError("candidate validation failed")
            self.store.select_candidate(candidate_path)
            if not self.nginx.reload_and_confirm():
                self._rollback()
                raise ActivationError("reload confirmation failed")
            if not self.nginx.probe_candidate(candidate_path):
                self._rollback()
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

    def _select_empty(self, kind: str) -> None:
        self.store.select_candidate(self.store.canonical_empty_path)
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

    def _rollback(self) -> None:
        try:
            self._select_empty("pending_empty")
        except OSError as exc:
            raise ActivationError("rollback failed") from exc
