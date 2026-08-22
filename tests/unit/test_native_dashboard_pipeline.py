import json
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

import ml_model.retraining.dashboard_pipeline as pipeline_module
from ml_model.preprocessing.model_input import MODEL_INPUT_VERSION
from ml_model.retraining.dashboard_contracts import GateStatus, RunState
from ml_model.retraining.dashboard_export import export_dashboard_reviews
from ml_model.retraining.dashboard_pipeline import NativeDashboardPipeline, PipelineFailure
from ml_model.retraining.content_digest import compute_content_digest
from web_app.domain.retraining import RetrainingReviewCandidate
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    RetrainingRunArtifactRepository,
    RetrainingRunRecord,
)
from ml_model.retraining.dashboard_worker import EXIT_TERMINAL_FAILURE, DashboardWorker

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
RUN_ID = "retrain-20260810T120000Z-000000000001"


def _record() -> RetrainingRunRecord:
    return RetrainingRunRecord(
        run_id=RUN_ID,
        state=RunState.QUEUED,
        stage="queued",
        attempt=0,
        retry_count=0,
        max_retries=2,
        created_at=NOW,
        updated_at=NOW,
        heartbeat_at=None,
        trigger="manual",
        requested_by="analyst-1",
        requested_timezone="UTC",
        input_fingerprint="a" * 64,
        source_review_revisions=("1:1",),
        source_dataset_version="v3_907k_cleaned",
        source_dataset_digest="b" * 64,
        pipeline_fingerprint="c" * 64,
        active_model_version="active-v1",
        active_model_digest="d" * 64,
        approved_sample_count=1,
    )


def _candidate() -> RetrainingReviewCandidate:
    text = "get /native"
    return RetrainingReviewCandidate(
        review_id=1,
        traffic_log_id=1,
        revision=1,
        predicted_label=None,
        verified_label="Normal",
        approval_state="approved_for_training",
        reviewer_id="analyst-1",
        reviewer_role="ANALYST",
        reviewed_at=NOW,
        model_version="active-v1",
        prediction_confidence=None,
        prediction_confidence_level=None,
        model_input_hash=sha256(text.encode()).hexdigest(),
        model_input_text=text,
        preprocessing_version=MODEL_INPUT_VERSION,
        ingest_event_hash="e" * 64,
        source_verification_status="VERIFIED",
        source_provenance="DIRECT_REMOTE_ADDR",
    )


def _prepare_run_artifacts(repository, root: Path, monkeypatch) -> Path:
    repository.create_or_get_run(_record())
    export_dashboard_reviews(
        [_candidate()],
        run_id=RUN_ID,
        output_root=root,
        source_dataset_version="v3_907k_cleaned",
        expected_preprocessing_version=MODEL_INPUT_VERSION,
        created_at=NOW,
    )
    run_dir = root / RUN_ID
    dataset_dir = run_dir / "dataset"
    dataset_dir.mkdir()
    (dataset_dir / "test.parquet").write_bytes(b"validated snapshot")
    monkeypatch.setattr(
        pipeline_module,
        "_load_existing_dataset",
        lambda **_: SimpleNamespace(
            dataset_dir=dataset_dir,
            dataset_version="dashboard-test-snapshot",
            manifest={
                "manifest_sha256": "f" * 64,
                "row_counts": {"train": 1, "validation": 1, "test": 1},
                "historical_data_unchanged": True,
            },
        ),
    )
    return run_dir


