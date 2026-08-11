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

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)


@dataclass
class FakeSupervisor:
    calls: int = 0

    def ensure_worker_available(self):
        self.calls += 1


class StaticSnapshotProvider:
    def __init__(self, snapshot):
        self.snapshot = snapshot

    async def __call__(self):
        return self.snapshot


def _snapshot(active_digest: str) -> RetrainingInputSnapshot:
    return RetrainingInputSnapshot(
        source_review_revisions=("1:1",),
        source_dataset_version="v3_907k_cleaned",
        source_dataset_digest="b" * 64,
        pipeline_fingerprint="c" * 64,
        active_model_version="active-v1",
        active_model_digest=active_digest,
        approved_sample_count=2,
    )


@pytest.mark.asyncio
async def test_scheduled_request_skips_when_another_snapshot_is_active(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    supervisor = FakeSupervisor()
    provider = StaticSnapshotProvider(_snapshot("d" * 64))
    use_case = RetrainingRunUseCase(
        repository,
        snapshot_provider=provider,
        worker_supervisor=supervisor,
        clock=lambda: NOW,
    )

    first = await use_case.start_run(
        trigger="manual", requested_by="analyst-1", requested_timezone="Asia/Manila"
    )
    repository.transition(first.run.run_id, RunState.EXPORTING)
    repository.transition(first.run.run_id, RunState.DATASET_VALIDATED)
    repository.transition(first.run.run_id, RunState.TRAINING)

    provider.snapshot = _snapshot("e" * 64)
    second = await use_case.start_run(
        trigger="scheduled", requested_by="scheduler", requested_timezone="Asia/Manila"
    )

    assert second.created is False
    assert second.run.run_id == first.run.run_id
    assert second.run.state is RunState.TRAINING
    assert repository.read_events(first.run.run_id)[-1]["code"] == (
        "SCHEDULE_SKIPPED_CONCURRENT_RUN"
    )
    assert supervisor.calls == 1


@pytest.mark.asyncio
async def test_scheduled_request_remains_a_terminal_noop_without_approved_data(
    tmp_path,
):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    supervisor = FakeSupervisor()
    use_case = RetrainingRunUseCase(
        repository,
        snapshot_provider=lambda: RetrainingInputSnapshot(
            source_review_revisions=("1:1",),
            source_dataset_version="v3_907k_cleaned",
            source_dataset_digest="b" * 64,
            pipeline_fingerprint="c" * 64,
            active_model_version="active-v1",
            active_model_digest="d" * 64,
            approved_sample_count=0,
        ),
        worker_supervisor=supervisor,
        clock=lambda: NOW,
    )

    result = await use_case.start_run(
        trigger="scheduled", requested_by="scheduler", requested_timezone="Asia/Manila"
    )

    assert result.created is True
    assert result.run.state is RunState.SKIPPED_NO_APPROVED_DATA
    assert supervisor.calls == 0
