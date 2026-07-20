from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


POLICY_VERSION = "confidence-enforcement-v1"


class EnforcementScope(StrEnum):
    RECORD_SEARCH = "RECORD_SEARCH"


class EnforcementTier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendedAction(StrEnum):
    # These are shadow policy intents only. They do not apply controls.
    MONITOR = "MONITOR"
    THROTTLE = "THROTTLE"
    APPLICATION_BLOCK = "APPLICATION_BLOCK"
    WAF_BLOCK = "WAF_BLOCK"


class EnforcementMode(StrEnum):
    OFF = "off"
    SHADOW = "shadow"


@dataclass(frozen=True, slots=True)
class PolicyRecommendation:
    scope: EnforcementScope
    tier: EnforcementTier
    action: RecommendedAction
    policy_version: str = POLICY_VERSION


class EnforcementPolicy:
    """Pure PR4 mapping from completed WAF classification to shadow intent."""

    _ACTIONS = {
        EnforcementTier.LOW: RecommendedAction.MONITOR,
        EnforcementTier.MEDIUM: RecommendedAction.THROTTLE,
        EnforcementTier.HIGH: RecommendedAction.APPLICATION_BLOCK,
        EnforcementTier.CRITICAL: RecommendedAction.WAF_BLOCK,
    }

    @classmethod
    def recommend(
        cls,
        *,
        prediction: str,
        confidence_level: str,
        request_path: str,
    ) -> PolicyRecommendation | None:
        if not prediction:
            raise ValueError("prediction is required")
        if not confidence_level:
            raise ValueError("confidence_level is required")

        try:
            tier = EnforcementTier(confidence_level)
        except ValueError:
            raise ValueError(f"Unknown confidence_level: {confidence_level}") from None

        if request_path != "/records/search" or prediction == "Normal":
            return None

        return PolicyRecommendation(
            scope=EnforcementScope.RECORD_SEARCH,
            tier=tier,
            action=cls._ACTIONS[tier],
        )
