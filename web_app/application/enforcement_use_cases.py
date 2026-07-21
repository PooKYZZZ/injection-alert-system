from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from web_app.domain.enforcement import (
    ACTIVE_POLICY_VERSION,
    ChallengeGrant,
    CounterKind,
    EffectiveRecommendation,
    EnforcementDecision,
    EnforcementMode,
    EnforcementPolicy,
    EnforcementScope,
    EnforcementTier,
    IEnforcementRecommendationRepository,
    NewEnforcementRecommendation,
    TurnstileVerificationResult,
)
from web_app.domain.source_address import canonicalize_source_ip
from web_app.observability.structured_logging import log_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ShadowCheckResult:
    decision: str = "ALLOW"
    matched: bool = False
    recommendation: EffectiveRecommendation | None = None
    degraded: bool = False


@dataclass(frozen=True, slots=True)
class ActiveEnforcementResult:
    decision: str = EnforcementDecision.ALLOW.value
    matched: bool = False
    recommendation: EffectiveRecommendation | None = None
    retry_after_seconds: int | None = None
    challenge_tier: str | None = None
    degraded: bool = False


@dataclass(frozen=True, slots=True)
class EnforcementChallengeResult:
    verified: bool = False
    status: str = "INVALID"
    grant_expires_at: datetime | None = None


