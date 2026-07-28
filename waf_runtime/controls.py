from __future__ import annotations

from datetime import datetime, timezone

from .state import CandidateStateStore


class WafControls:
    def __init__(self, store: CandidateStateStore):
        self.store = store

    def disable(self) -> str:
        with self.store.locked():
            self.store.set_disabled(True)
            self.store.select_candidate(self.store.canonical_empty_path)
            content = self.store.canonical_empty_path.read_bytes()
            self.store.write_metadata(
                {
                    "metadata_schema_version": 1,
                    "selected_kind": "disabled_empty",
                    "selected_source_revision": None,
                    "selected_source_state_checksum_sha256": None,
                    "selected_file_checksum_sha256": self.store.checksum(content),
                    "selected_at": datetime.now(timezone.utc)
                    .isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z"),
                }
            )
        return "Disable completed: dynamic enforcement is latched disabled and empty."

    def enable(self) -> str:
        with self.store.locked():
            self.store.set_disabled(False)
        return (
            "Enable completed: disable latch cleared. Dynamic enforcement is not "
            "yet confirmed active. Selected state: pending_empty."
        )

    def status(self) -> dict[str, object]:
        return {
            "disabled": self.store.is_disabled(),
            "metadata": self.store.read_metadata(),
        }
