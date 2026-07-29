from __future__ import annotations

from .state import CandidateStateStore


class WafControls:
    def __init__(self, store: CandidateStateStore, nginx):
        self.store = store
        self.nginx = nginx

    def disable(self) -> str:
        with self.store.locked():
            self.store.set_disabled(True)
            from .activation import ActivationManager

            ActivationManager(self.store, self.nginx).deactivate_empty(
                "disabled_empty"
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
