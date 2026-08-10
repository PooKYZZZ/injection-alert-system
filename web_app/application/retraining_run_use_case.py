"""Application boundary for idempotent local retraining run requests."""

from __future__ import annotations

import hashlib
import inspect
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Protocol

from ml_model.retraining.dashboard_contracts import (
    RunState,
    build_run_id,
    canonical_json,
)
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    RetrainingRunArtifactRepository,
    RetrainingRunRecord,
)

_SCHEDULE_ACTIVE_STATES = frozenset(
    {
        RunState.QUEUED,
        RunState.EXPORTING,
        RunState.DATASET_VALIDATED,
        RunState.TRAINING,
        RunState.EVALUATING,
        RunState.PENDING_APPROVAL,
        RunState.APPROVED,
        RunState.DEPLOYING,
        RunState.RETRYABLE_FAILED,
    }
)


@dataclass(frozen=True, slots=True)
class RetrainingInputSnapshot:
    """Server-resolved inputs used to bind a run to one immutable snapshot."""

    source_review_revisions: tuple[str, ...]
    source_dataset_version: str
    source_dataset_digest: str
    pipeline_fingerprint: str
    active_model_version: str
    active_model_digest: str
    approved_sample_count: int

    def __post_init__(self) -> None:
        if (
            not self.source_dataset_version.strip()
            or not self.active_model_version.strip()
        ):
            raise ValueError("dataset and active model versions are required")
        for value, name in (
            (self.source_dataset_digest, "source_dataset_digest"),
            (self.pipeline_fingerprint, "pipeline_fingerprint"),
            (self.active_model_digest, "active_model_digest"),
        ):
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError(f"{name} must be a SHA-256 digest")
        if self.approved_sample_count < 0:
            raise ValueError("approved sample count cannot be negative")


class SnapshotProvider(Protocol):
    def __call__(
        self,
    ) -> RetrainingInputSnapshot | Awaitable[RetrainingInputSnapshot]: ...


class WorkerSupervisor(Protocol):
    def ensure_worker_available(self) -> Any: ...


@dataclass(frozen=True, slots=True)
class RetrainingStartResult:
    run: RetrainingRunRecord
    created: bool


