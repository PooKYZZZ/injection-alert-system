from __future__ import annotations

from collections.abc import Callable

from .activation import ActivationError, ActivationManager
from .snapshot import SnapshotRejected
from .state import CandidateStateStore


class WafControls:
    def __init__(
        self,
        store: CandidateStateStore,
        nginx,
        reconcile: Callable[[], str] | None = None,
    ):
        self.store = store
        self.nginx = nginx
        self.reconcile = reconcile

    def disable(self) -> str:
        with self.store.locked():
            self.store.set_disabled(True)
            ActivationManager(self.store, self.nginx).deactivate_empty(
                "disabled_empty"
            )
        return "Disable completed: dynamic enforcement is latched disabled and empty."

    def enable(self) -> str:
        with self.store.locked():
            self.store.set_disabled(False)
            ActivationManager(self.store, self.nginx).deactivate_empty("pending_empty")
        selected_kind = "pending_empty"
        if self.reconcile is not None:
            try:
                outcome = self.reconcile()
                if outcome in {"authoritative", "pending_empty", "mode_empty"}:
                    selected_kind = outcome
            except (SnapshotRejected, ActivationError):
                pass
            if selected_kind == "pending_empty":
                selected_kind = self.store.read_metadata().get(
                    "selected_kind", "pending_empty"
                )
        return f"Enable completed: selected state: {selected_kind}."

    def status(self) -> dict[str, object]:
        return {
            "disabled": self.store.is_disabled(),
            "metadata": self.store.read_metadata(),
        }
