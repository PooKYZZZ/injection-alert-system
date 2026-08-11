from datetime import datetime, timezone

import pytest

from ml_model.retraining.dashboard_contracts import RunState
from web_app.application.retraining_control_use_case import (
    RetrainingControlError,
    RetrainingControlUseCase,
)
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    ArtifactRepositoryError,
    RetrainingRunArtifactRepository,
    RetrainingRunRecord,
)
from web_app.domain.retraining import RetrainingReviewSummary

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)


def _record(
    run_id: str, *, state: RunState = RunState.PENDING_APPROVAL
) -> RetrainingRunRecord:
    return RetrainingRunRecord(
        run_id=run_id,
        state=state,
        stage=state.value,
        attempt=1,
        retry_count=0,
        max_retries=2,
        created_at=NOW,
        updated_at=NOW,
        heartbeat_at=NOW,
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
        approved_sample_count=1,
        dataset_version="dashboard-dataset-v1",
        dataset_digest="e" * 64,
        candidate_model_version="candidate-v1",
        candidate_model_digest="f" * 64,
        evaluation_digest="0" * 64,
    )


def _control(repository: RetrainingRunArtifactRepository) -> RetrainingControlUseCase:
    return RetrainingControlUseCase(
        object(),
        repository,
        object(),
        object(),
        clock=lambda: NOW,
    )


class _ReviewRepository:
    async def get_retraining_review_summary(self):
        return RetrainingReviewSummary(approved=1, excluded=0, unreviewed=0)


@pytest.mark.asyncio
async def test_summary_marks_queued_runs_as_in_progress(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000004"
    repository.create_or_get_run(_record(run_id, state=RunState.QUEUED))
    control = RetrainingControlUseCase(
        _ReviewRepository(),
        repository,
        object(),
        object(),
        clock=lambda: NOW,
    )

    summary = await control.get_summary()

    assert summary.run_in_progress is True


def test_hold_requires_reason_and_records_administrator_event(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000001"
    repository.create_or_get_run(_record(run_id))
    control = _control(repository)

    with pytest.raises(RetrainingControlError, match="reason is required"):
        control.decide(
            run_id=run_id,
            decision="hold",
            reason=None,
            actor_id="admin-1",
            actor_role="ADMIN",
        )

    result = control.decide(
        run_id=run_id,
        decision="hold",
        reason="Need a second reviewer.",
        actor_id="admin-1",
        actor_role="ADMIN",
    )

    assert result.run.state is RunState.HELD
    event = repository.read_events(run_id)[-1]
    assert event["code"] == "CANDIDATE_HOLD"
    assert event["actor_id"] == "admin-1"
    assert event["actor_role"] == "ADMIN"
    assert event["message"] == "Need a second reviewer."
    with pytest.raises(ArtifactRepositoryError):
        repository.append_event(
            run_id,
            stage="decision",
            outcome="WARN",
            code="REDACTION_CHECK",
            message="INTERNAL_API_KEY=should-not-be-stored",
        )


def test_approve_requires_complete_candidate_and_evaluation_evidence(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000002"
    repository.create_or_get_run(_record(run_id))
    control = _control(repository)

    with pytest.raises(RetrainingControlError, match="passing evaluation"):
        control.decide(
            run_id=run_id,
            decision="approve",
            reason=None,
            actor_id="admin-1",
            actor_role="ADMIN",
        )

    repository.publish_json_artifact(
        run_id,
        "stages/evaluation.json",
        {"evidence_status": "NATIVE", "status": "PASS"},
        stage="evaluation",
    )
    repository.publish_json_artifact(
        run_id,
        "stages/comparison.json",
        {
            "overall_status": "PASS",
            "decision_allowed": True,
            "provenance": {
                "dataset_version": "dashboard-dataset-v1",
                "dataset_digest": "e" * 64,
                "evaluation_digest": "0" * 64,
                "active_model_digest": "d" * 64,
                "candidate_model_digest": "f" * 64,
            },
            "gate_results": {
                "active_model_binding": {"status": "PASS"},
                "evaluation_binding": {"status": "PASS"},
                "evidence": {"status": "PASS"},
                "security_regression": {"status": "PASS"},
                "quality": {"status": "PASS"},
                "improvement": {"status": "PASS"},
            },
        },
        stage="evidence_comparison",
    )
    result = control.decide(
        run_id=run_id,
        decision="approve",
        reason=None,
        actor_id="admin-1",
        actor_role="ADMIN",
    )

    assert result.run.state is RunState.APPROVED


def test_decision_rejects_runs_that_are_not_pending_approval(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000003"
    repository.create_or_get_run(_record(run_id, state=RunState.QUEUED))
    control = _control(repository)

    with pytest.raises(RetrainingControlError, match="not awaiting"):
        control.decide(
            run_id=run_id,
            decision="hold",
            reason="not ready",
            actor_id="admin-1",
            actor_role="ADMIN",
        )
