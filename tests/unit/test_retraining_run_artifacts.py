import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone

import pytest

from ml_model.retraining.dashboard_contracts import RunState
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    ArtifactIntegrityError,
    ArtifactRepositoryError,
    InvalidRunTransition,
    RetrainingRunArtifactRepository,
    RetrainingRunRecord,
    WorkerLockBusy,
)

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
RUN_ID = "retrain-20260810T120000Z-000000000001"


def _record(
    *,
    run_id: str = RUN_ID,
    state: RunState = RunState.QUEUED,
    approved_sample_count: int = 1,
    max_retries: int = 2,
) -> RetrainingRunRecord:
    return RetrainingRunRecord(
        run_id=run_id,
        state=state,
        stage="queued",
        attempt=0,
        retry_count=0,
        max_retries=max_retries,
        created_at=NOW,
        updated_at=NOW,
        heartbeat_at=None,
        trigger="manual",
        requested_by="analyst-1",
        requested_timezone="Asia/Manila",
        input_fingerprint="a" * 64,
        source_review_revisions=("1:1",),
        source_dataset_version="v3_907k_cleaned",
        source_dataset_digest="b" * 64,
        pipeline_fingerprint="c" * 64,
        active_model_version="active-v1",
        active_model_digest="d" * 64,
        approved_sample_count=approved_sample_count,
        operator_note="manual smoke",
    )


def test_queue_is_atomic_versioned_and_rejects_path_traversal(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)

    created = repository.create_or_get_run(_record())

    assert created.run_id == RUN_ID
    assert (tmp_path / "runs" / RUN_ID / "run.json").is_file()
    queue = json.loads((tmp_path / "runs" / "queue.json").read_text(encoding="utf-8"))
    assert queue["generation"] == 1
    assert queue["runs"][0]["state"] == "queued"
    duplicate = repository.create_or_get_run(_record())
    assert duplicate.run_id == RUN_ID
    assert (
        json.loads((tmp_path / "runs" / "queue.json").read_text(encoding="utf-8"))[
            "generation"
        ]
        == 1
    )

    with pytest.raises(ValueError):
        repository.load_run("../outside")


def test_reviewed_run_states_require_dataset_candidate_and_evaluation_bindings(
    tmp_path,
):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)

    with pytest.raises(ArtifactRepositoryError, match="state requires"):
        repository.create_or_get_run(_record(state=RunState.APPROVED))


