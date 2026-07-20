from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import logging
from collections.abc import Callable

from web_app.domain.enforcement import (
    EffectiveRecommendation,
    EnforcementMode,
    EnforcementPolicy,
    EnforcementScope,
    IEnforcementRecommendationRepository,
    NewEnforcementRecommendation,
)
from web_app.domain.source_address import canonicalize_source_ip
from web_app.observability.structured_logging import log_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ShadowCheckResult:
    decision: str = "ALLOW"
    matched: bool = False
    recommendation: EffectiveRecommendation | None = None


class RecordShadowRecommendationUseCase:
    """Persist a durable, expiring recommendation without applying a control."""

    def __init__(
        self,
        *,
        repository: IEnforcementRecommendationRepository,
        mode: EnforcementMode | str,
        ttl_seconds: int,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._mode = EnforcementMode(mode)
        self._ttl_seconds = ttl_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    async def execute(
        self,
        *,
        alert_id: int | None,
        prediction: str,
        confidence_level: str,
        request_path: str,
    ) -> bool:
        if self._mode is EnforcementMode.OFF or alert_id is None:
            return False
        try:
            recommendation = EnforcementPolicy.recommend(
                prediction=prediction,
                confidence_level=confidence_level,
                request_path=request_path,
            )
        except (TypeError, ValueError):
            return False
        if recommendation is None:
            return False

        created_at = self._clock()
        row = NewEnforcementRecommendation(
            trigger_traffic_log_id=alert_id,
            scope=recommendation.scope,
            tier=recommendation.tier,
            action=recommendation.action,
            mode=EnforcementMode.SHADOW,
            policy_version=recommendation.policy_version,
            created_at=created_at,
            expires_at=created_at + timedelta(seconds=self._ttl_seconds),
        )
        try:
            inserted = await self._repository.insert_if_absent(row)
        except Exception as exc:  # pragma: no cover - exercised through failure test
            log_event(
                logger,
                "enforcement.shadow_recommendation_failed",
                "Shadow recommendation persistence failed; triage result is unchanged",
                level="WARNING",
                alert_id=alert_id,
                error_type=type(exc).__name__,
            )
            return False
        if inserted:
            log_event(
                logger,
                "enforcement.shadow_recommendation_recorded",
                "Recorded an expiring shadow enforcement recommendation",
                alert_id=alert_id,
                scope=row.scope.value,
                tier=row.tier.value,
                recommended_action=row.action.value,
                policy_version=row.policy_version,
                expires_at=row.expires_at.isoformat(),
            )
        return inserted


class CheckShadowEnforcementUseCase:
    """Look up shadow state and report ALLOW regardless of the recommendation."""

    def __init__(
        self,
        *,
        repository: IEnforcementRecommendationRepository,
        mode: EnforcementMode | str,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._mode = EnforcementMode(mode)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    async def execute(
        self, *, source_ip: str | None, scope: EnforcementScope
    ) -> ShadowCheckResult:
        canonical_ip = canonicalize_source_ip(source_ip)
        if self._mode is EnforcementMode.OFF or canonical_ip is None:
            return ShadowCheckResult()
        try:
            recommendation = await self._repository.find_effective_active(
                source_ip=canonical_ip,
                scope=scope,
                now=self._clock(),
            )
        except Exception as exc:  # fail open on the protected request path
            log_event(
                logger,
                "enforcement.shadow_check_failed",
                "Shadow enforcement lookup failed; request remains allowed",
                level="WARNING",
                scope=scope.value,
                error_type=type(exc).__name__,
            )
            return ShadowCheckResult()

        if recommendation is None:
            log_event(
                logger,
                "enforcement.shadow_check",
                "No active shadow recommendation matched the request",
                scope=scope.value,
                matched=False,
                actual_decision="ALLOW",
            )
            return ShadowCheckResult()

        log_event(
            logger,
            "enforcement.shadow_check",
            "An active shadow recommendation matched the request",
            scope=scope.value,
            matched=True,
            recommendation_tier=recommendation.tier.value,
            recommended_action=recommendation.action.value,
            policy_version=recommendation.policy_version,
            source_verification_status=recommendation.source_verification_status,
            actual_decision="ALLOW",
        )
        return ShadowCheckResult(matched=True, recommendation=recommendation)