def test_native_worker_path_reaches_pending_approval_without_touching_production(
    tmp_path, monkeypatch
):
    root = tmp_path / "runs"
    project_root = tmp_path / "project"
    (project_root / "ml_model" / "model_registry" / "production").mkdir(parents=True)
    production_marker = project_root / "ml_model" / "model_registry" / "production" / "active.txt"
    production_marker.write_text("unchanged", encoding="utf-8")
    repository = RetrainingRunArtifactRepository(root, clock=lambda: NOW)
    run_dir = _prepare_run_artifacts(repository, root, monkeypatch)

    training_calls = []

    def fake_native_training(config):
        training_calls.append(config)
        training_source = (
            config.output_dir
            / "distilbert"
            / "loss_weighted_ce"
            / "seed_0042"
        )
        (training_source / "checkpoint").mkdir(parents=True)
        for name in (
            "config_metadata.json",
            "summary_metrics.json",
            "per_class_metrics.json",
            "calibration.json",
        ):
            (training_source / name).write_text("{}\n", encoding="utf-8")
        (
            training_source
            / "checkpoint"
            / "best_distilbert_weighted_ce_seed0042.pt"
        ).write_bytes(b"checkpoint")
        return training_source

    monkeypatch.setattr(pipeline_module, "_run_native_training", fake_native_training)

    candidate_path = run_dir / "candidate_model"
    candidate_path.mkdir()
    (candidate_path / "serving_manifest.json").write_text(
        json.dumps({"model_version": f"distilbert_dashboard_{RUN_ID}", "temperature": 1.0, "local_reload_verified": True}),
        encoding="utf-8",
    )
    (candidate_path / "git_hash.txt").write_text("test\n", encoding="utf-8")
    (run_dir / "candidate_evaluation" / "native").mkdir(parents=True)
    candidate_digest = compute_content_digest(candidate_path)

    monkeypatch.setattr(
        pipeline_module,
        "_build_candidate_artifact",
        lambda **_: (candidate_path, f"distilbert_dashboard_{RUN_ID}", candidate_digest),
    )
    monkeypatch.setattr(
        pipeline_module,
        "_evaluate_candidate",
        lambda **_: (
            SimpleNamespace(overall_status=GateStatus.PASS),
            "a" * 64,
            {"stage": "evaluation", "evidence_status": "NATIVE", "status": "PASS"},
            {"stage": "evidence_comparison", "overall_status": "PASS"},
        ),
    )
    monkeypatch.setattr(
        "ml_model.export.promote_final_training_run.write_eval_provenance_files",
        lambda **_: run_dir / "candidate_evaluation" / "native",
    )

    worker = DashboardWorker(
        repository,
        root=root,
        pipeline=NativeDashboardPipeline(project_root=project_root),
        smoke=False,
        worker_id="native-worker",
        clock=lambda: NOW,
    )
    result = worker.run_once()

    assert result.state is RunState.PENDING_APPROVAL, repository.load_run(RUN_ID).to_dict()
    assert len(training_calls) == 1
    assert training_calls[0].device == "cpu"
    assert training_calls[0].resume is False
    run = repository.load_run(RUN_ID)
    assert run.candidate_model_version == f"distilbert_dashboard_{RUN_ID}"
    assert run.candidate_model_digest == candidate_digest
    assert run.evaluation_digest == "a" * 64
    assert repository.verify_artifacts(
        RUN_ID,
        (
            "stages/export.json",
            "stages/dataset.json",
            "stages/training.json",
            "stages/evaluation.json",
            "stages/comparison.json",
            "stages/candidate.json",
        ),
    )
    assert production_marker.read_text(encoding="utf-8") == "unchanged"


def test_native_training_adapter_calls_the_canonical_entrypoint(monkeypatch):
    calls = []

    def fake_run_training(config):
        calls.append(config)
        return "training-run"

    monkeypatch.setattr("ml_model.training.train.run_training", fake_run_training)

    config = object()
    assert pipeline_module._run_native_training(config) == "training-run"
    assert calls == [config]


def test_native_pipeline_uses_authoritative_model_input_contract():
    assert pipeline_module.NATIVE_PREPROCESSING_VERSION == MODEL_INPUT_VERSION


def test_native_pipeline_uses_explicit_v2_training_profile():
    from ml_model.training.config import load_training_config

    assert pipeline_module.NATIVE_PROFILE_PATH.name == "laptop_smoke_v2.toml"
    config = load_training_config(pipeline_module.NATIVE_PROFILE_PATH)

    assert config.dataset_version == "v3_907k_cleaned_model_input_v2"
    assert config.preprocessing_version == MODEL_INPUT_VERSION


