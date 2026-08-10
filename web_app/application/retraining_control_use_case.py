"""Application services for the retraining control-plane boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from ml_model.retraining.dashboard_contracts import RunState
from ml_model.retraining.dashboard_export import DashboardExportResult
from web_app.application.retraining_export_use_case import RetrainingExportUseCase
from web_app.application.retraining_run_use_case import (
    RetrainingRunUseCase,
    RetrainingStartResult,
)
from web_app.domain.interfaces import ITrafficLabelReviewRepository
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    ArtifactRepositoryError,
    RetrainingRunArtifactRepository,
    RetrainingRunRecord,
)

RUNNING_STATES = frozenset(
    {
        RunState.EXPORTING,
        RunState.DATASET_VALIDATED,
        RunState.TRAINING,
        RunState.EVALUATING,
        RunState.DEPLOYING,
    }
)


class RetrainingControlError(ValueError):
    """Bounded application error mapped to a safe HTTP response."""

    def __init__(self, code: str, message: str, *, status_code: int = 409) -> None:
        self.code = code
        self.safe_message = message[:240].replace("\r", " ").replace("\n", " ")
        self.status_code = status_code
        super().__init__(self.safe_message)


@dataclass(frozen=True, slots=True)
class RetrainingSummarySnapshot:
    active_model_version: str
    latest_run_state: RunState | None
    approved_count: int
    unreviewed_count: int
    excluded_count: int
    latest_dataset_version: str | None
    run_in_progress: bool
    last_trigger_time: datetime | None


@dataclass(frozen=True, slots=True)
class RetrainingRunDetail:
    record: RetrainingRunRecord
    events: tuple[dict[str, Any], ...]
    evidence_status: str
    heartbeat_age_seconds: int | None
    retry_available: bool


@dataclass(frozen=True, slots=True)
class RetrainingDecisionResult:
    run: RetrainingRunRecord
    decision: str


class RetrainingControlUseCase:
    """Coordinate safe API operations without putting policy in route handlers."""

    def __init__(
        self,
        review_repository: ITrafficLabelReviewRepository,
        artifact_repository: RetrainingRunArtifactRepository,
        run_use_case: RetrainingRunUseCase,
        export_use_case: RetrainingExportUseCase,
        *,
        active_model_version: str = "NOT_AVAILABLE",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._review_repository = review_repository
        self._artifact_repository = artifact_repository
        self._run_use_case = run_use_case
        self._export_use_case = export_use_case
        self._active_model_version = active_model_version
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    async def get_summary(self) -> RetrainingSummarySnapshot:
        review_summary = await self._review_repository.get_retraining_review_summary()
        runs = self._artifact_repository.list_runs()
        latest = runs[-1] if runs else None
        latest_dataset_version = next(
            (
                record.dataset_version
                for record in reversed(runs)
                if record.dataset_version
            ),
            None,
        )
        return RetrainingSummarySnapshot(
            active_model_version=self._active_model_version,
            latest_run_state=latest.state if latest else None,
            approved_count=review_summary.approved,
            unreviewed_count=review_summary.unreviewed,
            excluded_count=review_summary.excluded,
            latest_dataset_version=latest_dataset_version,
            run_in_progress=any(record.state in RUNNING_STATES for record in runs),
            last_trigger_time=latest.created_at if latest else None,
        )

    async def start_run(self, **kwargs: Any) -> RetrainingStartResult:
        return await self._run_use_case.start_run(**kwargs)

    async def export_samples(self, *, export_id: str) -> DashboardExportResult:
        return await self._export_use_case.execute(run_id=export_id)

    def list_runs(self) -> list[RetrainingRunRecord]:
        return list(reversed(self._artifact_repository.list_runs()))

    def get_run_detail(self, run_id: str) -> RetrainingRunDetail:
        try:
            record = self._artifact_repository.load_run(run_id)
            events = tuple(self._artifact_repository.read_events(run_id))
        except (ArtifactRepositoryError, FileNotFoundError, ValueError) as exc:
            raise RetrainingControlError(
                "RUN_NOT_FOUND", "The retraining run was not found.", status_code=404
            ) from exc
        now = self._clock().astimezone(timezone.utc)
        heartbeat_age = None
        if record.heartbeat_at is not None:
            heartbeat_age = max(0, int((now - record.heartbeat_at).total_seconds()))
        evidence_status = (
            "NOT_ENOUGH_EVIDENCE"
            if record.state is RunState.NOT_ENOUGH_EVIDENCE
            else "NOT_RUN"
        )
        return RetrainingRunDetail(
            record=record,
            events=events,
            evidence_status=evidence_status,
            heartbeat_age_seconds=heartbeat_age,
            retry_available=(
                record.state is RunState.RETRYABLE_FAILED
                and record.retry_count < record.max_retries
            ),
        )

    def decide(
        self,
        *,
        run_id: str,
        decision: str,
        reason: str | None,
        actor_id: str,
        actor_role: str,
    ) -> RetrainingDecisionResult:
        if actor_role != "ADMIN":
            raise RetrainingControlError(
                "FORBIDDEN", "Administrator review is required.", status_code=403
            )
        if decision not in {"approve", "hold", "reject"}:
            raise RetrainingControlError("INVALID_DECISION", "Decision is invalid.")
        if not actor_id.strip() or len(actor_id) > 128:
            raise RetrainingControlError(
                "INVALID_ACTOR", "Reviewer identity is invalid."
            )
        if reason is not None and len(reason) > 500:
            raise RetrainingControlError(
                "INVALID_REASON", "Decision reason is too long."
            )
        if reason is not None and any(
            marker in reason
            for marker in (
                "model_input_text",
                "http_request",
                "API_SECRET_KEY",
                "INTERNAL_API_KEY",
            )
        ):
            raise RetrainingControlError(
                "INVALID_REASON", "Decision reason contains forbidden content."
            )
        if decision in {"hold", "reject"} and not (reason or "").strip():
            raise RetrainingControlError(
                "REASON_REQUIRED", "A reason is required for hold or reject."
            )

        try:
            current = self._artifact_repository.load_run(run_id)
        except (ArtifactRepositoryError, FileNotFoundError, ValueError) as exc:
            raise RetrainingControlError(
                "RUN_NOT_FOUND", "The retraining run was not found.", status_code=404
            ) from exc
        if current.state is not RunState.PENDING_APPROVAL:
            raise RetrainingControlError(
                "RUN_NOT_PENDING", "The run is not awaiting a reviewer decision."
            )
        if decision == "approve" and not (
            current.candidate_model_version
            and current.candidate_model_digest
            and current.evaluation_digest
        ):
            raise RetrainingControlError(
                "EVIDENCE_NOT_READY",
                "The candidate has no complete evaluation evidence.",
            )

        target = {
            "approve": RunState.APPROVED,
            "hold": RunState.HELD,
            "reject": RunState.REJECTED,
        }[decision]
        updated = self._artifact_repository.transition(
            run_id,
            target,
            stage=f"decision_{decision}",
        )
        self._artifact_repository.append_event(
            run_id,
            stage="decision",
            outcome="SUCCESS",
            code=f"CANDIDATE_{decision.upper()}",
            message=reason or "candidate decision recorded",
            actor_id=actor_id,
            actor_role=actor_role,
        )
        return RetrainingDecisionResult(run=updated, decision=decision)

    def deploy(self, *, run_id: str, expected_candidate_version: str) -> None:
        del run_id, expected_candidate_version
        raise RetrainingControlError(
            "DEPLOYMENT_NOT_AVAILABLE",
            "Local staging deployment is not available in this control-plane slice.",
            status_code=501,
        )

    def rollback(
        self, *, run_id: str, previous_staging_version: str, reason: str
    ) -> None:
        del run_id, previous_staging_version, reason
        raise RetrainingControlError(
            "ROLLBACK_NOT_AVAILABLE",
            "Local staging rollback is not available in this control-plane slice.",
            status_code=501,
        )


__all__ = [
    "RetrainingControlError",
    "RetrainingControlUseCase",
    "RetrainingDecisionResult",
    "RetrainingRunDetail",
    "RetrainingSummarySnapshot",
]
