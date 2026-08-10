from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

from ml_model.retraining.dashboard_contracts import RunState
from web_app.application.retraining_run_use_case import (
    RetrainingInputSnapshot,
    RetrainingRunUseCase,
)
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    RetrainingRunArtifactRepository,
)

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)


@dataclass
class FakeSupervisor:
    calls: int = 0

    def ensure_worker_available(self):
        self.calls += 1
        return {"started": self.calls == 1, "reason": "test"}


class StaticSnapshotProvider:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    async def __call__(self):
        return self.snapshot


def _snapshot(*, approved_sample_count: int = 2, active_digest: str = "d" * 64):
    return RetrainingInputSnapshot(
        source_review_revisions=("2:1", "1:2"),
        source_dataset_version="v3_907k_cleaned",
        source_dataset_digest="b" * 64,
        pipeline_fingerprint="c" * 64,
        active_model_version="active-v1",
        active_model_digest=active_digest,
        approved_sample_count=approved_sample_count,
    )


@pytest.mark.asyncio
async def test_start_is_idempotent_for_same_snapshot_and_does_not_duplicate_worker(
    tmp_path,
):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    supervisor = FakeSupervisor()
    use_case = RetrainingRunUseCase(
        repository,
        snapshot_provider=StaticSnapshotProvider(_snapshot()),
        worker_supervisor=supervisor,
        clock=lambda: NOW,
    )

    first = await use_case.start_run(
        trigger="manual", requested_by="analyst-1", requested_timezone="Asia/Manila"
    )
    second = await use_case.start_run(
        trigger="manual", requested_by="analyst-2", requested_timezone="UTC"
    )

    assert first.created is True
    assert second.created is False
    assert first.run.run_id == second.run.run_id
    assert first.run.input_fingerprint == second.run.input_fingerprint
    assert supervisor.calls == 2


@pytest.mark.asyncio
async def test_no_approved_data_is_a_terminal_noop_and_does_not_start_worker(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    supervisor = FakeSupervisor()
    use_case = RetrainingRunUseCase(
        repository,
        snapshot_provider=StaticSnapshotProvider(_snapshot(approved_sample_count=0)),
        worker_supervisor=supervisor,
        clock=lambda: NOW,
    )

    result = await use_case.start_run(
        trigger="scheduled", requested_by="scheduler", requested_timezone="UTC"
    )

    assert result.run.state is RunState.SKIPPED_NO_APPROVED_DATA
    assert supervisor.calls == 0
    assert repository.read_events(result.run.run_id)[-1]["code"] == "NO_APPROVED_DATA"


@pytest.mark.asyncio
async def test_changed_active_digest_creates_a_new_fingerprint(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    supervisor = FakeSupervisor()
    provider = StaticSnapshotProvider(_snapshot())
    use_case = RetrainingRunUseCase(
        repository,
        snapshot_provider=provider,
        worker_supervisor=supervisor,
        clock=lambda: NOW,
    )

    first = await use_case.start_run(
        trigger="manual", requested_by="analyst-1", requested_timezone="UTC"
    )
    provider.snapshot = _snapshot(active_digest="e" * 64)
    second = await use_case.start_run(
        trigger="manual", requested_by="analyst-1", requested_timezone="UTC"
    )

    assert first.run.run_id != second.run.run_id
    assert first.run.input_fingerprint != second.run.input_fingerprint


@pytest.mark.asyncio
async def test_request_validation_rejects_unsafe_trigger_identity_and_note(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    use_case = RetrainingRunUseCase(
        repository,
        snapshot_provider=StaticSnapshotProvider(_snapshot()),
        worker_supervisor=FakeSupervisor(),
        clock=lambda: NOW,
    )

    with pytest.raises(ValueError):
        await use_case.start_run(
            trigger="shell", requested_by="analyst-1", requested_timezone="UTC"
        )
    with pytest.raises(ValueError):
        await use_case.start_run(
            trigger="manual", requested_by="analyst\nraw", requested_timezone="UTC"
        )
    with pytest.raises(ValueError):
        await use_case.start_run(
            trigger="manual",
            requested_by="analyst-1",
            requested_timezone="UTC",
            operator_note="x" * 501,
        )