def test_native_pipeline_rejects_changed_dataset_identity_on_retry(tmp_path, monkeypatch):
    root = tmp_path / "runs"
    project_root = tmp_path / "project"
    repository = RetrainingRunArtifactRepository(root, clock=lambda: NOW)
    run_dir = _prepare_run_artifacts(repository, root, monkeypatch)
    repository.mark_run_prepared(RUN_ID)
    claimed = repository.claim_next(worker_id="native-worker", now=NOW)
    assert claimed is not None

    repository.update_run_metadata(
        RUN_ID,
        worker_id="native-worker",
        dataset_version="dashboard-prior-snapshot",
        dataset_digest="a" * 64,
    )
    dataset_dir = run_dir / "dataset"
    dataset_digest = compute_content_digest(dataset_dir)
    assert dataset_digest != "a" * 64

    monkeypatch.setattr(
        pipeline_module,
        "_load_export",
        lambda **_: ({"status": "READY"}, ()),
    )
    monkeypatch.setattr(
        pipeline_module,
        "_load_existing_dataset",
        lambda **_: SimpleNamespace(
            dataset_dir=dataset_dir,
            dataset_version="dashboard-test-snapshot",
            manifest={
                "manifest_sha256": "f" * 64,
                "row_counts": {"train": 1, "validation": 1, "test": 1},
                "historical_data_unchanged": True,
            },
        ),
    )

    def fail_if_training_starts(_config):
        raise PipelineFailure(
            "TRAINING_SHOULD_NOT_START",
            retryable=False,
            message="dataset identity was not checked",
        )

    monkeypatch.setattr(pipeline_module, "_run_native_training", fail_if_training_starts)

    with pytest.raises(PipelineFailure) as failure:
        NativeDashboardPipeline(project_root=project_root).execute(
            repository.load_run(RUN_ID), repository, lambda: None
        )

    assert failure.value.code == "NATIVE_DATASET_IDENTITY_CHANGED"


def test_native_pipeline_rejects_changed_training_identity_on_retry(tmp_path, monkeypatch):
    root = tmp_path / "runs"
    project_root = tmp_path / "project"
    repository = RetrainingRunArtifactRepository(root, clock=lambda: NOW)
    run_dir = _prepare_run_artifacts(repository, root, monkeypatch)
    repository.mark_run_prepared(RUN_ID)
    claimed = repository.claim_next(worker_id="native-worker", now=NOW)
    assert claimed is not None

    dataset_dir = run_dir / "dataset"
    dataset_digest = compute_content_digest(dataset_dir)
    repository.update_run_metadata(
        RUN_ID,
        worker_id="native-worker",
        dataset_version="dashboard-test-snapshot",
        dataset_digest=dataset_digest,
    )
    training_source = run_dir / "training" / "distilbert" / "loss_weighted_ce" / "seed_0042"
    (training_source / "checkpoint").mkdir(parents=True)
    for name in (
        "config_metadata.json",
        "summary_metrics.json",
        "per_class_metrics.json",
        "calibration.json",
    ):
        (training_source / name).write_text("{}\n", encoding="utf-8")
    (
        training_source
        / "checkpoint"
        / "best_distilbert_weighted_ce_seed0042.pt"
    ).write_bytes(b"checkpoint")
    repository.publish_json_artifact(
        RUN_ID,
        "stages/training.json",
        {
            "stage": "training",
            "training_output_digest": "b" * 64,
        },
        stage="training",
        worker_id="native-worker",
    )

    monkeypatch.setattr(
        pipeline_module,
        "_load_export",
        lambda **_: ({"status": "READY"}, ()),
    )
    monkeypatch.setattr(
        pipeline_module,
        "_load_existing_dataset",
        lambda **_: SimpleNamespace(
            dataset_dir=dataset_dir,
            dataset_version="dashboard-test-snapshot",
            manifest={
                "manifest_sha256": "f" * 64,
                "row_counts": {"train": 1, "validation": 1, "test": 1},
                "historical_data_unchanged": True,
            },
        ),
    )
    monkeypatch.setattr(
        pipeline_module,
        "_training_config_for_run",
        lambda **_: SimpleNamespace(
            to_dict=lambda: {},
            seeds=(42,),
            device="cpu",
            precision="full",
            max_train_samples=None,
            max_validation_samples=None,
            max_test_samples=None,
        ),
    )

    with pytest.raises(PipelineFailure) as failure:
        NativeDashboardPipeline(project_root=project_root).execute(
            repository.load_run(RUN_ID), repository, lambda: None
        )

    assert failure.value.code == "NATIVE_TRAINING_IDENTITY_CHANGED"


