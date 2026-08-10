import json
from datetime import datetime, timedelta, timezone

import pytest

from ml_model.retraining.dashboard_contracts import RunState
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    ArtifactIntegrityError,
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
    manifest = repository.read_artifact_manifest(RUN_ID)
    assert manifest["artifacts"]["stages/export.json"]["sha256"]
    assert repository.verify_artifacts(RUN_ID, ("stages/export.json",)) is True
    path = tmp_path / "runs" / RUN_ID / "stages" / "export.json"
    path.write_text("tampered", encoding="utf-8")
    assert repository.verify_artifacts(RUN_ID, ("stages/export.json",)) is False


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
