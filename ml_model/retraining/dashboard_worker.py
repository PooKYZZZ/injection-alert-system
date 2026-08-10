"""Bounded local worker for the durable dashboard retraining queue."""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from ml_model.retraining.dashboard_contracts import RunState
from ml_model.retraining.dashboard_pipeline import (
    NativeDashboardPipeline,
    PipelineFailure,
    PipelineResult,
    SmokeDashboardPipeline,
)
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    ArtifactRepositoryError,
    RetrainingRunArtifactRepository,
    WorkerLockBusy,
)
from web_app.infrastructure.retraining_worker_supervisor import (
    RetrainingWorkerSupervisor,
)

EXIT_SUCCESS = 0
EXIT_NOOP = 10
EXIT_RETRYABLE_FAILURE = 20
EXIT_TERMINAL_FAILURE = 30


class DashboardPipeline(Protocol):
    def execute(
        self,
        run,
        repository: RetrainingRunArtifactRepository,
        heartbeat: Callable[[], None],
    ) -> PipelineResult: ...


@dataclass(frozen=True, slots=True)
class WorkerResult:
    exit_code: int
    run_id: str | None
    state: RunState | None


class DashboardWorker:
    """Claim at most one run and release the host lock on every outcome."""

    def __init__(
        self,
        repository: RetrainingRunArtifactRepository,
        *,
        root: Path | str,
        pipeline: DashboardPipeline | None = None,
        worker_id: str | None = None,
        smoke: bool = True,
        timeout_seconds: float = 3600,
        heartbeat_timeout_seconds: int = 300,
        lock_stale_after_seconds: int = 300,
        clock: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("worker timeout must be positive")
        self._repository = repository
        self._root = Path(root).expanduser().resolve()
        self._pipeline = pipeline or (
            SmokeDashboardPipeline() if smoke else NativeDashboardPipeline()
        )
        self._worker_id = worker_id or f"worker-{os.getpid()}"
        self._timeout_seconds = timeout_seconds
        self._heartbeat_timeout_seconds = heartbeat_timeout_seconds
        self._lock_stale_after_seconds = lock_stale_after_seconds
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._monotonic = monotonic or time.monotonic

    def _heartbeat(self, run_id: str) -> None:
        self._repository.heartbeat(
            run_id,
            worker_id=self._worker_id,
            now=self._clock().astimezone(timezone.utc),
        )

    def run_once(self, *, now: datetime | None = None) -> WorkerResult:
        current_time = (now or self._clock()).astimezone(timezone.utc)
        self._repository.recover_stale_runs(
            now=current_time,
            heartbeat_timeout_seconds=self._heartbeat_timeout_seconds,
        )
        try:
            lock = self._repository.acquire_worker_lock(
                worker_id=self._worker_id,
                now=current_time,
                stale_after_seconds=self._lock_stale_after_seconds,
            )
        except WorkerLockBusy:
            return WorkerResult(EXIT_NOOP, None, None)

        run = None
        try:
            run = self._repository.claim_next(
                worker_id=self._worker_id, now=current_time
            )
            if run is None:
                return WorkerResult(EXIT_NOOP, None, None)
            self._repository.append_event(
                run.run_id,
                stage="exporting",
                outcome="STARTED",
                code="WORKER_CLAIMED",
                message="worker claimed one queued run",
            )
            if run.approved_sample_count == 0:
                skipped = self._repository.transition(
                    run.run_id,
                    RunState.SKIPPED_NO_APPROVED_DATA,
                    worker_id=self._worker_id,
                    stage="preflight",
                )
                self._repository.append_event(
                    run.run_id,
                    stage="preflight",
                    outcome="SKIPPED",
                    code="NO_APPROVED_DATA",
                    message="worker found no approved data",
                )
                return WorkerResult(EXIT_SUCCESS, run.run_id, skipped.state)
            started = self._monotonic()
            try:
                result = self._pipeline.execute(
                    run,
                    self._repository,
                    lambda: self._heartbeat(run.run_id),
                )
                elapsed = self._monotonic() - started
                if elapsed > self._timeout_seconds:
                    raise PipelineFailure(
                        "WORKER_TIMEOUT",
                        retryable=True,
                        message="worker execution exceeded the configured timeout",
                    )
                current = self._repository.load_run(run.run_id)
                if current.state is not result.terminal_state:
                    raise PipelineFailure(
                        "PIPELINE_STATE_INCOMPLETE",
                        retryable=False,
                        message="pipeline did not publish its terminal state",
                    )
                self._repository.append_event(
                    run.run_id,
                    stage=current.stage,
                    outcome="SUCCESS",
                    code="RUN_TERMINAL",
                    message="run reached a published terminal state",
                    duration_ms=int(max(0.0, elapsed) * 1000),
                )
                return WorkerResult(EXIT_SUCCESS, run.run_id, current.state)
            except PipelineFailure as exc:
                failed = self._repository.fail_run(
                    run.run_id,
                    error_code=exc.code,
                    error_message=exc.safe_message,
                    retryable=exc.retryable,
                    worker_id=self._worker_id,
                    now=self._clock().astimezone(timezone.utc),
                )
                self._repository.append_event(
                    run.run_id,
                    stage="failed",
                    outcome="RETRYABLE"
                    if failed.state is RunState.RETRYABLE_FAILED
                    else "FAILED",
                    code=exc.code,
                    message=exc.safe_message,
                )
                return WorkerResult(
                    EXIT_RETRYABLE_FAILURE
                    if failed.state is RunState.RETRYABLE_FAILED
                    else EXIT_TERMINAL_FAILURE,
                    run.run_id,
                    failed.state,
                )
            except ArtifactRepositoryError as exc:
                failed = self._repository.fail_run(
                    run.run_id,
                    error_code="INVALID_RUN_ARTIFACT",
                    error_message=type(exc).__name__,
                    retryable=False,
                    worker_id=self._worker_id,
                    now=self._clock().astimezone(timezone.utc),
                )
                self._repository.append_event(
                    run.run_id,
                    stage="failed",
                    outcome="FAILED",
                    code="INVALID_RUN_ARTIFACT",
                    message=type(exc).__name__,
                )
                return WorkerResult(EXIT_TERMINAL_FAILURE, run.run_id, failed.state)
            except Exception as exc:
                failed = self._repository.fail_run(
                    run.run_id,
                    error_code="WORKER_EXCEPTION",
                    error_message=type(exc).__name__,
                    retryable=True,
                    worker_id=self._worker_id,
                    now=self._clock().astimezone(timezone.utc),
                )
                self._repository.append_event(
                    run.run_id,
                    stage="failed",
                    outcome="RETRYABLE"
                    if failed.state is RunState.RETRYABLE_FAILED
                    else "FAILED",
                    code="WORKER_EXCEPTION",
                    message=type(exc).__name__,
                )
                return WorkerResult(
                    EXIT_RETRYABLE_FAILURE
                    if failed.state is RunState.RETRYABLE_FAILED
                    else EXIT_TERMINAL_FAILURE,
                    run.run_id,
                    failed.state,
                )
        finally:
            lock.release()
            if run is not None:
                RetrainingWorkerSupervisor.clear_worker_marker(self._root, os.getpid())

    def run_until_idle(
        self,
        *,
        poll_seconds: float = 5.0,
        max_runtime_seconds: float = 60.0,
    ) -> WorkerResult:
        if not 0.0 < poll_seconds <= 60.0 or max_runtime_seconds <= 0:
            raise ValueError("worker polling limits are invalid")
        deadline = self._monotonic() + max_runtime_seconds
        last = WorkerResult(EXIT_NOOP, None, None)
        while self._monotonic() < deadline:
            last = self.run_once()
            if last.exit_code in {EXIT_RETRYABLE_FAILURE, EXIT_TERMINAL_FAILURE}:
                return last
            if last.exit_code == EXIT_SUCCESS:
                return last
            time.sleep(poll_seconds)
        return last


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--max-runtime-seconds", type=float, default=60.0)
    parser.add_argument("--timeout-seconds", type=float, default=3600.0)
    parser.add_argument("--worker-id", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    repository = RetrainingRunArtifactRepository(args.root)
    worker = DashboardWorker(
        repository,
        root=args.root,
        worker_id=args.worker_id,
        smoke=args.smoke,
        timeout_seconds=args.timeout_seconds,
    )
    result = (
        worker.run_once()
        if args.once
        else worker.run_until_idle(
            poll_seconds=args.poll_seconds,
            max_runtime_seconds=args.max_runtime_seconds,
        )
    )
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DashboardWorker",
    "EXIT_NOOP",
    "EXIT_RETRYABLE_FAILURE",
    "EXIT_SUCCESS",
    "EXIT_TERMINAL_FAILURE",
    "WorkerResult",
]