@pytest.mark.parametrize(
    "candidate_model_version",
    [f"distilbert_dashboard_{RUN_ID}", "distilbert_other"],
)
def test_native_pipeline_rejects_changed_candidate_identity_on_retry(
    tmp_path, monkeypatch, candidate_model_version
):
    run_dir = tmp_path / RUN_ID
    training_source = run_dir / "training" / "source"
    training_source.mkdir(parents=True)
    config_path = training_source / "config_metadata.json"
    config_path.write_text(
        json.dumps(
            {
                "dataset_version": "dashboard-test-snapshot",
                "preprocessing_version": MODEL_INPUT_VERSION,
            }
        ),
        encoding="utf-8",
    )
    summary_path = training_source / "summary_metrics.json"
    summary_path.write_text("{}\n", encoding="utf-8")
    per_class_path = training_source / "per_class_metrics.json"
    per_class_path.write_text("[]\n", encoding="utf-8")
    calibration_path = training_source / "calibration.json"
    calibration_path.write_text("{}\n", encoding="utf-8")
    checkpoint_path = training_source / "checkpoint.pt"
    checkpoint_path.write_bytes(b"checkpoint")

    candidate_dir = run_dir / "candidate_model"
    candidate_dir.mkdir(parents=True)
    (candidate_dir / "serving_manifest.json").write_text(
        json.dumps({"model_version": candidate_model_version}),
        encoding="utf-8",
    )
    (candidate_dir / "candidate.bin").write_bytes(b"candidate")
    actual_digest = compute_content_digest(candidate_dir)
    assert actual_digest != "a" * 64

    monkeypatch.setattr(
        pipeline_module,
        "_load_training_source",
        lambda _training_dir: {
            "config_metadata.json": config_path,
            "summary_metrics.json": summary_path,
            "per_class_metrics.json": per_class_path,
            "calibration.json": calibration_path,
            "checkpoint": checkpoint_path,
        },
    )
    monkeypatch.setattr(
        "ml_model.export.promote_final_training_run.validate_native_promotion_metadata",
        lambda _metadata: None,
    )
    monkeypatch.setattr(
        "ml_model.export.package_serving_artifact.load_training_summary",
        lambda _path: SimpleNamespace(metrics={}, raw_bytes=b""),
    )
    monkeypatch.setattr(
        "ml_model.export.promote_final_training_run.extract_calibration_temperature",
        lambda _payload: 1.0,
    )

    with pytest.raises(PipelineFailure) as failure:
        pipeline_module._build_candidate_artifact(
            run=replace(_record(), candidate_model_digest="a" * 64),
            run_dir=run_dir,
            training_dir=run_dir / "training",
            project_root=tmp_path,
            dataset_version="dashboard-test-snapshot",
        )

    assert failure.value.code == "NATIVE_CANDIDATE_IDENTITY_CHANGED"


def test_native_worker_missing_prepared_export_is_terminal_and_bounded(tmp_path):
    root = tmp_path / "runs"
    repository = RetrainingRunArtifactRepository(root, clock=lambda: NOW)
    repository.create_or_get_run(_record())

    result = DashboardWorker(
        repository,
        root=root,
        pipeline=NativeDashboardPipeline(project_root=tmp_path),
        smoke=False,
        worker_id="native-worker",
        clock=lambda: NOW,
    ).run_once()

    assert result.exit_code == EXIT_TERMINAL_FAILURE
    run = repository.load_run(RUN_ID)
    assert run.state is RunState.FAILED
    assert run.error_code == "EXPORT_ARTIFACT_MISSING"
    assert "traceback" not in (run.error_message or "").lower()
