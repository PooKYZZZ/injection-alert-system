"""Atomic local queue and immutable run-artifact persistence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from ml_model.retraining.dashboard_contracts import (
    RunState,
    canonical_json,
    get_run_artifact_directory,
)

QUEUE_FILENAME = "queue.json"
RUN_FILENAME = "run.json"
EVENTS_FILENAME = "events.jsonl"
ARTIFACT_MANIFEST_FILENAME = "artifact_manifest.json"
WORKER_LOCK_FILENAME = ".worker.lock.json"
MAX_EVENT_COUNT = 256
MAX_ARTIFACT_BYTES = 25 * 1024 * 1024
SAFE_CODE = re.compile(r"^[A-Z0-9_]{1,64}$")
RUN_RESERVATION_WAIT_SECONDS = 5.0
RUN_RESERVATION_OWNER_FILENAME = "owner.json"
RUN_RESERVATION_STALE_SECONDS = 30.0

_RUN_TRANSITIONS: dict[RunState, frozenset[RunState]] = {
    RunState.QUEUED: frozenset(
        {
            RunState.EXPORTING,
            RunState.SKIPPED_NO_APPROVED_DATA,
            RunState.QUARANTINED_FOR_REVIEW,
            RunState.RETRYABLE_FAILED,
            RunState.FAILED,
        }
    ),
    RunState.EXPORTING: frozenset(
        {
            RunState.DATASET_VALIDATED,
            RunState.SKIPPED_NO_APPROVED_DATA,
            RunState.QUARANTINED_FOR_REVIEW,
            RunState.RETRYABLE_FAILED,
            RunState.FAILED,
        }
    ),
    RunState.DATASET_VALIDATED: frozenset(
        {RunState.TRAINING, RunState.RETRYABLE_FAILED, RunState.FAILED}
    ),
    RunState.TRAINING: frozenset(
        {RunState.EVALUATING, RunState.RETRYABLE_FAILED, RunState.FAILED}
    ),
    RunState.EVALUATING: frozenset(
        {
            RunState.PENDING_APPROVAL,
            RunState.NOT_ENOUGH_EVIDENCE,
            RunState.QUARANTINED_FOR_REVIEW,
            RunState.RETRYABLE_FAILED,
            RunState.FAILED,
        }
    ),
    RunState.PENDING_APPROVAL: frozenset(
        {
            RunState.APPROVED,
            RunState.HELD,
            RunState.REJECTED,
            RunState.NOT_ENOUGH_EVIDENCE,
            RunState.FAILED,
        }
    ),
    RunState.APPROVED: frozenset(
        {RunState.DEPLOYING, RunState.FAILED, RunState.RECOVERY_REQUIRED}
    ),
    RunState.DEPLOYING: frozenset(
        {
            RunState.APPROVED,
            RunState.DEPLOYED,
            RunState.ROLLED_BACK,
            RunState.FAILED,
            RunState.RECOVERY_REQUIRED,
        }
    ),
    RunState.RETRYABLE_FAILED: frozenset({RunState.QUEUED, RunState.FAILED}),
    RunState.NOT_ENOUGH_EVIDENCE: frozenset(),
    RunState.QUARANTINED_FOR_REVIEW: frozenset(),
    RunState.HELD: frozenset(),
    RunState.REJECTED: frozenset(),
    RunState.DEPLOYED: frozenset(
        {RunState.DEPLOYING, RunState.ROLLED_BACK, RunState.RECOVERY_REQUIRED}
    ),
    RunState.ROLLED_BACK: frozenset(),
    RunState.RECOVERY_REQUIRED: frozenset(
        {
            RunState.APPROVED,
            RunState.DEPLOYING,
            RunState.DEPLOYED,
            RunState.ROLLED_BACK,
            RunState.FAILED,
            RunState.RECOVERY_REQUIRED,
        }
    ),
    RunState.SKIPPED_NO_APPROVED_DATA: frozenset(),
    RunState.FAILED: frozenset(),
}
_HEARTBEAT_STATES = frozenset(
    {
        RunState.EXPORTING,
        RunState.DATASET_VALIDATED,
        RunState.TRAINING,
        RunState.EVALUATING,
        RunState.DEPLOYING,
    }
)


class ArtifactRepositoryError(RuntimeError):
    """Base error for unsafe or inconsistent local run artifacts."""


class ArtifactIntegrityError(ArtifactRepositoryError):
    """A required artifact is missing, tampered with, or too large."""


class InvalidRunTransition(ArtifactRepositoryError):
    """A requested state transition is not in the run state machine."""


class WorkerLockBusy(ArtifactRepositoryError):
    """Another local worker owns the single-run lock."""


@dataclass(frozen=True, slots=True)
class RetrainingRunRecord:
    run_id: str
    state: RunState
    stage: str
    attempt: int
    retry_count: int
    max_retries: int
    created_at: datetime
    updated_at: datetime
    heartbeat_at: datetime | None
    trigger: str
    requested_by: str
    requested_timezone: str
    input_fingerprint: str
    source_review_revisions: tuple[str, ...]
    source_dataset_version: str
    source_dataset_digest: str
    pipeline_fingerprint: str
    active_model_version: str
    active_model_digest: str
    approved_sample_count: int
    operator_note: str | None = None
    worker_id: str | None = None
    next_retry_at: datetime | None = None
    dataset_version: str | None = None
    dataset_digest: str | None = None
    candidate_model_version: str | None = None
    candidate_model_digest: str | None = None
    evaluation_digest: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    generation: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "generation": self.generation,
            "run_id": self.run_id,
            "state": self.state.value,
            "stage": self.stage,
            "attempt": self.attempt,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
            "heartbeat_at": _iso(self.heartbeat_at) if self.heartbeat_at else None,
            "trigger": self.trigger,
            "requested_by": self.requested_by,
            "requested_timezone": self.requested_timezone,
            "input_fingerprint": self.input_fingerprint,
            "source_review_revisions": list(self.source_review_revisions),
            "source_dataset_version": self.source_dataset_version,
            "source_dataset_digest": self.source_dataset_digest,
            "pipeline_fingerprint": self.pipeline_fingerprint,
            "active_model_version": self.active_model_version,
            "active_model_digest": self.active_model_digest,
            "approved_sample_count": self.approved_sample_count,
            "operator_note": self.operator_note,
            "worker_id": self.worker_id,
            "next_retry_at": _iso(self.next_retry_at) if self.next_retry_at else None,
            "dataset_version": self.dataset_version,
            "dataset_digest": self.dataset_digest,
            "candidate_model_version": self.candidate_model_version,
            "candidate_model_digest": self.candidate_model_digest,
            "evaluation_digest": self.evaluation_digest,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RetrainingRunRecord":
        if not isinstance(payload, Mapping):
            raise ArtifactRepositoryError("run manifest must be an object")
        try:
            run_id = str(payload["run_id"])
            state = RunState.parse(str(payload["state"]))
            revisions = tuple(str(item) for item in payload["source_review_revisions"])
            record = cls(
                run_id=run_id,
                state=state,
                stage=str(payload["stage"]),
                attempt=int(payload["attempt"]),
                retry_count=int(payload["retry_count"]),
                max_retries=int(payload["max_retries"]),
                created_at=_parse_time(payload["created_at"]),
                updated_at=_parse_time(payload["updated_at"]),
                heartbeat_at=_optional_time(payload.get("heartbeat_at")),
                trigger=str(payload["trigger"]),
                requested_by=str(payload["requested_by"]),
                requested_timezone=str(payload["requested_timezone"]),
                input_fingerprint=str(payload["input_fingerprint"]),
                source_review_revisions=revisions,
                source_dataset_version=str(payload["source_dataset_version"]),
                source_dataset_digest=str(payload["source_dataset_digest"]),
                pipeline_fingerprint=str(payload["pipeline_fingerprint"]),
                active_model_version=str(payload["active_model_version"]),
                active_model_digest=str(payload["active_model_digest"]),
                approved_sample_count=int(payload["approved_sample_count"]),
                operator_note=_optional_text(payload.get("operator_note")),
                worker_id=_optional_text(payload.get("worker_id")),
                next_retry_at=_optional_time(payload.get("next_retry_at")),
                dataset_version=_optional_text(payload.get("dataset_version")),
                dataset_digest=_optional_text(payload.get("dataset_digest")),
                candidate_model_version=_optional_text(
                    payload.get("candidate_model_version")
                ),
                candidate_model_digest=_optional_text(
                    payload.get("candidate_model_digest")
                ),
                evaluation_digest=_optional_text(payload.get("evaluation_digest")),
                error_code=_optional_text(payload.get("error_code")),
                error_message=_optional_text(payload.get("error_message")),
                generation=int(payload.get("generation", 1)),
            )
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ArtifactRepositoryError("run manifest is malformed") from exc
        _validate_record(record)
        return record


@dataclass
class LocalWorkerLock:
    _repository: "RetrainingRunArtifactRepository"
    worker_id: str
    owner_token: str
    _released: bool = False

    def heartbeat(self, now: datetime) -> None:
        if self._released:
            raise WorkerLockBusy("worker lock is already released")
        self._repository._update_lock(self.worker_id, self.owner_token, now)

    def release(self) -> None:
        if self._released:
            return
        self._repository._release_lock(self.worker_id, self.owner_token)
        self._released = True


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _optional_time(value: Any) -> datetime | None:
    return None if value in (None, "") else _parse_time(value)


def _optional_text(value: Any) -> str | None:
    return None if value in (None, "") else str(value)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _safe_message(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    if any(
        marker in text
        for marker in (
            "model_input_text",
            "http_request",
            "API_SECRET_KEY",
            "INTERNAL_API_KEY",
        )
    ):
        raise ArtifactRepositoryError("run event contains forbidden payload fields")
    return text[:500]


def _validate_digest(value: str, field_name: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ArtifactRepositoryError(f"{field_name} must be a SHA-256 digest")


def _reservation_owner_is_live(pid: object) -> bool:
    """Check a reservation owner conservatively when process state is unknown."""

    try:
        process_id = int(pid)
    except (TypeError, ValueError):
        return False
    if process_id <= 0:
        return False

    if os.name == "nt":
        # Windows does not provide the POSIX signal-0 probe. Querying the
        # process exit code avoids sending a termination signal to the owner.
        import ctypes
        from ctypes import wintypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.DWORD,
        )
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetExitCodeProcess.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        )
        kernel32.GetExitCodeProcess.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(
            process_query_limited_information, False, process_id
        )
        if not handle:
            # A protected process can reject the query even while it is live;
            # only known invalid/not-found errors prove that the owner exited.
            return ctypes.get_last_error() not in {6, 87, 1168}
        exit_code = wintypes.DWORD()
        try:
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return True
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(process_id, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # Unknown inspection failures must not be treated as proof that the
        # owner exited; preserving the reservation is safer than reclaiming a
        # potentially live creator.
        return True
    return True


def _validate_record(record: RetrainingRunRecord) -> None:
    if not re.fullmatch(r"retrain-\d{8}T\d{6}Z-[0-9a-f]{12}", record.run_id):
        raise ArtifactRepositoryError("run id is invalid")
    if not record.stage.strip() or record.trigger not in {"manual", "scheduled"}:
        raise ArtifactRepositoryError("run metadata is invalid")
    if not record.requested_by.strip() or len(record.requested_by) > 128:
        raise ArtifactRepositoryError("requested_by is invalid")
    if any(ord(char) < 32 for char in record.requested_by):
        raise ArtifactRepositoryError("requested_by is invalid")
    if not record.requested_timezone.strip() or len(record.requested_timezone) > 64:
        raise ArtifactRepositoryError("requested timezone is invalid")
    for value, name in (
        (record.input_fingerprint, "input_fingerprint"),
        (record.source_dataset_digest, "source_dataset_digest"),
        (record.pipeline_fingerprint, "pipeline_fingerprint"),
        (record.active_model_digest, "active_model_digest"),
    ):
        _validate_digest(value, name)
    if record.approved_sample_count < 0 or record.retry_count < 0:
        raise ArtifactRepositoryError("run counts cannot be negative")
    if record.max_retries < 0 or record.attempt < 0:
        raise ArtifactRepositoryError("run retry settings are invalid")
    if record.operator_note is not None and len(record.operator_note) > 500:
        raise ArtifactRepositoryError("operator note is too long")
    if record.dataset_version is not None and not record.dataset_version.strip():
        raise ArtifactRepositoryError("dataset version is invalid")
    for value, name in (
        (record.dataset_digest, "dataset_digest"),
        (record.candidate_model_digest, "candidate_model_digest"),
        (record.evaluation_digest, "evaluation_digest"),
    ):
        if value is not None:
            _validate_digest(value, name)
    if record.candidate_model_version is not None and not (
        record.candidate_model_version.strip()
    ):
        raise ArtifactRepositoryError("candidate model version is invalid")
    if record.state in {
        RunState.PENDING_APPROVAL,
        RunState.APPROVED,
        RunState.DEPLOYING,
        RunState.DEPLOYED,
        RunState.ROLLED_BACK,
        RunState.RECOVERY_REQUIRED,
    } and (
        not record.dataset_version
        or not record.dataset_digest
        or not record.candidate_model_version
        or not record.candidate_model_digest
        or not record.evaluation_digest
    ):
        raise ArtifactRepositoryError(
            "reviewed run state requires dataset, candidate, and evaluation bindings"
        )


class RetrainingRunArtifactRepository:
    """Store queue state and stage metadata under one configured local root."""

    def __init__(
        self,
        root: Path | str,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("repository clock must return an aware datetime")
        return value.astimezone(timezone.utc)

    def _run_dir(self, run_id: str) -> Path:
        return get_run_artifact_directory(self.root, run_id)

    def _atomic_write(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()

    def _atomic_json(self, path: Path, payload: Mapping[str, Any]) -> None:
        self._atomic_write(
            path,
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ArtifactRepositoryError(
                f"artifact manifest could not be read: {path.name}"
            ) from exc
        if not isinstance(payload, dict):
            raise ArtifactRepositoryError("artifact manifest must be an object")
        return payload

    def _save_run(self, record: RetrainingRunRecord) -> RetrainingRunRecord:
        _validate_record(record)
        self._atomic_json(self._run_dir(record.run_id) / RUN_FILENAME, record.to_dict())
        self._update_queue()
        return record

    def _reservation_is_stale(self, reservation: Path) -> bool:
        owner_path = reservation / RUN_RESERVATION_OWNER_FILENAME
        if owner_path.exists():
            try:
                owner = self._read_json(owner_path)
            except ArtifactRepositoryError:
                # Do not remove an active reservation whose metadata is present
                # but unreadable; an operator can inspect the corrupt marker.
                return False
            try:
                owner_created_at = float(owner["created_at"])
                owner_pid = owner["pid"]
            except (KeyError, TypeError, ValueError):
                return False
            if time.time() - owner_created_at < RUN_RESERVATION_STALE_SECONDS:
                return False
            return not _reservation_owner_is_live(owner_pid)

        try:
            reservation_age = time.time() - reservation.stat().st_mtime
        except OSError:
            return False
        # A process can terminate after mkdir and before owner metadata is
        # published. An old empty reservation is therefore recoverable.
        return reservation_age >= RUN_RESERVATION_STALE_SECONDS

    def _recover_stale_reservation(self, reservation: Path) -> bool:
        if not self._reservation_is_stale(reservation):
            return False
        quarantine = reservation.with_name(
            f".{reservation.name}.stale.{uuid.uuid4().hex}"
        )
        try:
            reservation.rename(quarantine)
        except FileNotFoundError:
            return False
        except OSError:
            return False
        try:
            shutil.rmtree(quarantine)
        except OSError:
            # The reservation no longer blocks its fingerprint. Keep the
            # quarantined marker for manual inspection if cleanup is denied.
            return True
        return True

    def _release_reservation(self, reservation: Path) -> None:
        """Remove our marker after concurrent readers release it on Windows."""

        deadline = time.monotonic() + RUN_RESERVATION_WAIT_SECONDS
        owner_path = reservation / RUN_RESERVATION_OWNER_FILENAME
        while True:
            try:
                owner_path.unlink(missing_ok=True)
                reservation.rmdir()
                return
            except FileNotFoundError:
                return
            except PermissionError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.01)

    def _update_queue(self) -> None:
        queue_path = self.root / QUEUE_FILENAME
        generation = 0
        if queue_path.is_file():
            try:
                generation = int(self._read_json(queue_path).get("generation", 0))
            except ArtifactRepositoryError, TypeError, ValueError:
                generation = 0
        summaries = []
        for record in self.list_runs():
            summaries.append(
                {
                    "run_id": record.run_id,
                    "state": record.state.value,
                    "stage": record.stage,
                    "attempt": record.attempt,
                    "updated_at": _iso(record.updated_at),
                    "input_fingerprint": record.input_fingerprint,
                }
            )
        self._atomic_json(
            queue_path,
            {
                "generation": generation + 1,
                "queue_version": "retraining-queue.v1",
                "updated_at": _iso(self._now()),
                "runs": summaries,
            },
        )

    def list_runs(self) -> list[RetrainingRunRecord]:
        records: list[RetrainingRunRecord] = []
        if not self.root.is_dir():
            return records
        for child in sorted(self.root.iterdir(), key=lambda path: path.name):
            if not child.is_dir() or child.name.startswith("."):
                continue
            run_path = child / RUN_FILENAME
            if run_path.is_file():
                records.append(RetrainingRunRecord.from_dict(self._read_json(run_path)))
        return sorted(records, key=lambda record: (record.created_at, record.run_id))

    def find_by_input_fingerprint(self, fingerprint: str) -> RetrainingRunRecord | None:
        _validate_digest(fingerprint, "input_fingerprint")
        return next(
            (
                record
                for record in self.list_runs()
                if record.input_fingerprint == fingerprint
            ),
            None,
        )

    def create_or_get_run(self, record: RetrainingRunRecord) -> RetrainingRunRecord:
        _validate_record(record)
        existing = self.find_by_input_fingerprint(record.input_fingerprint)
        if existing is not None:
            return existing
        reservation = self.root / (
            f".run-fingerprint.{record.input_fingerprint}.reservation"
        )
        owns_reservation = False
        run_dir: Path | None = None
        try:
            while True:
                try:
                    reservation.mkdir(exist_ok=False)
                    owns_reservation = True
                    self._atomic_json(
                        reservation / RUN_RESERVATION_OWNER_FILENAME,
                        {
                            "pid": os.getpid(),
                            "created_at": time.time(),
                        },
                    )
                    break
                except FileExistsError:
                    deadline = time.monotonic() + RUN_RESERVATION_WAIT_SECONDS
                    recovered = False
                    while time.monotonic() < deadline:
                        existing = self.find_by_input_fingerprint(
                            record.input_fingerprint
                        )
                        if existing is not None:
                            return existing
                        if self._recover_stale_reservation(reservation):
                            recovered = True
                            break
                        time.sleep(0.01)
                    if recovered:
                        continue
                    raise ArtifactRepositoryError(
                        "another run with the same input fingerprint is being created"
                    )
            existing = self.find_by_input_fingerprint(record.input_fingerprint)
            if existing is not None:
                return existing
            run_dir = self._run_dir(record.run_id)
            try:
                run_dir.mkdir(parents=True, exist_ok=False)
            except FileExistsError as exc:
                if (run_dir / RUN_FILENAME).is_file():
                    return self.load_run(record.run_id)
                raise ArtifactRepositoryError(
                    "run directory exists without a run manifest"
                ) from exc
            self._atomic_json(
                run_dir / ARTIFACT_MANIFEST_FILENAME,
                {
                    "manifest_version": "retraining-artifacts.v1",
                    "generation": 1,
                    "artifacts": {},
                },
            )
            self._atomic_write(run_dir / EVENTS_FILENAME, b"")
            # run.json is the publication marker: readers only see a complete
            # run after its supporting manifest and event stream exist.
            self._atomic_json(run_dir / RUN_FILENAME, record.to_dict())
            self._update_queue()
            return record
        except BaseException:
            if run_dir is not None and run_dir.exists() and not (
                run_dir / RUN_FILENAME
            ).is_file():
                shutil.rmtree(run_dir, ignore_errors=True)
            raise
        finally:
            if owns_reservation:
                self._release_reservation(reservation)

    def load_run(self, run_id: str) -> RetrainingRunRecord:
        path = self._run_dir(run_id) / RUN_FILENAME
        if not path.is_file():
            raise FileNotFoundError(f"run does not exist: {run_id}")
        return RetrainingRunRecord.from_dict(self._read_json(path))

    def _assert_worker(
        self, record: RetrainingRunRecord, worker_id: str | None
    ) -> None:
        if worker_id is not None and record.worker_id != worker_id:
            raise ArtifactRepositoryError("run ownership does not match worker")

    def transition(
        self,
        run_id: str,
        next_state: RunState,
        *,
        worker_id: str | None = None,
        stage: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> RetrainingRunRecord:
        current = self.load_run(run_id)
        self._assert_worker(current, worker_id)
        target = RunState.parse(next_state)
        if target != current.state and target not in _RUN_TRANSITIONS[current.state]:
            raise InvalidRunTransition(
                f"cannot transition {current.state.value} to {target.value}"
            )
        now = self._now()
        updated = replace(
            current,
            state=target,
            stage=stage or target.value,
            updated_at=now,
            heartbeat_at=(now if target in _HEARTBEAT_STATES else current.heartbeat_at),
            worker_id=current.worker_id if target in _HEARTBEAT_STATES else None,
            error_code=error_code,
            error_message=_safe_message(error_message),
            generation=current.generation + 1,
        )
        return self._save_run(updated)

    def claim_next(
        self, *, worker_id: str, now: datetime | None = None
    ) -> RetrainingRunRecord | None:
        current_time = (now or self._now()).astimezone(timezone.utc)
        for record in self.list_runs():
            if record.state is RunState.RETRYABLE_FAILED:
                if record.next_retry_at and record.next_retry_at > current_time:
                    continue
                record = self.transition(record.run_id, RunState.QUEUED)
            if record.state is RunState.QUEUED:
                self.cleanup_partial_artifacts(record.run_id)
                claimed = replace(
                    record,
                    state=RunState.EXPORTING,
                    stage="exporting",
                    attempt=record.attempt + 1,
                    updated_at=current_time,
                    heartbeat_at=current_time,
                    worker_id=worker_id,
                    next_retry_at=None,
                    generation=record.generation + 1,
                )
                return self._save_run(claimed)
        return None

    def cleanup_partial_artifacts(self, run_id: str) -> int:
        """Remove only abandoned atomic-write temporary files for one run."""

        run_dir = self._run_dir(run_id)
        if not run_dir.is_dir():
            return 0
        removed = 0
        for path in run_dir.rglob(".*.tmp"):
            if path.is_file():
                path.unlink()
                removed += 1
        return removed

    def heartbeat(
        self, run_id: str, *, worker_id: str, now: datetime | None = None
    ) -> RetrainingRunRecord:
        record = self.load_run(run_id)
        self._assert_worker(record, worker_id)
        if record.state not in _HEARTBEAT_STATES:
            return record
        timestamp = (now or self._now()).astimezone(timezone.utc)
        return self._save_run(
            replace(
                record,
                heartbeat_at=timestamp,
                updated_at=timestamp,
                generation=record.generation + 1,
            )
        )

    def update_run_metadata(
        self,
        run_id: str,
        *,
        worker_id: str | None = None,
        dataset_version: str | None = None,
        dataset_digest: str | None = None,
        candidate_model_version: str | None = None,
        candidate_model_digest: str | None = None,
        evaluation_digest: str | None = None,
        active_model_version: str | None = None,
        active_model_digest: str | None = None,
    ) -> RetrainingRunRecord:
        """Record stage-produced identities without changing immutable inputs."""

        current = self.load_run(run_id)
        self._assert_worker(current, worker_id)
        for value, field_name in (
            (dataset_digest, "dataset_digest"),
            (candidate_model_digest, "candidate_model_digest"),
            (evaluation_digest, "evaluation_digest"),
            (active_model_digest, "active_model_digest"),
        ):
            if value is not None:
                _validate_digest(value, field_name)
        updated = replace(
            current,
            dataset_version=dataset_version or current.dataset_version,
            dataset_digest=dataset_digest or current.dataset_digest,
            candidate_model_version=candidate_model_version
            or current.candidate_model_version,
            candidate_model_digest=candidate_model_digest
            or current.candidate_model_digest,
            evaluation_digest=evaluation_digest or current.evaluation_digest,
            active_model_version=active_model_version or current.active_model_version,
            active_model_digest=active_model_digest or current.active_model_digest,
            updated_at=self._now(),
            generation=current.generation + 1,
        )
        return self._save_run(updated)

    def fail_run(
        self,
        run_id: str,
        *,
        error_code: str,
        error_message: str,
        retryable: bool,
        worker_id: str | None = None,
        now: datetime | None = None,
    ) -> RetrainingRunRecord:
        if not SAFE_CODE.fullmatch(error_code):
            raise ArtifactRepositoryError("error code is not bounded")
        current = self.load_run(run_id)
        self._assert_worker(current, worker_id)
        timestamp = (now or self._now()).astimezone(timezone.utc)
        can_retry = retryable and current.retry_count < current.max_retries
        next_retry = (
            timestamp + timedelta(seconds=min(60, 2**current.retry_count))
            if can_retry
            else None
        )
        target = RunState.RETRYABLE_FAILED if can_retry else RunState.FAILED
        updated = replace(
            current,
            state=target,
            stage="failed",
            retry_count=current.retry_count + (1 if retryable else 0),
            updated_at=timestamp,
            heartbeat_at=None,
            worker_id=None,
            next_retry_at=next_retry,
            error_code=error_code,
            error_message=_safe_message(error_message) or error_code,
            generation=current.generation + 1,
        )
        return self._save_run(updated)

    def recover_stale_runs(
        self, *, now: datetime | None = None, heartbeat_timeout_seconds: int = 300
    ) -> list[RetrainingRunRecord]:
        timestamp = (now or self._now()).astimezone(timezone.utc)
        recovered: list[RetrainingRunRecord] = []
        for record in self.list_runs():
            if record.state not in _HEARTBEAT_STATES or record.heartbeat_at is None:
                continue
            if (
                timestamp - record.heartbeat_at
            ).total_seconds() <= heartbeat_timeout_seconds:
                continue
            recovered.append(
                self.fail_run(
                    record.run_id,
                    error_code="HEARTBEAT_EXPIRED",
                    error_message="worker heartbeat expired",
                    retryable=True,
                    worker_id=record.worker_id,
                    now=timestamp,
                )
            )
        return recovered

    def publish_json_artifact(
        self,
        run_id: str,
        relative_path: str,
        payload: Mapping[str, Any],
        *,
        stage: str,
        worker_id: str | None = None,
    ) -> dict[str, Any]:
        record = self.load_run(run_id)
        self._assert_worker(record, worker_id)
        path = self._safe_artifact_path(run_id, relative_path)
        content = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
        if len(content) > MAX_ARTIFACT_BYTES:
            raise ArtifactIntegrityError("artifact exceeds the configured size limit")
        digest = _sha256_bytes(content)
        manifest_path = self._run_dir(run_id) / ARTIFACT_MANIFEST_FILENAME
        manifest = self._read_json(manifest_path)
        artifacts = dict(manifest.get("artifacts", {}))
        existing = artifacts.get(relative_path)
        if path.is_file():
            if (
                isinstance(existing, Mapping)
                and existing.get("sha256") == digest
                and path.read_bytes() == content
            ):
                return {
                    "sha256": digest,
                    "size": len(content),
                    "stage": str(existing.get("stage", stage))[:64],
                }
            raise ArtifactIntegrityError(
                "published artifacts are immutable within a run"
            )
        if existing is not None:
            raise ArtifactIntegrityError(
                "artifact manifest is inconsistent with the published file"
            )
        if path.exists():
            raise ArtifactIntegrityError("published artifact path is not a file")
        self._atomic_write(path, content)
        artifacts[relative_path] = {
            "sha256": digest,
            "size": len(content),
            "stage": str(stage)[:64],
        }
        manifest["generation"] = int(manifest.get("generation", 0)) + 1
        manifest["artifacts"] = dict(sorted(artifacts.items()))
        self._atomic_json(manifest_path, manifest)
        return dict(artifacts[relative_path])

    def _safe_artifact_path(self, run_id: str, relative_path: str) -> Path:
        candidate = Path(relative_path)
        if (
            not relative_path
            or candidate.is_absolute()
            or any(part in {"", ".", ".."} for part in candidate.parts)
            or candidate.name
            in {
                RUN_FILENAME,
                EVENTS_FILENAME,
                QUEUE_FILENAME,
                ARTIFACT_MANIFEST_FILENAME,
            }
        ):
            raise ArtifactRepositoryError("artifact path is invalid")
        path = (self._run_dir(run_id) / candidate).resolve()
        try:
            path.relative_to(self._run_dir(run_id))
        except ValueError as exc:
            raise ArtifactRepositoryError(
                "artifact path escapes run directory"
            ) from exc
        return path

    def read_artifact_manifest(self, run_id: str) -> dict[str, Any]:
        return self._read_json(self._run_dir(run_id) / ARTIFACT_MANIFEST_FILENAME)

    def read_json_artifact(self, run_id: str, relative_path: str) -> dict[str, Any]:
        """Read one manifest-tracked JSON artifact after verifying its hash."""

        if not self.verify_artifacts(run_id, (relative_path,)):
            raise ArtifactIntegrityError("required JSON artifact is missing or invalid")
        path = self._safe_artifact_path(run_id, relative_path)
        return self._read_json(path)

    def verify_artifacts(self, run_id: str, relative_paths: Iterable[str]) -> bool:
        manifest = self.read_artifact_manifest(run_id)
        artifacts = manifest.get("artifacts", {})
        for relative_path in relative_paths:
            try:
                path = self._safe_artifact_path(run_id, relative_path)
            except ArtifactRepositoryError:
                return False
            entry = artifacts.get(relative_path)
            if not isinstance(entry, Mapping) or not path.is_file():
                return False
            try:
                if path.stat().st_size != int(entry["size"]):
                    return False
                if _sha256_bytes(path.read_bytes()) != entry["sha256"]:
                    return False
            except OSError, KeyError, TypeError, ValueError:
                return False
        return True

    def complete_stage(
        self,
        run_id: str,
        *,
        next_state: RunState,
        required_artifacts: Iterable[str],
        worker_id: str | None = None,
        stage: str | None = None,
    ) -> RetrainingRunRecord:
        required = tuple(required_artifacts)
        if not self.verify_artifacts(run_id, required):
            raise ArtifactIntegrityError(
                "required stage artifact is missing or invalid"
            )
        return self.transition(run_id, next_state, worker_id=worker_id, stage=stage)

    def append_event(
        self,
        run_id: str,
        *,
        stage: str,
        outcome: str,
        code: str,
        message: str | None = None,
        duration_ms: int | None = None,
        actor_id: str | None = None,
        actor_role: str | None = None,
        candidate_model_version: str | None = None,
        candidate_model_digest: str | None = None,
        active_model_digest: str | None = None,
        previous_staging_version: str | None = None,
        decision: str | None = None,
        scheduled_at: datetime | None = None,
        exit_code: int | None = None,
    ) -> dict[str, Any]:
        if not SAFE_CODE.fullmatch(code):
            raise ArtifactRepositoryError("event code is not bounded")
        record = self.load_run(run_id)
        event = {
            "event_version": "retraining-event.v1",
            "created_at": _iso(self._now()),
            "run_id": run_id,
            "attempt": record.attempt,
            "stage": str(stage)[:64],
            "trigger": record.trigger,
            "dataset_version": record.dataset_version or record.source_dataset_version,
            "active_model_version": record.active_model_version,
            "outcome": str(outcome)[:32],
            "code": code,
            "message": _safe_message(message),
        }
        if duration_ms is not None:
            event["duration_ms"] = max(0, min(int(duration_ms), 86_400_000))
        if actor_id is not None:
            if not actor_id.strip() or len(actor_id) > 128:
                raise ArtifactRepositoryError("event actor identity is invalid")
            event["actor_id"] = actor_id[:128]
        if actor_role is not None:
            if not actor_role.strip() or len(actor_role) > 32:
                raise ArtifactRepositoryError("event actor role is invalid")
            event["actor_role"] = actor_role[:32]
        for value, field_name in (
            (candidate_model_version, "candidate model version"),
            (previous_staging_version, "previous staging version"),
            (decision, "decision"),
        ):
            if value is not None:
                if (
                    not value.strip()
                    or len(value) > 128
                    or any(marker in value for marker in ("/", "\\", ".."))
                ):
                    raise ArtifactRepositoryError(f"{field_name} is invalid")
                event[field_name.replace(" ", "_")] = value
        for value, field_name in (
            (candidate_model_digest, "candidate_model_digest"),
            (active_model_digest, "active_model_digest"),
        ):
            if value is not None:
                _validate_digest(value, field_name)
                event[field_name] = value
        if scheduled_at is not None:
            event["scheduled_at"] = _iso(scheduled_at)
        if exit_code is not None:
            if not isinstance(exit_code, int) or not 0 <= exit_code <= 255:
                raise ArtifactRepositoryError("event exit code is invalid")
            event["exit_code"] = exit_code
        path = self._run_dir(run_id) / EVENTS_FILENAME
        existing = []
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    payload = json.loads(line)
                    if isinstance(payload, dict):
                        existing.append(payload)
        if len(existing) >= MAX_EVENT_COUNT:
            raise ArtifactRepositoryError("run event limit exceeded")
        existing.append(event)
        content = "".join(canonical_json(item) + "\n" for item in existing).encode(
            "utf-8"
        )
        self._atomic_write(path, content)
        return event

    def read_events(self, run_id: str) -> list[dict[str, Any]]:
        path = self._run_dir(run_id) / EVENTS_FILENAME
        if not path.is_file():
            return []
        return [
            payload
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
            for payload in [json.loads(line)]
            if isinstance(payload, dict)
        ]

    def acquire_worker_lock(
        self,
        *,
        worker_id: str,
        now: datetime | None = None,
        stale_after_seconds: int = 300,
    ) -> LocalWorkerLock:
        if (
            not worker_id
            or len(worker_id) > 128
            or any(ord(char) < 32 for char in worker_id)
        ):
            raise WorkerLockBusy("worker identity is invalid")
        timestamp = (now or self._now()).astimezone(timezone.utc)
        lock_path = self.root / WORKER_LOCK_FILENAME
        owner_token = uuid.uuid4().hex
        for _ in range(3):
            try:
                with lock_path.open("x", encoding="utf-8") as handle:
                    json.dump(
                        {
                            "worker_id": worker_id,
                            "owner_token": owner_token,
                            "heartbeat_at": _iso(timestamp),
                        },
                        handle,
                        sort_keys=True,
                    )
                return LocalWorkerLock(self, worker_id, owner_token)
            except FileExistsError:
                try:
                    owner = self._read_json(lock_path)
                    heartbeat = _parse_time(owner.get("heartbeat_at"))
                except ArtifactRepositoryError, ValueError, OSError:
                    corrupt_path = self.root / (
                        f".worker.lock.corrupt.{uuid.uuid4().hex}.json"
                    )
                    try:
                        os.replace(lock_path, corrupt_path)
                    except FileNotFoundError:
                        continue
                    except OSError as exc:
                        raise WorkerLockBusy(
                            "worker lock is malformed and cannot be quarantined"
                        ) from exc
                    continue
                if (timestamp - heartbeat).total_seconds() <= stale_after_seconds:
                    raise WorkerLockBusy(
                        "another worker owns the local retraining lock"
                    )
                stale_path = self.root / f".worker.lock.stale.{uuid.uuid4().hex}.json"
                try:
                    os.replace(lock_path, stale_path)
                    stale_path.unlink(missing_ok=True)
                except FileNotFoundError:
                    continue
        raise WorkerLockBusy("worker lock could not be acquired")

    def _update_lock(self, worker_id: str, owner_token: str, now: datetime) -> None:
        path = self.root / WORKER_LOCK_FILENAME
        owner = self._read_json(path)
        if (
            owner.get("worker_id") != worker_id
            or owner.get("owner_token") != owner_token
        ):
            raise WorkerLockBusy("worker lock ownership changed")
        self._atomic_json(
            path,
            {
                "worker_id": worker_id,
                "owner_token": owner_token,
                "heartbeat_at": _iso(now.astimezone(timezone.utc)),
            },
        )

    def _release_lock(self, worker_id: str, owner_token: str) -> None:
        path = self.root / WORKER_LOCK_FILENAME
        if not path.is_file():
            return
        try:
            owner = self._read_json(path)
        except ArtifactRepositoryError:
            return
        if (
            owner.get("worker_id") == worker_id
            and owner.get("owner_token") == owner_token
        ):
            path.unlink(missing_ok=True)


__all__ = [
    "ArtifactIntegrityError",
    "ArtifactRepositoryError",
    "InvalidRunTransition",
    "LocalWorkerLock",
    "RetrainingRunArtifactRepository",
    "RetrainingRunRecord",
    "WorkerLockBusy",
]
