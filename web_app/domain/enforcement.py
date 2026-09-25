from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol
from urllib.parse import urlsplit

from web_app.domain.classification_scope import is_actionable_attack_class

POLICY_VERSION = "confidence-enforcement-v1"
ACTIVE_POLICY_VERSION = "confidence-enforcement-v3"


class EnforcementScope(StrEnum):
    RECORD_SEARCH = "RECORD_SEARCH"
    RECORD_DETAIL = "RECORD_DETAIL"
    TRACK_STATUS = "TRACK_STATUS"
    SUPPORT_SUBMIT = "SUPPORT_SUBMIT"
    APPOINTMENT_SUBMIT = "APPOINTMENT_SUBMIT"
    COMMENTS_SUBMIT = "COMMENTS_SUBMIT"
    LOGIN_SUBMIT = "LOGIN_SUBMIT"
    REQUEST_COPY_SUBMIT = "REQUEST_COPY_SUBMIT"


class EnforcementTier(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RecommendedAction(StrEnum):
    # v1 values are historical shadow policy intents. v3 keeps LOW monitor-only;
    # legacy LOW challenge rows are handled as non-enforcing state.
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


# These are deliberately narrow CRS signals.  A generic anomaly score or an
# evaluation rule such as 949110 is not sufficient evidence for an application
# block.  The bridge currently emits tags like ``attack-sqli`` and numeric CRS
# rule IDs, so keep both representations in the policy boundary.
STRONG_CRS_TAGS_BY_CLASS = {
    "SQL Injection": frozenset({"attack-sqli"}),
    "Code Injection": frozenset(
        {
            "attack-rce",
            "attack-command-injection",
            "attack-injection-php",
            "attack-injection-nodejs",
        }
    ),
}
STRONG_CRS_RULE_PREFIXES_BY_CLASS = {
    "SQL Injection": ("942",),
    "Code Injection": ("932", "933", "934"),
}
STRONG_CRS_TAGS = frozenset().union(*STRONG_CRS_TAGS_BY_CLASS.values())
STRONG_CRS_RULE_PREFIXES = tuple(
    prefix
    for prefixes in STRONG_CRS_RULE_PREFIXES_BY_CLASS.values()
    for prefix in prefixes
)
_NUMERIC_RULE_ID = re.compile(r"^[0-9]{3,}$")


@dataclass(frozen=True, slots=True)
class EnforcementEvidence:
    """Redacted WAF context used to decide whether ML state may enforce."""

    source_verification_status: str | None = None
    crs_score: int | None = None
    crs_rule_ids: tuple[str, ...] = ()
    matched_rule_tags: tuple[str, ...] = ()

    @property
    def source_verified(self) -> bool:
        return self.source_verification_status == "VERIFIED"

    @property
    def has_strong_waf_evidence(self) -> bool:
        """Whether any supported CRS attack-family signal is present."""

        tags = {tag.strip().lower() for tag in self.matched_rule_tags if tag.strip()}
        if tags.intersection(STRONG_CRS_TAGS):
            return True
        return any(
            _NUMERIC_RULE_ID.fullmatch(rule_id.strip())
            and rule_id.strip().startswith(STRONG_CRS_RULE_PREFIXES)
            for rule_id in self.crs_rule_ids
        )

    def strongly_supports(self, prediction: str) -> bool:
        """Whether CRS evidence belongs to the predicted attack family."""

        tags = {tag.strip().lower() for tag in self.matched_rule_tags if tag.strip()}
        expected_tags = STRONG_CRS_TAGS_BY_CLASS.get(prediction, frozenset())
        if tags.intersection(expected_tags):
            return True

        expected_prefixes = STRONG_CRS_RULE_PREFIXES_BY_CLASS.get(prediction, ())
        return any(
            _NUMERIC_RULE_ID.fullmatch(rule_id.strip())
            and rule_id.strip().startswith(expected_prefixes)
            for rule_id in self.crs_rule_ids
        )

    def to_context(self, *, prediction: str | None = None) -> dict[str, object]:
        """Return bounded, non-payload evidence suitable for JSON persistence."""

        context: dict[str, object] = {
            "source_verification_status": self.source_verification_status,
            "crs_score": self.crs_score,
            "crs_rule_ids": list(self.crs_rule_ids[:32]),
            "matched_rule_tags": list(self.matched_rule_tags[:32]),
            "strong_waf_evidence": self.has_strong_waf_evidence,
        }
        if prediction is not None:
            context["strong_waf_evidence_for_prediction"] = self.strongly_supports(
                prediction
            )
        return context


def evidence_from_waf_fields(
    *,
    source_verification_status: str | object | None,
    crs_score: int | None,
    crs_rule_ids: list[str] | tuple[str, ...] | None,
    matched_rule_tags: list[str] | tuple[str, ...] | None,
) -> EnforcementEvidence:
    """Build policy evidence from already-redacted WAF fields."""

    status = getattr(source_verification_status, "value", source_verification_status)
    return EnforcementEvidence(
        source_verification_status=str(status) if status is not None else None,
        crs_score=crs_score,
        crs_rule_ids=tuple(str(value)[:64] for value in (crs_rule_ids or ())),
        matched_rule_tags=tuple(
            str(value)[:128] for value in (matched_rule_tags or ())
        ),
    )


def scope_for_request_path(request_path: str) -> EnforcementScope | None:
    """Map the portal's public dynamic routes to the shared policy scope."""

    path = urlsplit(request_path or "").path
    exact = {
        "/records/search": EnforcementScope.RECORD_SEARCH,
        "/transactions/status": EnforcementScope.TRACK_STATUS,
        "/support/submit": EnforcementScope.SUPPORT_SUBMIT,
        "/appointments/submit": EnforcementScope.APPOINTMENT_SUBMIT,
        "/comments/submit": EnforcementScope.COMMENTS_SUBMIT,
        "/login/submit": EnforcementScope.LOGIN_SUBMIT,
    }
    if path in exact:
        return exact[path]
    if re.fullmatch(r"/records/[^/]+/request-copy(?:/submit)?", path):
        return EnforcementScope.REQUEST_COPY_SUBMIT
    if re.fullmatch(r"/records/[^/]+", path):
        return EnforcementScope.RECORD_DETAIL
    return None


@dataclass(frozen=True, slots=True)
class PolicyRecommendation:
    scope: EnforcementScope
    tier: EnforcementTier
    action: RecommendedAction
    policy_version: str = POLICY_VERSION
    decision_reason: str = ""
    evidence_context: dict[str, object] | None = None


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
    decision_reason: str = ""
    evidence_context: dict[str, object] | None = None


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
    decision_reason: str = ""
    evidence_context: dict[str, object] | None = None


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

    async def count_recent_suspicious_events(
        self,
        *,
        source_ip: str,
        scope: EnforcementScope,
        now: datetime,
        window_seconds: int,
    ) -> int: ...

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
        evidence: EnforcementEvidence | None = None,
    ) -> PolicyRecommendation | None:
        if not prediction:
            raise ValueError("prediction is required")
        if not confidence_level:
            raise ValueError("confidence_level is required")

        try:
            tier = EnforcementTier(confidence_level)
        except ValueError:
            raise ValueError(f"Unknown confidence_level: {confidence_level}") from None

        scope = scope_for_request_path(request_path)
        if scope is None or not is_actionable_attack_class(prediction):
            return None

        selected_mode = EnforcementMode(mode)
        policy_version = (
            ACTIVE_POLICY_VERSION
            if selected_mode is EnforcementMode.ENFORCE
            else POLICY_VERSION
        )

        selected_evidence = evidence or EnforcementEvidence()
        action = cls._ACTIONS[tier]
        if tier in {EnforcementTier.HIGH, EnforcementTier.CRITICAL}:
            if selected_evidence.strongly_supports(prediction):
                decision_reason = "STRONG_CRS_EVIDENCE"
            else:
                action = RecommendedAction.MONITOR
                decision_reason = "STRONG_CRS_EVIDENCE_REQUIRED"
        elif tier is EnforcementTier.MEDIUM:
            decision_reason = "REPEAT_OR_STRONG_CRS_EVIDENCE_REQUIRED"
        else:
            decision_reason = "LOW_MONITOR_ONLY"

        return PolicyRecommendation(
            scope=scope,
            tier=tier,
            action=action,
            policy_version=policy_version,
            decision_reason=decision_reason,
            evidence_context=selected_evidence.to_context(prediction=prediction),
        )