def test_fingerprint_reservation_makes_concurrent_run_creation_idempotent(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    first_observers = threading.Barrier(2)
    original_find = repository.find_by_input_fingerprint
    calls = 0
    calls_lock = threading.Lock()

    def synchronized_find(fingerprint):
        nonlocal calls
        with calls_lock:
            calls += 1
            should_wait = calls <= 2
        if should_wait:
            first_observers.wait(timeout=5)
        return original_find(fingerprint)

    repository.find_by_input_fingerprint = synchronized_find
    records = []
    errors = []

    def create(record):
        try:
            records.append(repository.create_or_get_run(record))
        except Exception as exc:  # pragma: no cover - assertion reports the error
            errors.append(exc)

    threads = [
        threading.Thread(target=create, args=(_record(run_id=run_id),))
        for run_id in (
            RUN_ID,
            "retrain-20260810T120001Z-000000000002",
        )
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert errors == []
    assert len(records) == 2
    assert len({record.run_id for record in records}) == 1
    assert len(repository.list_runs()) == 1


def test_orphaned_fingerprint_reservation_is_recovered(tmp_path, monkeypatch):
    from web_app.infrastructure.repositories import (
        retraining_run_artifact_repository as artifact_repository,
    )

    repository = artifact_repository.RetrainingRunArtifactRepository(
        tmp_path / "runs", clock=lambda: NOW
    )
    reservation = repository.root / (
        f".run-fingerprint.{_record().input_fingerprint}.reservation"
    )
    reservation.mkdir()
    (reservation / artifact_repository.RUN_RESERVATION_OWNER_FILENAME).write_text(
        json.dumps(
            {
                "pid": 4_000_000,
                "created_at": time.time()
                - artifact_repository.RUN_RESERVATION_STALE_SECONDS
                - 1,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        artifact_repository, "_reservation_owner_is_live", lambda _pid: False
    )

    created = repository.create_or_get_run(_record())

    assert created.run_id == RUN_ID
    assert len(repository.list_runs()) == 1
    assert not reservation.exists()


def test_live_fingerprint_reservation_is_not_recovered(tmp_path, monkeypatch):
    from web_app.infrastructure.repositories import (
        retraining_run_artifact_repository as artifact_repository,
    )

    repository = artifact_repository.RetrainingRunArtifactRepository(
        tmp_path / "runs", clock=lambda: NOW
    )
    reservation = repository.root / (
        f".run-fingerprint.{_record().input_fingerprint}.reservation"
    )
    reservation.mkdir()
    (reservation / artifact_repository.RUN_RESERVATION_OWNER_FILENAME).write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "created_at": time.time()
                - artifact_repository.RUN_RESERVATION_STALE_SECONDS
                - 1,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(artifact_repository, "RUN_RESERVATION_WAIT_SECONDS", 0.02)
    monkeypatch.setattr(
        artifact_repository, "_reservation_owner_is_live", lambda _pid: True
    )

    with pytest.raises(ArtifactRepositoryError, match="same input fingerprint"):
        repository.create_or_get_run(_record())

    assert reservation.exists()


def test_run_manifest_is_published_after_supporting_artifacts(tmp_path, monkeypatch):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    original_atomic_json = repository._atomic_json

    def observe_publication(path, payload):
        if path.name == "run.json":
            assert (path.parent / "artifact_manifest.json").is_file()
            assert (path.parent / "events.jsonl").is_file()
        original_atomic_json(path, payload)

    monkeypatch.setattr(repository, "_atomic_json", observe_publication)

    repository.create_or_get_run(_record())


def test_stage_completion_requires_published_artifact_and_valid_transition(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())
    claimed = repository.claim_next(worker_id="worker-a", now=NOW)
    assert claimed is not None
    assert claimed.state is RunState.EXPORTING
    with pytest.raises(ArtifactIntegrityError):
        repository.complete_stage(
            RUN_ID,
            next_state=RunState.DATASET_VALIDATED,
            required_artifacts=("stages/export.json",),
            worker_id="worker-a",
        )

    repository.publish_json_artifact(
        RUN_ID,
        "stages/export.json",
        {"status": "CONTROLLED_SMOKE", "row_count": 1},
        stage="export",
        worker_id="worker-a",
    )
    completed = repository.complete_stage(
        RUN_ID,
        next_state=RunState.DATASET_VALIDATED,
        required_artifacts=("stages/export.json",),
        worker_id="worker-a",
    )
    assert completed.state is RunState.DATASET_VALIDATED
    with pytest.raises(InvalidRunTransition):
        repository.transition(
            RUN_ID,
            RunState.DEPLOYED,
            worker_id="worker-a",
        )


def test_worker_lock_contention_and_stale_recovery_are_bounded(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    first = repository.acquire_worker_lock(
        worker_id="worker-a", now=NOW, stale_after_seconds=60
    )
    with pytest.raises(WorkerLockBusy):
        repository.acquire_worker_lock(
            worker_id="worker-b", now=NOW, stale_after_seconds=60
        )
    first.heartbeat(NOW + timedelta(seconds=10))
    first.release()

    stale_path = tmp_path / "runs" / ".worker.lock.json"
    stale_path.write_text(
        json.dumps(
            {
                "worker_id": "dead-worker",
                "owner_token": "dead-token",
                "heartbeat_at": "2026-08-10T10:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    recovered = repository.acquire_worker_lock(
        worker_id="worker-c", now=NOW, stale_after_seconds=60
    )
    assert recovered.worker_id == "worker-c"
    recovered.release()


def test_expired_run_heartbeat_becomes_retryable_with_recovery_code(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())
    claimed = repository.claim_next(worker_id="worker-a", now=NOW)
    assert claimed is not None

    recovered = repository.recover_stale_runs(
        now=NOW + timedelta(seconds=301), heartbeat_timeout_seconds=300
    )

    assert len(recovered) == 1
    assert recovered[0].state is RunState.RETRYABLE_FAILED
    assert recovered[0].error_code == "HEARTBEAT_EXPIRED"


def test_events_are_bounded_and_artifact_manifest_is_hash_checked(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())
    long_message = "safe failure " + ("x" * 1000)
    event = repository.append_event(
        RUN_ID,
        stage="queued",
        outcome="INFO",
        code="RUN_QUEUED",
        message=long_message,
    )
    assert len(event["message"]) <= 500
    repository.publish_json_artifact(
        RUN_ID,
        "stages/export.json",
        {"status": "CONTROLLED_SMOKE"},
        stage="export",
    )
    assert repository.publish_json_artifact(
        RUN_ID,
        "stages/export.json",
        {"status": "CONTROLLED_SMOKE"},
        stage="export",
    )["sha256"]
    with pytest.raises(ArtifactIntegrityError, match="immutable"):
        repository.publish_json_artifact(
            RUN_ID,
            "stages/export.json",
            {"status": "changed"},
            stage="export",
        )
    manifest = repository.read_artifact_manifest(RUN_ID)
    assert manifest["artifacts"]["stages/export.json"]["sha256"]
    assert repository.verify_artifacts(RUN_ID, ("stages/export.json",)) is True
    path = tmp_path / "runs" / RUN_ID / "stages" / "export.json"
    path.write_text("tampered", encoding="utf-8")
    assert repository.verify_artifacts(RUN_ID, ("stages/export.json",)) is False
    path.unlink()
    with pytest.raises(ArtifactIntegrityError, match="manifest is inconsistent"):
        repository.publish_json_artifact(
            RUN_ID,
            "stages/export.json",
            {"status": "CONTROLLED_SMOKE"},
            stage="export",
        )

    with pytest.raises(ArtifactRepositoryError):
        repository.publish_json_artifact(
            RUN_ID,
            "artifact_manifest.json",
            {"unsafe": True},
            stage="export",
        )


def test_malformed_worker_lock_is_quarantined_instead_of_blocking_forever(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    lock_path = tmp_path / "runs" / ".worker.lock.json"
    lock_path.write_text("{not-json", encoding="utf-8")

    recovered = repository.acquire_worker_lock(
        worker_id="worker-a", now=NOW, stale_after_seconds=60
    )

    assert recovered.worker_id == "worker-a"
    assert list((tmp_path / "runs").glob(".worker.lock.corrupt.*.json"))
    recovered.release()


def test_stale_worker_cannot_publish_after_run_ownership_is_cleared(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())
    claimed = repository.claim_next(worker_id="worker-a", now=NOW)
    assert claimed is not None
    repository.fail_run(
        RUN_ID,
        error_code="WORKER_TIMEOUT",
        error_message="bounded timeout",
        retryable=False,
        worker_id="worker-a",
        now=NOW,
    )

    with pytest.raises(ArtifactRepositoryError, match="ownership"):
        repository.publish_json_artifact(
            RUN_ID,
            "stages/late.json",
            {"stale": True},
            stage="late",
            worker_id="worker-a",
        )


def test_claim_cleans_only_abandoned_atomic_temporary_artifacts(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())
    temporary = tmp_path / "runs" / RUN_ID / "stages" / ".export.json.deadbeef.tmp"
    temporary.parent.mkdir(parents=True)
    temporary.write_text("partial", encoding="utf-8")

    claimed = repository.claim_next(worker_id="worker-a", now=NOW)

    assert claimed is not None
    assert not temporary.exists()


def test_stage_metadata_records_candidate_and_evaluation_digests(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())

    updated = repository.update_run_metadata(
        RUN_ID,
        dataset_version="dashboard-dataset-v1",
        dataset_digest="e" * 64,
        candidate_model_version="candidate-v1",
        candidate_model_digest="f" * 64,
        evaluation_digest="0" * 64,
    )

    assert updated.dataset_version == "dashboard-dataset-v1"
    assert updated.candidate_model_digest == "f" * 64
    assert updated.evaluation_digest == "0" * 64
