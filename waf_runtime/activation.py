from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .render import render_snapshot
from .snapshot import Snapshot, _timestamp_epoch
from .state import CandidateStateStore


class NginxActivation(Protocol):
    def validate_candidate(self, path: Path) -> bool: ...
    def reload_and_confirm(self) -> bool: ...
    def probe_candidate(
        self,
        candidate: Path,
        source_ip: str | None = None,
        revision: int | None = None,
        recommendation_id: int | None = None,
    ) -> bool: ...
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
            decision = self._revision_decision(snapshot)
            if decision is not None:
                return ActivationResult(decision)
            previous_metadata = self.store.read_metadata()
            candidate = render_snapshot(snapshot)
            if candidate.entry_count == 0:
                return self._activate_authoritative_empty(snapshot, previous_metadata)
            probe_item = self._probe_item(snapshot)
            if probe_item is None:
                return self.deactivate_empty("pending_empty")
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
                self._restore_previous(previous_metadata)
                raise ActivationError("reload confirmation failed")
            if not self.nginx.probe_candidate(
                candidate_path,
                probe_item["source_ip"],
                snapshot.revision,
                probe_item["recommendation_id"],
            ):
                self._restore_previous(previous_metadata)
                raise ActivationError("candidate probe failed")
            self.store.write_metadata(
                self._authoritative_metadata(
                    snapshot, candidate.checksum_sha256, probe_item
                )
            )
            self.store.prune_candidates()
            return ActivationResult("authoritative")

    def deactivate_empty(self, kind: str) -> ActivationResult:
        self.store.select_candidate(self.store.canonical_empty_path)
        try:
            self._confirm_empty()
        except (ActivationError, OSError, ValueError):
            try:
                self.store.select_candidate(self.store.canonical_empty_path)
                self._confirm_empty()
            except (ActivationError, OSError, ValueError) as second_error:
                raise RollbackError("empty transition failed") from second_error
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

    def _activate_authoritative_empty(
        self, snapshot: Snapshot, previous_metadata: dict
    ) -> ActivationResult:
        self.store.select_candidate(self.store.canonical_empty_path)
        try:
            self._confirm_empty()
        except (ActivationError, OSError, ValueError):
            try:
                self.store.select_candidate(self.store.canonical_empty_path)
                self._confirm_empty()
            except (ActivationError, OSError, ValueError) as second_error:
                raise RollbackError("empty transition failed") from second_error
        content = self.store.canonical_empty_path.read_bytes()
        self.store.write_metadata(
            self._authoritative_metadata(
                snapshot,
                self.store.checksum(content),
            )
        )
        return ActivationResult("authoritative")

    def _authoritative_metadata(
        self,
        snapshot: Snapshot,
        candidate_checksum: str,
        probe_item: dict | None = None,
    ) -> dict:
        metadata = {
            "metadata_schema_version": 1,
            "selected_kind": "authoritative",
            "selected_source_revision": snapshot.revision,
            "selected_source_state_checksum_sha256": snapshot.state_checksum_sha256,
            "selected_file_checksum_sha256": candidate_checksum,
            "selected_at": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
        }
        if probe_item is not None:
            metadata["selected_probe_source_ip"] = probe_item["source_ip"]
            metadata["selected_probe_recommendation_id"] = probe_item[
                "recommendation_id"
            ]
        return metadata

    def _revision_decision(self, snapshot: Snapshot) -> str | None:
        metadata = self.store.read_metadata()
        selected_revision = metadata.get("selected_source_revision")
        if metadata.get("selected_kind") != "authoritative" or not isinstance(
            selected_revision, int
        ):
            return None
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
        return None

    def _restore_previous(self, metadata: dict) -> None:
        try:
            self.store.restore_previous()
            if self._confirm_selected(metadata):
                self.store.write_metadata(metadata)
                return
        except (ActivationError, OSError, ValueError):
            pass
        try:
            self.store.select_candidate(self.store.canonical_empty_path)
            if not self.nginx.validate_candidate(self.store.selected_path):
                raise ActivationError("empty fallback validation failed")
            if not self.nginx.reload_and_confirm():
                raise ActivationError("empty fallback reload failed")
            if not self.nginx.probe_empty(self.store.selected_path):
                raise ActivationError("empty fallback probe failed")
            self._write_empty_metadata("pending_empty")
        except (ActivationError, OSError, ValueError) as exc:
            raise RollbackError("rollback failed") from exc

    def _confirm_selected(self, metadata: dict) -> bool:
        if not self.nginx.validate_candidate(self.store.selected_path):
            return False
        if not self.nginx.reload_and_confirm():
            return False
        if metadata.get("selected_kind") == "authoritative":
            return self.nginx.probe_candidate(
                self.store.selected_path,
                metadata.get("selected_probe_source_ip"),
                metadata.get("selected_source_revision"),
                metadata.get("selected_probe_recommendation_id"),
            )
        return self.nginx.probe_empty(self.store.selected_path)

    def _confirm_empty(self) -> None:
        if not self.nginx.validate_candidate(self.store.selected_path):
            raise ActivationError("empty candidate validation failed")
        if not self.nginx.reload_and_confirm():
            raise ActivationError("empty candidate reload failed")
        if not self.nginx.probe_empty(self.store.selected_path):
            raise ActivationError("empty candidate probe failed")

    def _probe_item(self, snapshot: Snapshot) -> dict | None:
        if not snapshot.items:
            return None
        latest = max(
            snapshot.items,
            key=lambda item: _timestamp_epoch(item["expires_at"]) // 1000 - 1,
        )
        cutoff = _timestamp_epoch(latest["expires_at"]) // 1000 - 1
        required_seconds = max(1, math.ceil(getattr(self.nginx, "timeout", 5.0) * 3))
        if cutoff - time.time() < required_seconds:
            return None
        return latest
