"""Central policy separating classifier observations from alert actionability."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class ClassificationScope(StrEnum):
    """Operational meaning assigned to a persisted classifier label."""

    BENIGN = "BENIGN"
    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


BENIGN_CLASS: Final[str] = "Normal"

# This is intentionally a positive allowlist.  Adding a new operational attack
# requires changing this policy and its tests rather than inheriting alerting by
# default from a new model label.
ACTIONABLE_ATTACK_CLASSES: Final[frozenset[str]] = frozenset(
    {"SQL Injection", "Code Injection"}
)

OPERATIONAL_TRAFFIC_CLASSES: Final[frozenset[str]] = frozenset(
    {BENIGN_CLASS, *ACTIONABLE_ATTACK_CLASSES}
)


def classification_scope(prediction: str | None) -> ClassificationScope:
    """Return the fail-closed operational scope for a classifier prediction."""

    if prediction == BENIGN_CLASS:
        return ClassificationScope.BENIGN
    if prediction in ACTIONABLE_ATTACK_CLASSES:
        return ClassificationScope.IN_SCOPE
    return ClassificationScope.OUT_OF_SCOPE


def is_actionable_attack_class(prediction: str | None) -> bool:
    """Whether a prediction may enter the operational security-alert path."""

    return prediction in ACTIONABLE_ATTACK_CLASSES


def is_operational_traffic_class(prediction: str | None) -> bool:
    """Whether a retained row may contribute to operational traffic views."""

    return prediction in OPERATIONAL_TRAFFIC_CLASSES