class VerifyEnforcementChallengeUseCase:
    """Verify a challenge server-side and persist only bounded grant metadata."""

    def __init__(
        self,
        *,
        repository: IEnforcementRecommendationRepository,
        verifier,
        mode: EnforcementMode | str,
        grant_ttl_seconds: int,
        allow_unverified_source_for_tests: bool,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._verifier = verifier
        self._mode = EnforcementMode(mode)
        self._grant_ttl_seconds = grant_ttl_seconds
        self._allow_unverified_source_for_tests = allow_unverified_source_for_tests
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    async def execute(
        self, *, source_ip: str | None, scope: EnforcementScope, token: str
    ) -> EnforcementChallengeResult:
        canonical_ip = canonicalize_source_ip(source_ip)
        if (
            self._mode is not EnforcementMode.ENFORCE
            or canonical_ip is None
            or not isinstance(token, str)
            or not 1 <= len(token) <= 2048
        ):
            return EnforcementChallengeResult()

        now = self._clock()
        try:
            recommendation = await self._repository.find_effective_enforceable(
                source_ip=canonical_ip,
                scope=scope,
                now=now,
                policy_version=ACTIVE_POLICY_VERSION,
            )
            if recommendation is None:
                return EnforcementChallengeResult(status="NO_ACTIVE_ENFORCEMENT")
            if (
                recommendation.source_verification_status != "VERIFIED"
                and not self._allow_unverified_source_for_tests
            ):
                return EnforcementChallengeResult(status="SOURCE_INELIGIBLE")

            tier = recommendation.tier
            existing = await self._repository.find_valid_challenge_grant(
                source_ip=canonical_ip,
                scope=scope,
                tier=tier,
                policy_version=ACTIVE_POLICY_VERSION,
                now=now,
            )
            if existing is not None:
                return EnforcementChallengeResult(
                    verified=True,
                    status="VERIFIED",
                    grant_expires_at=existing.expires_at,
                )

            verification = await self._verifier.verify(
                token=token,
                remote_ip=canonical_ip,
            )
            if not verification.success:
                return EnforcementChallengeResult(
                    status="UNAVAILABLE" if verification.unavailable else "INVALID"
                )

            # Siteverify is external: bind a grant only after the recommendation
            # is read again and remains eligible.
            current = await self._repository.find_effective_enforceable(
                source_ip=canonical_ip,
                scope=scope,
                now=now,
                policy_version=ACTIVE_POLICY_VERSION,
            )
            if current is None or current.tier is not tier:
                return EnforcementChallengeResult(status="NO_ACTIVE_ENFORCEMENT")
            expires_at = min(
                now + timedelta(seconds=self._grant_ttl_seconds),
                current.expires_at,
            )
            if expires_at <= now:
                return EnforcementChallengeResult(status="NO_ACTIVE_ENFORCEMENT")
            grant = ChallengeGrant(
                source_ip=canonical_ip,
                scope=scope,
                tier=tier,
                policy_version=ACTIVE_POLICY_VERSION,
                verified_at=now,
                expires_at=expires_at,
            )
            await self._repository.upsert_challenge_grant(grant)
            return EnforcementChallengeResult(
                verified=True,
                status="VERIFIED",
                grant_expires_at=expires_at,
            )
        except Exception as exc:  # challenge failure never creates a bypass grant
            log_event(
                logger,
                "enforcement.challenge_failed",
                "Enforcement challenge verification failed",
                level="WARNING",
                scope=scope.value,
                error_type=type(exc).__name__,
            )
            return EnforcementChallengeResult(status="UNAVAILABLE")


class EvaluateEnforcementUseCase:
    """Evaluate explicit v2 LOW/MEDIUM state for the protected search route."""

    def __init__(
        self,
        *,
        repository: IEnforcementRecommendationRepository,
        mode: EnforcementMode | str,
        low_window_seconds: int,
        low_max_unchallenged_requests: int,
        medium_window_seconds: int,
        medium_max_requests: int,
        allow_unverified_source_for_tests: bool,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._mode = EnforcementMode(mode)
        self._low_window_seconds = low_window_seconds
        self._low_max_unchallenged_requests = low_max_unchallenged_requests
        self._medium_window_seconds = medium_window_seconds
        self._medium_max_requests = medium_max_requests
        self._allow_unverified_source_for_tests = allow_unverified_source_for_tests
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    async def execute(
        self, *, source_ip: str | None, scope: EnforcementScope
    ) -> ActiveEnforcementResult:
        canonical_ip = canonicalize_source_ip(source_ip)
        if self._mode is not EnforcementMode.ENFORCE or canonical_ip is None:
            return ActiveEnforcementResult()

        now = self._clock()
        try:
            recommendation = await self._repository.find_effective_enforceable(
                source_ip=canonical_ip,
                scope=scope,
                now=now,
                policy_version=ACTIVE_POLICY_VERSION,
            )
            if recommendation is None:
                return ActiveEnforcementResult()
            if (
                recommendation.source_verification_status != "VERIFIED"
                and not self._allow_unverified_source_for_tests
            ):
                log_event(
                    logger,
                    "enforcement.active_source_ineligible",
                    "Active enforcement source is not verified; request remains allowed",
                    level="WARNING",
                    scope=scope.value,
                    source_verification_status=recommendation.source_verification_status,
                    policy_version=recommendation.policy_version,
                )
                return ActiveEnforcementResult()

            if recommendation.tier is EnforcementTier.LOW:
                grant = await self._repository.find_valid_challenge_grant(
                    source_ip=canonical_ip,
                    scope=scope,
                    tier=EnforcementTier.LOW,
                    policy_version=ACTIVE_POLICY_VERSION,
                    now=now,
                )
                if grant is not None:
                    return ActiveEnforcementResult(
                        matched=True,
                        recommendation=recommendation,
                    )
                state = await self._repository.increment_request_window(
                    source_ip=canonical_ip,
                    scope=scope,
                    counter_kind=CounterKind.LOW_LIGHT,
                    policy_version=ACTIVE_POLICY_VERSION,
                    now=now,
                    window_seconds=self._low_window_seconds,
                )
                if state.request_count > self._low_max_unchallenged_requests:
                    return ActiveEnforcementResult(
                        decision=EnforcementDecision.CHALLENGE.value,
                        matched=True,
                        recommendation=recommendation,
                        challenge_tier=EnforcementTier.LOW.value,
                    )
                return ActiveEnforcementResult(
                    matched=True,
                    recommendation=recommendation,
                )

            grant = await self._repository.find_valid_challenge_grant(
                source_ip=canonical_ip,
                scope=scope,
                tier=EnforcementTier.MEDIUM,
                policy_version=ACTIVE_POLICY_VERSION,
                now=now,
            )
            if grant is None:
                return ActiveEnforcementResult(
                    decision=EnforcementDecision.CHALLENGE.value,
                    matched=True,
                    recommendation=recommendation,
                    challenge_tier=EnforcementTier.MEDIUM.value,
                )
            state = await self._repository.increment_request_window(
                source_ip=canonical_ip,
                scope=scope,
                counter_kind=CounterKind.MEDIUM_HARD,
                policy_version=ACTIVE_POLICY_VERSION,
                now=now,
                window_seconds=self._medium_window_seconds,
            )
            if state.request_count > self._medium_max_requests:
                retry_after = max(1, math.ceil((state.window_end - now).total_seconds()))
                return ActiveEnforcementResult(
                    decision=EnforcementDecision.THROTTLE.value,
                    matched=True,
                    recommendation=recommendation,
                    retry_after_seconds=retry_after,
                )
            return ActiveEnforcementResult(
                matched=True,
                recommendation=recommendation,
            )
        except Exception as exc:  # protected request path is fail-open
            log_event(
                logger,
                "enforcement.active_check_failed",
                "Active enforcement evaluation failed; request remains allowed",
                level="WARNING",
                scope=scope.value,
                error_type=type(exc).__name__,
            )
            return ActiveEnforcementResult(degraded=True)


class RecordShadowRecommendationUseCase:
    """Persist a durable, expiring v1 shadow or v2 active recommendation."""

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
        occurred_at: datetime | None = None,
    ) -> bool:
        if self._mode is EnforcementMode.OFF or alert_id is None:
            return False
        try:
            recommendation = EnforcementPolicy.recommend(
                prediction=prediction,
                confidence_level=confidence_level,
                request_path=request_path,
                mode=self._mode,
            )
        except (TypeError, ValueError):
            return False
        if recommendation is None:
            return False

        created_at = self._clock()
        event_time = occurred_at if isinstance(occurred_at, datetime) else created_at
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        expires_at = event_time + timedelta(seconds=self._ttl_seconds)
        if expires_at <= created_at:
            return False
        row = NewEnforcementRecommendation(
            trigger_traffic_log_id=alert_id,
            scope=recommendation.scope,
            tier=recommendation.tier,
            action=recommendation.action,
            mode=self._mode,
            policy_version=recommendation.policy_version,
            created_at=created_at,
            expires_at=expires_at,
        )
        try:
            inserted = await self._repository.insert_if_absent(row)
        except Exception as exc:  # pragma: no cover - exercised through failure test
            log_event(
                logger,
                "enforcement.recommendation_failed",
                "Enforcement recommendation persistence failed; triage result is unchanged",
                level="WARNING",
                alert_id=alert_id,
                error_type=type(exc).__name__,
            )
            return False
        if inserted:
            log_event(
                logger,
                "enforcement.recommendation_recorded",
                "Recorded an expiring enforcement recommendation",
                alert_id=alert_id,
                scope=row.scope.value,
                tier=row.tier.value,
                recommended_action=row.action.value,
                policy_version=row.policy_version,
                expires_at=row.expires_at.isoformat(),
            )
        return inserted


RecordEnforcementRecommendationUseCase = RecordShadowRecommendationUseCase


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
            return ShadowCheckResult(degraded=True)

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
