from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from web_app.domain.classification_scope import is_actionable_attack_class

POLICY_VERSION = "confidence-enforcement-v1"
ACTIVE_POLICY_VERSION = "confidence-enforcement-v2"


class EnforcementScope(StrEnum):
    RECORD_SEARCH = "RECORD_SEARCH"


class EnforcementTier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendedAction(StrEnum):
    # v1 values are historical shadow policy intents. v2 adds CHALLENGE for LOW.
    MONITOR = "MONITOR"
    CHALLENGE = "CHALLENGE"
    THROTTLE = "THROTTLE"
    APPLICATION_BLOCK = "APPLICATION_BLOCK"
    WAF_BLOCK = "WAF_BLOCK"


class EnforcementMode(StrEnum):
    OFF = "off"
    SHADOW = "shadow"
    ENFORCE = "enforce"


class EnforcementDecision(StrEnum):
    ALLOW = "ALLOW"
    CHALLENGE = "CHALLENGE"
    THROTTLE = "THROTTLE"
    BLOCK = "BLOCK"


class CounterKind(StrEnum):
    LOW_LIGHT = "LOW_LIGHT"
    MEDIUM_HARD = "MEDIUM_HARD"


@dataclass(frozen=True, slots=True)
class PolicyRecommendation:
    scope: EnforcementScope
    tier: EnforcementTier
    action: RecommendedAction
    policy_version: str = POLICY_VERSION


@dataclass(frozen=True, slots=True)
class NewEnforcementRecommendation:
    trigger_traffic_log_id: int
    scope: EnforcementScope
    tier: EnforcementTier
    action: RecommendedAction
    mode: EnforcementMode
    policy_version: str
    created_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class EffectiveRecommendation:
    trigger_traffic_log_id: int
    scope: EnforcementScope
    tier: EnforcementTier
    action: RecommendedAction
    mode: EnforcementMode
    policy_version: str
    created_at: datetime
    expires_at: datetime
    source_verification_status: str


@dataclass(frozen=True, slots=True)
class RequestWindowState:
    source_ip: str
    scope: EnforcementScope
    counter_kind: CounterKind
    policy_version: str
    window_start: datetime
    window_end: datetime
    request_count: int


@dataclass(frozen=True, slots=True)
class ChallengeGrant:
    source_ip: str
    scope: EnforcementScope
    tier: EnforcementTier
    policy_version: str
    verified_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class TurnstileVerificationResult:
    success: bool
    unavailable: bool = False


class IEnforcementRecommendationRepository(Protocol):
    async def insert_if_absent(
        self, recommendation: NewEnforcementRecommendation
    ) -> bool: ...

    async def find_effective_active(
        self,
        *,
        source_ip: str,
        scope: EnforcementScope,
        now: datetime,
    ) -> EffectiveRecommendation | None: ...

    async def find_effective_enforceable(
        self,
        *,
        source_ip: str,
        scope: EnforcementScope,
        now: datetime,
        policy_version: str,
        require_verified: bool,
    ) -> EffectiveRecommendation | None: ...

    async def increment_request_window(
        self,
        *,
        source_ip: str,
        scope: EnforcementScope,
        counter_kind: CounterKind,
        policy_version: str,
        now: datetime,
        window_seconds: int,
    ) -> RequestWindowState: ...

    async def find_valid_challenge_grant(
        self,
        *,
        source_ip: str,
        scope: EnforcementScope,
        tier: EnforcementTier,
        policy_version: str,
        now: datetime,
    ) -> ChallengeGrant | None: ...

    async def upsert_challenge_grant(self, grant: ChallengeGrant) -> ChallengeGrant: ...


class EnforcementPolicy:
    """Map completed malicious classifications to versioned enforcement intents."""

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
        mode: EnforcementMode | str = EnforcementMode.SHADOW,
    ) -> PolicyRecommendation | None:
        if not prediction:
            raise ValueError("prediction is required")
        if not confidence_level:
            raise ValueError("confidence_level is required")

        try:
            tier = EnforcementTier(confidence_level)
        except ValueError:
            raise ValueError(f"Unknown confidence_level: {confidence_level}") from None

        if request_path != "/records/search" or not is_actionable_attack_class(
            prediction
        ):
            return None

        selected_mode = EnforcementMode(mode)
        actions = cls._ACTIONS
        policy_version = POLICY_VERSION
        if selected_mode is EnforcementMode.ENFORCE:
            actions = {
                **cls._ACTIONS,
                EnforcementTier.LOW: RecommendedAction.CHALLENGE,
            }
            policy_version = ACTIVE_POLICY_VERSION

        return PolicyRecommendation(
            scope=EnforcementScope.RECORD_SEARCH,
            tier=tier,
            action=actions[tier],
            policy_version=policy_version,
        )
