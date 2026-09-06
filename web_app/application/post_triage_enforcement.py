"""Post-triage recommendation ownership for controlled PR7 enforcement."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Protocol

from web_app.application.enforcement_use_cases import (
    RecordShadowRecommendationUseCase,
)
from web_app.domain.classification_scope import is_actionable_attack_class
from web_app.domain.enforcement import EnforcementMode
from web_app.domain.waf_state import PR7_DEFAULT_CAPACITY, PR7_PATH


@dataclass(frozen=True, slots=True)
class WafMutationOutcome:
    """Small application-facing view of a Block 1 mutation result."""

    category: str
    recommendation_id: int
    revision: int
    state_changed: bool


class IWafStateMutationRepository(Protocol):
    async def record_critical_waf_recommendation(
        self,
        *,
        trigger_traffic_log_id: int,
        recommendation_expires_at: datetime,
        effective_expires_at: datetime,
        capacity: int,
    ) -> WafMutationOutcome:
        """Atomically create PR7 provenance and effective state."""


@dataclass(frozen=True, slots=True)
class PostTriageEnforcementResult:
    route: Literal["NONE", "GENERIC", "PR7"]
    recorded: bool
    category: str
    recommendation_id: int | None = None
    revision: int | None = None
    state_changed: bool = False


class PostTriageEnforcementCoordinator:
    """Select exactly one recommendation writer after alert persistence."""

    def __init__(
        self,
        *,
        generic_use_case: RecordShadowRecommendationUseCase,
        waf_repository: IWafStateMutationRepository,
        enforcement_mode: EnforcementMode | str,
        pr7_mutation_enabled: bool,
        recommendation_ttl_seconds: int,
        pr7_capacity: int = PR7_DEFAULT_CAPACITY,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._generic = generic_use_case
        self._waf_repository = waf_repository
        self._mode = EnforcementMode(enforcement_mode)
        self._pr7_mutation_enabled = pr7_mutation_enabled
        self._ttl_seconds = recommendation_ttl_seconds
        self._capacity = pr7_capacity
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    async def execute(
        self,
        *,
        alert_id: int | None,
        prediction: str,
        confidence_level: str,
        request_path: str,
        occurred_at: datetime | None,
    ) -> PostTriageEnforcementResult:
        if alert_id is None or not is_actionable_attack_class(prediction):
            return PostTriageEnforcementResult(
                route="NONE",
                recorded=False,
                category="NOT_APPLICABLE",
            )

        is_pr7_candidate = (
            self._pr7_mutation_enabled
            and self._mode is EnforcementMode.ENFORCE
            and confidence_level == "CRITICAL"
            and request_path == PR7_PATH
        )
        if not is_pr7_candidate:
            inserted = await self._generic.execute(
                alert_id=alert_id,
                prediction=prediction,
                confidence_level=confidence_level,
                request_path=request_path,
                occurred_at=occurred_at,
            )
            return PostTriageEnforcementResult(
                route="GENERIC",
                recorded=inserted,
                category="RECORDED" if inserted else "NO_CHANGE",
            )

        now = self._clock()
        event_time = occurred_at or now
        if event_time.tzinfo is None or event_time.utcoffset() is None:
            # SQLite-backed tests and some legacy DateTime adapters return
            # persisted UTC values without timezone metadata. The ingest
            # contract supplies UTC timestamps, so restore that metadata at
            # the application boundary before calculating expiry.
            event_time = event_time.replace(tzinfo=timezone.utc)
        else:
            event_time = event_time.astimezone(timezone.utc)
        expires_at = event_time + timedelta(seconds=self._ttl_seconds)

        mutation = await self._waf_repository.record_critical_waf_recommendation(
            trigger_traffic_log_id=alert_id,
            recommendation_expires_at=expires_at,
            effective_expires_at=expires_at,
            capacity=self._capacity,
        )
        return PostTriageEnforcementResult(
            route="PR7",
            recorded=mutation.recommendation_id > 0,
            category=mutation.category,
            recommendation_id=(
                mutation.recommendation_id
                if mutation.recommendation_id > 0
                else None
            ),
            revision=mutation.revision,
            state_changed=mutation.state_changed,
        )
