"""One-process local worker supervision for the durable retraining queue."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ml_model.retraining.dashboard_contracts import RunState
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    RetrainingRunArtifactRepository,
)
from web_app.infrastructure.retraining_process_runner import (
    RetrainingProcessRunner,
    WorkerProcessHandle,
)

WORKER_MARKER_FILENAME = ".worker.process.json"
SUPERVISOR_GUARD_FILENAME = ".worker.supervisor.guard"


@dataclass(frozen=True, slots=True)
class WorkerSupervisorResult:
    started: bool
    pid: int | None
    reason: str


class RetrainingWorkerSupervisor:
    """Ensure at most one detached local worker is advertised for a root."""

    def __init__(
        self,
        repository: RetrainingRunArtifactRepository,
        *,
        root: Path | str,
        process_runner: RetrainingProcessRunner,
        clock: Callable[[], datetime] | None = None,
        process_checker: Callable[[int], bool] | None = None,
    ) -> None:
        self._repository = repository
        self._root = Path(root).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._runner = process_runner
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._process_checker = process_checker or self._is_process_alive

    @staticmethod
    def _is_process_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError, ProcessLookupError, PermissionError:
            return False
        return True

    @property
    def marker_path(self) -> Path:
        return self._root / WORKER_MARKER_FILENAME

    def _read_marker(self) -> dict[str, object] | None:
        if not self.marker_path.is_file():
            return None
        try:
            payload = json.loads(self.marker_path.read_text(encoding="utf-8"))
        except OSError, UnicodeError, json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _write_marker(self, handle: WorkerProcessHandle) -> None:
        temporary = self.marker_path.with_name(
            f".{self.marker_path.name}.{uuid.uuid4().hex}.tmp"
        )
        temporary.write_text(
            json.dumps(
                {
                    "pid": handle.pid,
                    "started_at": handle.started_at.astimezone(timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        os.replace(temporary, self.marker_path)

    def _has_runnable_run(self) -> bool:
        now = self._clock().astimezone(timezone.utc)
        return any(
            record.state is RunState.QUEUED
            or (
                record.state is RunState.RETRYABLE_FAILED
                and (record.next_retry_at is None or record.next_retry_at <= now)
            )
            for record in self._repository.list_runs()
        )

    def ensure_worker_available(self) -> WorkerSupervisorResult:
        marker = self._read_marker()
        if marker is not None:
            try:
                pid = int(marker["pid"])
            except KeyError, TypeError, ValueError:
                pid = -1
            if self._process_checker(pid):
                return WorkerSupervisorResult(False, pid, "already_running")
            self.marker_path.unlink(missing_ok=True)
        if not self._has_runnable_run():
            return WorkerSupervisorResult(False, None, "no_runnable_run")

        guard = self._root / SUPERVISOR_GUARD_FILENAME
        try:
            with guard.open("x", encoding="utf-8"):
                marker = self._read_marker()
                if marker is not None:
                    try:
                        pid = int(marker["pid"])
                    except KeyError, TypeError, ValueError:
                        pid = -1
                    if self._process_checker(pid):
                        return WorkerSupervisorResult(False, pid, "already_running")
                handle = self._runner.start_worker(self._root)
                self._write_marker(handle)
                return WorkerSupervisorResult(True, handle.pid, "started")
        except FileExistsError:
            return WorkerSupervisorResult(False, None, "another_supervisor_starting")
        finally:
            guard.unlink(missing_ok=True)

    @staticmethod
    def clear_worker_marker(root: Path | str, pid: int) -> None:
        marker_path = Path(root).expanduser().resolve() / WORKER_MARKER_FILENAME
        if not marker_path.is_file():
            return
        try:
            payload = json.loads(marker_path.read_text(encoding="utf-8"))
            if int(payload.get("pid", -1)) == int(pid):
                marker_path.unlink(missing_ok=True)
        except OSError, TypeError, ValueError, json.JSONDecodeError:
            return


__all__ = ["RetrainingWorkerSupervisor", "WorkerSupervisorResult"]
