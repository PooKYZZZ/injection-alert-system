from dataclasses import replace
from datetime import datetime, timezone

import pytest

from ml_model.retraining.dashboard_contracts import RunState
from web_app.application.retraining_control_use_case import (
    RetrainingControlError,
    RetrainingControlUseCase,
)
from web_app.domain.retraining import RetrainingReviewSummary
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    ArtifactRepositoryError,
    RetrainingRunArtifactRepository,
    RetrainingRunRecord,
)

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


def test_run_detail_reports_published_evidence_status(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000005"
    repository.create_or_get_run(_record(run_id))
    evaluation = repository.publish_json_artifact(
        run_id,
        "stages/evaluation.json",
        {"evidence_status": "NATIVE", "status": "PASS"},
        stage="evaluation",
    )
    repository.publish_json_artifact(
        run_id,
        "stages/comparison.json",
        {"overall_status": "PASS"},
        stage="evidence_comparison",
    )
    repository.update_run_metadata(run_id, evaluation_digest=evaluation["sha256"])

    detail = _control(repository).get_run_detail(run_id)

    assert detail.evidence_status == "NATIVE"


def test_run_detail_reports_not_run_before_evaluation_is_published(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000015"
    repository.create_or_get_run(
        replace(
            _record(run_id, state=RunState.TRAINING),
            evaluation_digest=None,
        )
    )

    detail = _control(repository).get_run_detail(run_id)

    assert detail.evidence_status == "NOT_RUN"
    assert detail.evidence_summary.evaluation_status == "NOT_RUN"
    assert detail.evidence_summary.comparison_status == "NOT_RUN"


def test_run_detail_preserves_not_run_for_published_smoke_evidence(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000020"
    repository.create_or_get_run(_record(run_id, state=RunState.NOT_ENOUGH_EVIDENCE))
    repository.publish_json_artifact(
        run_id,
        "stages/evaluation.json",
        {
            "evidence_status": "NOT_RUN",
            "gate_status": "NOT_ENOUGH_EVIDENCE",
            "native_training_status": "NOT_RUN",
        },
        stage="evaluation",
    )
    repository.publish_json_artifact(
        run_id,
        "stages/comparison.json",
        {
            "comparison_status": "NOT_RUN",
            "gate_status": "NOT_ENOUGH_EVIDENCE",
        },
        stage="evidence_comparison",
    )

    detail = _control(repository).get_run_detail(run_id)

    assert detail.evidence_status == "NOT_RUN"
    assert detail.evidence_summary.evaluation_status == "NOT_RUN"
    assert detail.evidence_summary.comparison_status == "NOT_RUN"


def test_run_detail_reports_invalid_when_artifact_manifest_is_unreadable(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000021"
    repository.create_or_get_run(
        replace(
            _record(run_id, state=RunState.TRAINING),
            evaluation_digest=None,
        )
    )
    manifest_path = tmp_path / "runs" / run_id / "artifact_manifest.json"
    manifest_path.write_text("{", encoding="utf-8")

    detail = _control(repository).get_run_detail(run_id)

    assert detail.evidence_status == "INVALID"
    assert detail.evidence_summary.evaluation_status == "INVALID"
    assert detail.evidence_summary.comparison_status == "INVALID"


def test_run_detail_reports_invalid_when_published_evidence_is_missing(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000016"
    repository.create_or_get_run(_record(run_id))

    detail = _control(repository).get_run_detail(run_id)

    assert detail.evidence_status == "INVALID"
    assert detail.evidence_summary.evaluation_status == "INVALID"
    assert detail.evidence_summary.comparison_status == "INVALID"


def test_run_detail_reports_invalid_when_published_evidence_is_corrupted(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000017"
    repository.create_or_get_run(_record(run_id))
    repository.publish_json_artifact(
        run_id,
        "stages/evaluation.json",
        {"evidence_status": "NATIVE", "status": "PASS"},
        stage="evaluation",
    )
    repository.publish_json_artifact(
        run_id,
        "stages/comparison.json",
        {"overall_status": "PASS"},
        stage="evidence_comparison",
    )
    evaluation_path = tmp_path / "runs" / run_id / "stages" / "evaluation.json"
    evaluation_path.write_text("{}", encoding="utf-8")

    detail = _control(repository).get_run_detail(run_id)

    assert detail.evidence_status == "INVALID"
    assert detail.evidence_summary.evaluation_status == "INVALID"
    assert detail.evidence_summary.comparison_status == "INVALID"


def test_run_detail_reports_invalid_when_evidence_is_published_without_digest(
    tmp_path,
):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000018"
    repository.create_or_get_run(
        replace(
            _record(run_id, state=RunState.EVALUATING),
            evaluation_digest=None,
        )
    )
    repository.publish_json_artifact(
        run_id,
        "stages/evaluation.json",
        {"evidence_status": "NATIVE", "status": "PASS"},
        stage="evaluation",
    )

    detail = _control(repository).get_run_detail(run_id)

    assert detail.evidence_status == "INVALID"
    assert detail.evidence_summary.evaluation_status == "INVALID"
    assert detail.evidence_summary.comparison_status == "INVALID"


def test_run_detail_reports_invalid_for_malformed_published_status(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000019"
    repository.create_or_get_run(_record(run_id))
    evaluation = repository.publish_json_artifact(
        run_id,
        "stages/evaluation.json",
        {"evidence_status": "NATIVE", "status": "BROKEN"},
        stage="evaluation",
    )
    repository.publish_json_artifact(
        run_id,
        "stages/comparison.json",
        {"overall_status": "PASS"},
        stage="evidence_comparison",
    )
    repository.update_run_metadata(run_id, evaluation_digest=evaluation["sha256"])

    detail = _control(repository).get_run_detail(run_id)

    assert detail.evidence_status == "INVALID"
    assert detail.evidence_summary.evaluation_status == "INVALID"
    assert detail.evidence_summary.comparison_status == "INVALID"


def test_run_detail_redacts_non_numeric_evidence_values(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    run_id = "retrain-20260811T120000Z-000000000006"
    repository.create_or_get_run(_record(run_id))
    repository.publish_json_artifact(
        run_id,
        "stages/evaluation.json",
        {
            "evidence_status": "NATIVE",
            "status": "PASS",
            "preprocessing_version": "http-preprocessor-v1",
            "evaluation_split": "frozen_test",
        },
        stage="evaluation",
    )
    repository.publish_json_artifact(
        run_id,
        "stages/comparison.json",
        {
            "overall_status": "PASS",
            "metric_comparisons": {
                "macro_f1": {
                    "active": {"value": True},
                    "candidate": {"value": 10**1000, "support_count": True},
                    "delta": "not-a-number",
                }
            },
        },
        stage="evidence_comparison",
    )

    detail = _control(repository).get_run_detail(run_id)

    macro_f1 = next(
        metric
        for metric in detail.evidence_summary.metrics
        if metric.name == "macro_f1"
    )
    assert macro_f1.active_value is None
    assert macro_f1.candidate_value is None
    assert macro_f1.delta is None
    assert macro_f1.support_count is None


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
            actor_id="owner-1",
            actor_role="OWNER",
        )

    result = control.decide(
        run_id=run_id,
        decision="hold",
        reason="Need a second reviewer.",
        actor_id="owner-1",
        actor_role="OWNER",
    )

    assert result.run.state is RunState.HELD
    event = repository.read_events(run_id)[-1]
    assert event["code"] == "CANDIDATE_HOLD"
    assert event["actor_id"] == "owner-1"
    assert event["actor_role"] == "OWNER"
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
            actor_id="owner-1",
            actor_role="OWNER",
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
        actor_id="owner-1",
        actor_role="OWNER",
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
            actor_id="owner-1",
            actor_role="OWNER",
        )