class RetrainingRunUseCase:
    """Resolve server-side inputs, enqueue once, and hand off to a worker."""

    def __init__(
        self,
        repository: RetrainingRunArtifactRepository,
        *,
        snapshot_provider: SnapshotProvider,
        worker_supervisor: WorkerSupervisor,
        clock: Callable[[], datetime] | None = None,
        max_retries: int = 2,
    ) -> None:
        if max_retries < 0 or max_retries > 5:
            raise ValueError("max_retries must be between 0 and 5")
        self._repository = repository
        self._snapshot_provider = snapshot_provider
        self._worker_supervisor = worker_supervisor
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._max_retries = max_retries

    async def _resolve_snapshot(self) -> RetrainingInputSnapshot:
        result = self._snapshot_provider()
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, RetrainingInputSnapshot):
            raise ValueError(
                "snapshot provider returned an invalid retraining snapshot"
            )
        return result

    @staticmethod
    def _validate_request(
        *,
        trigger: str,
        requested_by: str,
        requested_timezone: str,
        operator_note: str | None,
    ) -> None:
        if trigger not in {"manual", "scheduled"}:
            raise ValueError("trigger must be manual or scheduled")
        if not requested_by.strip() or len(requested_by) > 128:
            raise ValueError("requested_by is invalid")
        if any(ord(char) < 32 for char in requested_by):
            raise ValueError("requested_by is invalid")
        if not requested_timezone.strip() or len(requested_timezone) > 64:
            raise ValueError("requested timezone is invalid")
        if operator_note is not None:
            if len(operator_note) > 500 or any(
                ord(char) < 32 for char in operator_note
            ):
                raise ValueError("operator note is invalid")
            if any(
                marker in operator_note
                for marker in (
                    "model_input_text",
                    "http_request",
                    "API_SECRET_KEY",
                    "INTERNAL_API_KEY",
                )
            ):
                raise ValueError("operator note contains forbidden content")

    @staticmethod
    def _input_fingerprint(snapshot: RetrainingInputSnapshot) -> str:
        payload = {
            "source_review_revisions": sorted(snapshot.source_review_revisions),
            "source_dataset_digest": snapshot.source_dataset_digest,
            "pipeline_fingerprint": snapshot.pipeline_fingerprint,
            "active_model_digest": snapshot.active_model_digest,
        }
        return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()

    async def start_run(
        self,
        *,
        trigger: str,
        requested_by: str,
        requested_timezone: str,
        operator_note: str | None = None,
        scheduled_at: datetime | None = None,
    ) -> RetrainingStartResult:
        self._validate_request(
            trigger=trigger,
            requested_by=requested_by,
            requested_timezone=requested_timezone,
            operator_note=operator_note,
        )
        if scheduled_at is not None and scheduled_at.tzinfo is None:
            raise ValueError("scheduled_at must be timezone-aware")
        snapshot = await self._resolve_snapshot()
        fingerprint = self._input_fingerprint(snapshot)
        existing = self._repository.find_by_input_fingerprint(fingerprint)
        if existing is not None:
            if existing.state in {RunState.QUEUED, RunState.RETRYABLE_FAILED}:
                self._ensure_worker_safely(existing.run_id)
            if trigger == "scheduled":
                self._repository.append_event(
                    existing.run_id,
                    stage="schedule",
                    outcome="SKIPPED",
                    code="SCHEDULE_IDEMPOTENT_RUN",
                    message="scheduled request matched an existing retraining snapshot",
                    actor_id=requested_by,
                    actor_role="SCHEDULER",
                    scheduled_at=scheduled_at,
                    exit_code=0,
                )
            return RetrainingStartResult(run=existing, created=False)

        if trigger == "scheduled" and snapshot.approved_sample_count > 0:
            active_run = next(
                (
                    record
                    for record in self._repository.list_runs()
                    if record.state in _SCHEDULE_ACTIVE_STATES
                ),
                None,
            )
            if active_run is not None:
                self._repository.append_event(
                    active_run.run_id,
                    stage="schedule",
                    outcome="SKIPPED",
                    code="SCHEDULE_SKIPPED_CONCURRENT_RUN",
                    message=(
                        "scheduled request skipped because a retraining run is active"
                    ),
                    actor_id=requested_by,
                    actor_role="SCHEDULER",
                    scheduled_at=scheduled_at,
                    exit_code=0,
                )
                return RetrainingStartResult(run=active_run, created=False)

        now = self._clock().astimezone(timezone.utc)
        initial_state = (
            RunState.SKIPPED_NO_APPROVED_DATA
            if snapshot.approved_sample_count == 0
            else RunState.QUEUED
        )
        record = RetrainingRunRecord(
            run_id=build_run_id(now, entropy=fingerprint),
            state=initial_state,
            stage="preflight" if initial_state is not RunState.QUEUED else "queued",
            attempt=0,
            retry_count=0,
            max_retries=self._max_retries,
            created_at=now,
            updated_at=now,
            heartbeat_at=None,
            trigger=trigger,
            requested_by=requested_by,
            requested_timezone=requested_timezone,
            input_fingerprint=fingerprint,
            source_review_revisions=tuple(sorted(snapshot.source_review_revisions)),
            source_dataset_version=snapshot.source_dataset_version,
            source_dataset_digest=snapshot.source_dataset_digest,
            pipeline_fingerprint=snapshot.pipeline_fingerprint,
            active_model_version=snapshot.active_model_version,
            active_model_digest=snapshot.active_model_digest,
            approved_sample_count=snapshot.approved_sample_count,
            operator_note=operator_note,
        )
        created = self._repository.create_or_get_run(record)
        if created.run_id != record.run_id:
            return RetrainingStartResult(run=created, created=False)
        if initial_state is RunState.SKIPPED_NO_APPROVED_DATA:
            self._repository.append_event(
                created.run_id,
                stage="preflight",
                outcome="SKIPPED",
                code="NO_APPROVED_DATA",
                message="no approved data was eligible for this snapshot",
                scheduled_at=scheduled_at,
                exit_code=0,
            )
        else:
            self._repository.append_event(
                created.run_id,
                stage="queued",
                outcome="INFO",
                code="RUN_QUEUED",
                message="run accepted by the local queue",
                scheduled_at=scheduled_at,
                exit_code=0,
            )
            self._ensure_worker_safely(created.run_id)
        return RetrainingStartResult(run=created, created=True)

    def _ensure_worker_safely(self, run_id: str) -> None:
        try:
            self._worker_supervisor.ensure_worker_available()
        except Exception as exc:
            self._repository.append_event(
                run_id,
                stage="queued",
                outcome="WARN",
                code="WORKER_START_FAILED",
                message=f"worker supervisor unavailable: {type(exc).__name__}",
            )

    def get_run(self, run_id: str) -> RetrainingRunRecord:
        return self._repository.load_run(run_id)

    def retry_run(self, run_id: str) -> RetrainingRunRecord:
        current = self._repository.load_run(run_id)
        if current.state is not RunState.RETRYABLE_FAILED:
            raise ValueError("only retryable failed runs can be retried")
        queued = self._repository.transition(run_id, RunState.QUEUED)
        self._ensure_worker_safely(run_id)
        return queued


__all__ = [
    "RetrainingInputSnapshot",
    "RetrainingRunUseCase",
    "RetrainingStartResult",
]
