from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ml_model.preprocessing.model_input import MODEL_INPUT_HASH_POLICY
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
from web_app.infrastructure.retraining_staging_adapter import (
    LocalStagingAdapter,
    StagingDeploymentRecord,
    compute_artifact_digest,
)

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
RUN_ID = "retrain-20260811T120000Z-000000000001"
LABELS = ["Code Injection", "Normal", "Other Attacks", "SQL Injection"]


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _make_serving_artifact(
    root: Path, version: str, *, directory_name: str | None = None
) -> Path:
    artifact = root / (directory_name or version)
    artifact.mkdir(parents=True)
    config_used = b'{"preprocessing_version":"model-input-v2-redacted"}\n'
    checkpoint = b"safe checkpoint fixture"
    (artifact / "config_used.json").write_bytes(config_used)
    (artifact / "best_distilbert_ckpt.pt").write_bytes(checkpoint)
    (artifact / "config.json").write_text("{}\n", encoding="utf-8")
    (artifact / "tokenizer_config.json").write_text("{}\n", encoding="utf-8")
    (artifact / "tokenizer.json").write_text("{}\n", encoding="utf-8")
    (artifact / "model.safetensors").write_bytes(b"model weights fixture")
    (artifact / "serving_manifest.json").write_text(
        json.dumps(
            {
                "model_version": version,
                "run_dir_name": version,
                "model_key": "distilbert",
                "preprocessing_version": "model-input-v2-redacted",
                "model_input_hash_policy": MODEL_INPUT_HASH_POLICY,
                "architecture": "distilbert_sequence_classification",
                "architecture_family": "huggingface_sequence_classifier",
                "head_type": "hf_sequence_classification_head",
                "model_class": "DistilBertForSequenceClassification",
                "model_revision": "fixture-revision",
                "label_names": LABELS,
                "num_labels": len(LABELS),
                "local_reload_verified": True,
                "checkpoint_file": "best_distilbert_ckpt.pt",
                "checkpoint_sha256": _sha256(checkpoint),
                "config_used_file": "config_used.json",
                "config_used_sha256": _sha256(config_used),
            }
        ),
        encoding="utf-8",
    )
    return artifact


def _record(
    *,
    state: RunState = RunState.APPROVED,
    candidate_version: str = "candidate-v1",
    candidate_digest: str,
    active_version: str = "active-v1",
    active_digest: str = "d" * 64,
) -> RetrainingRunRecord:
    return RetrainingRunRecord(
        run_id=RUN_ID,
        state=state,
        stage=state.value,
        attempt=1,
        retry_count=0,
        max_retries=2,
        created_at=NOW,
        updated_at=NOW,
        heartbeat_at=None,
        trigger="manual",
        requested_by="admin-1",
        requested_timezone="Asia/Manila",
        input_fingerprint="a" * 64,
        source_review_revisions=("1:1",),
        source_dataset_version="dashboard-dataset-v1",
        source_dataset_digest="b" * 64,
        pipeline_fingerprint="c" * 64,
        active_model_version=active_version,
        active_model_digest=active_digest,
        approved_sample_count=2,
        dataset_version="dashboard-dataset-v1",
        dataset_digest="b" * 64,
        candidate_model_version=candidate_version,
        candidate_model_digest=candidate_digest,
        evaluation_digest="0" * 64,
    )


class NoopDependency:
    pass


def _comparison(
    active_digest: str,
    candidate_digest: str,
    *,
    evaluation_digest: str,
    status: str = "PASS",
) -> dict:
    return {
        "overall_status": status,
        "decision_allowed": status == "PASS",
        "provenance": {
            "dataset_version": "dashboard-dataset-v1",
            "dataset_digest": "b" * 64,
            "evaluation_digest": evaluation_digest,
            "active_model_digest": active_digest,
            "candidate_model_digest": candidate_digest,
        },
        "gate_results": {
            "active_model_binding": {"status": status},
            "evaluation_binding": {"status": status},
            "evidence": {"status": status},
            "security_regression": {"status": status},
            "quality": {"status": status},
            "improvement": {"status": status},
        },
    }


def _make_control(
    tmp_path: Path,
    *,
    loader=None,
    active_version: str = "active-v1",
    active_digest: str | None = None,
    candidate_version: str = "candidate-v1",
    comparison_status: str = "PASS",
    state: RunState = RunState.APPROVED,
):
    run_root = tmp_path / "runs"
    staging_root = tmp_path / "model_registry" / "staging"
    archive_root = tmp_path / "model_registry" / "archive"
    candidate_fixture = _make_serving_artifact(
        tmp_path / "candidate-fixture", candidate_version
    )
    candidate_digest = compute_artifact_digest(candidate_fixture)
    active_fixture = _make_serving_artifact(staging_root, active_version)
    active_digest = active_digest or compute_artifact_digest(active_fixture)
    adapter = LocalStagingAdapter(
        staging_root=staging_root,
        archive_root=archive_root,
        load_validator=loader or (lambda _path, expected: expected),
        reload_callback=loader or (lambda _path, expected: expected),
        clock=lambda: NOW,
    )
    repository = RetrainingRunArtifactRepository(run_root, clock=lambda: NOW)
    repository.create_or_get_run(
        _record(
            state=state,
            candidate_version=candidate_version,
            candidate_digest=candidate_digest,
            active_version=active_version,
            active_digest=active_digest,
        )
    )
    candidate_source = run_root / RUN_ID / "candidate_model"
    shutil.copytree(candidate_fixture, candidate_source)
    evaluation = repository.publish_json_artifact(
        RUN_ID,
        "stages/evaluation.json",
        {"evidence_status": "NATIVE", "status": "PASS"},
        stage="evaluation",
    )
    repository.update_run_metadata(RUN_ID, evaluation_digest=evaluation["sha256"])
    repository.publish_json_artifact(
        RUN_ID,
        "stages/comparison.json",
        _comparison(
            active_digest,
            candidate_digest,
            evaluation_digest=evaluation["sha256"],
            status=comparison_status,
        ),
        stage="evidence_comparison",
    )
    control = RetrainingControlUseCase(
        NoopDependency(),
        repository,
        NoopDependency(),
        NoopDependency(),
        active_model_version=active_version,
        active_model_digest=active_digest,
        active_model_input_version="model-input-v2-redacted",
        staging_adapter=adapter,
        clock=lambda: NOW,
    )
    return (
        control,
        repository,
        staging_root,
        archive_root,
        candidate_digest,
        candidate_source,
        adapter,
    )


def test_deploy_requires_approval_passing_gate_and_current_active_binding(
    tmp_path: Path,
):
    control, repository, _, _, _, _, adapter = _make_control(
        tmp_path, state=RunState.HELD
    )
    with pytest.raises(RetrainingControlError, match="approved"):
        control.deploy(
            run_id=RUN_ID,
            expected_candidate_version="candidate-v1",
            actor_id="admin-1",
            actor_role="ADMIN",
        )

    control, repository, _, _, _, _, adapter = _make_control(
        tmp_path / "stale", state=RunState.APPROVED
    )
    stale = RetrainingControlUseCase(
        NoopDependency(),
        repository,
        NoopDependency(),
        NoopDependency(),
        active_model_version="active-v2",
        active_model_digest="e" * 64,
        active_model_input_version="model-input-v2-redacted",
        staging_adapter=adapter,
        clock=lambda: NOW,
    )
    with pytest.raises(RetrainingControlError, match="active model"):
        stale.deploy(
            run_id=RUN_ID,
            expected_candidate_version="candidate-v1",
            actor_id="admin-1",
            actor_role="ADMIN",
        )


def test_gate_failure_and_tampered_candidate_are_refused_without_staging_change(
    tmp_path: Path,
):
    control, repository, staging_root, _, candidate_digest, _, _ = _make_control(
        tmp_path, comparison_status="FAIL"
    )
    with pytest.raises(RetrainingControlError, match="gate"):
        control.deploy(
            run_id=RUN_ID,
            expected_candidate_version="candidate-v1",
            actor_id="admin-1",
            actor_role="ADMIN",
        )
    assert repository.load_run(RUN_ID).state is RunState.APPROVED
    assert (staging_root / "active-v1").is_dir()
    assert not (staging_root / "candidate-v1").exists()

    control, repository, staging_root, _, _, candidate_source, _ = _make_control(
        tmp_path / "tampered"
    )
    (candidate_source / "model.safetensors").write_bytes(b"tampered")
    with pytest.raises(RetrainingControlError, match="integrity"):
        control.deploy(
            run_id=RUN_ID,
            expected_candidate_version="candidate-v1",
            actor_id="admin-1",
            actor_role="ADMIN",
        )
    assert repository.load_run(RUN_ID).state is RunState.APPROVED
    assert (staging_root / "active-v1").is_dir()


def test_successful_local_staging_deploy_and_rollback_reload_known_good_model(
    tmp_path: Path,
):
    loaded: list[str] = []

    def loader(path: Path, expected_version: str) -> str:
        loaded.append(path.name)
        return expected_version

    control, repository, staging_root, archive_root, candidate_digest, _, _ = (
        _make_control(tmp_path, loader=loader)
    )
    deployed = control.deploy(
        run_id=RUN_ID,
        expected_candidate_version="candidate-v1",
        actor_id="admin-1",
        actor_role="ADMIN",
    )
    assert deployed.state is RunState.DEPLOYED
    assert (staging_root / "candidate-v1").is_dir()
    assert not (staging_root / "active-v1").exists()
    assert loaded[:2] == ["candidate_model", "candidate-v1"]
    assert any(path.is_dir() for path in archive_root.iterdir())
    events = repository.read_events(RUN_ID)
    assert events[-1]["code"] == "DEPLOY_SUCCEEDED"
    started = next(event for event in events if event["code"] == "DEPLOY_STARTED")
    assert started["candidate_model_version"] == "candidate-v1"
    assert started["candidate_model_digest"] == candidate_digest
    assert started["active_model_digest"] == compute_artifact_digest(
        archive_root / next(path.name for path in archive_root.iterdir())
    )
    assert started["previous_staging_version"] == "active-v1"
    assert started["actor_id"] == "admin-1"

    rolled_back = control.rollback(
        run_id=RUN_ID,
        previous_staging_version="active-v1",
        reason="Restore the known-good staging version.",
        actor_id="admin-1",
        actor_role="ADMIN",
    )
    assert rolled_back.state is RunState.ROLLED_BACK
    assert (staging_root / "active-v1").is_dir()
    assert not (staging_root / "candidate-v1").exists()
    assert loaded[-1] == "active-v1"
    assert repository.read_events(RUN_ID)[-1]["code"] == "ROLLBACK_SUCCEEDED"
    assert candidate_digest


def test_candidate_load_failure_restores_previous_staging_and_marks_rolled_back(
    tmp_path: Path,
):
    def loader(path: Path, expected_version: str) -> str:
        if path.name == "candidate-v1":
            raise RuntimeError("fixture load failure")
        return expected_version

    control, repository, staging_root, _, _, _, _ = _make_control(
        tmp_path, loader=loader
    )
    with pytest.raises(RetrainingControlError, match="load"):
        control.deploy(
            run_id=RUN_ID,
            expected_candidate_version="candidate-v1",
            actor_id="admin-1",
            actor_role="ADMIN",
        )

    assert repository.load_run(RUN_ID).state is RunState.ROLLED_BACK
    assert (staging_root / "active-v1").is_dir()
    assert not (staging_root / "candidate-v1").exists()


def test_deploy_audit_failure_enters_recovery_and_can_rollback_after_restart_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    control, repository, staging_root, _, _, _, _ = _make_control(tmp_path)
    original_publish = repository.publish_json_artifact

    def fail_after_activation(run_id, artifact_path, payload, **kwargs):
        if artifact_path == "staging/deployment.json":
            raise ArtifactRepositoryError("simulated post-activation audit failure")
        return original_publish(run_id, artifact_path, payload, **kwargs)

    monkeypatch.setattr(repository, "publish_json_artifact", fail_after_activation)

    with pytest.raises(RetrainingControlError, match="recovery"):
        control.deploy(
            run_id=RUN_ID,
            expected_candidate_version="candidate-v1",
            actor_id="admin-1",
            actor_role="ADMIN",
        )

    assert repository.load_run(RUN_ID).state is RunState.RECOVERY_REQUIRED
    pointer = json.loads((staging_root / "active_model.json").read_text())
    assert pointer["model_version"] == "candidate-v1"

    rolled_back = control.rollback(
        run_id=RUN_ID,
        previous_staging_version="active-v1",
        reason="Reconcile the local staging state.",
        actor_id="admin-1",
        actor_role="ADMIN",
    )

    assert rolled_back.state is RunState.ROLLED_BACK
    assert (
        json.loads((staging_root / "active_model.json").read_text())["model_version"]
        == "active-v1"
    )


def test_unclean_deploy_before_activation_is_reconciled_after_restart(
    tmp_path: Path,
):
    control, repository, staging_root, archive_root, _, _, adapter = _make_control(
        tmp_path
    )
    active_digest = repository.load_run(RUN_ID).active_model_digest
    adapter._write_active_pointer(
        model_version="active-v1",
        artifact_digest=active_digest,
        directory=staging_root / "active-v1",
        preprocessing_version="model-input-v2-redacted",
    )

    def terminate_before_activation(_plan):
        raise SystemExit("simulated process termination")

    adapter.deploy = terminate_before_activation
    with pytest.raises(SystemExit):
        control.deploy(
            run_id=RUN_ID,
            expected_candidate_version="candidate-v1",
            actor_id="admin-1",
            actor_role="ADMIN",
        )

    restarted_adapter = LocalStagingAdapter(
        staging_root=staging_root,
        archive_root=archive_root,
        load_validator=lambda _path, expected: expected,
        reload_callback=lambda _path, expected: expected,
        clock=lambda: NOW,
    )
    restarted = RetrainingControlUseCase(
        NoopDependency(),
        repository,
        NoopDependency(),
        NoopDependency(),
        active_model_version="active-v1",
        active_model_digest=active_digest,
        active_model_input_version="model-input-v2-redacted",
        staging_adapter=restarted_adapter,
        clock=lambda: NOW,
    )

    reconciled = restarted.rollback(
        run_id=RUN_ID,
        previous_staging_version="active-v1",
        reason="Reconcile an interrupted local deployment.",
        actor_id="admin-1",
        actor_role="ADMIN",
    )

    assert reconciled.state is RunState.APPROVED
    assert restarted_adapter.read_active_pointer().model_version == "active-v1"
    assert not (staging_root / "candidate-v1").exists()


def test_unreadable_recovery_events_fail_closed_after_interrupted_deploy(
    tmp_path: Path,
):
    control, repository, staging_root, archive_root, _, _, adapter = _make_control(
        tmp_path
    )
    active_digest = repository.load_run(RUN_ID).active_model_digest
    adapter._write_active_pointer(
        model_version="active-v1",
        artifact_digest=active_digest,
        directory=staging_root / "active-v1",
        preprocessing_version="model-input-v2-redacted",
    )

    def terminate_before_activation(_plan):
        raise SystemExit("simulated process termination")

    adapter.deploy = terminate_before_activation
    with pytest.raises(SystemExit):
        control.deploy(
            run_id=RUN_ID,
            expected_candidate_version="candidate-v1",
            actor_id="admin-1",
            actor_role="ADMIN",
        )

    restarted_adapter = LocalStagingAdapter(
        staging_root=staging_root,
        archive_root=archive_root,
        load_validator=lambda _path, expected: expected,
        reload_callback=lambda _path, expected: expected,
        clock=lambda: NOW,
    )
    restarted = RetrainingControlUseCase(
        NoopDependency(),
        repository,
        NoopDependency(),
        NoopDependency(),
        active_model_version="active-v1",
        active_model_digest=active_digest,
        active_model_input_version="model-input-v2-redacted",
        staging_adapter=restarted_adapter,
        clock=lambda: NOW,
    )

    def unreadable_events(_run_id):
        raise ArtifactRepositoryError("simulated event stream failure")

    repository.read_events = unreadable_events
    with pytest.raises(RetrainingControlError, match="recovery"):
        restarted.rollback(
            run_id=RUN_ID,
            previous_staging_version="active-v1",
            reason="Recover after an interrupted deployment.",
            actor_id="admin-1",
            actor_role="ADMIN",
        )

    assert repository.load_run(RUN_ID).state is RunState.RECOVERY_REQUIRED


def test_unclean_deploy_after_activation_can_rollback_after_restart(
    tmp_path: Path,
):
    control, repository, staging_root, archive_root, _, _, adapter = _make_control(
        tmp_path
    )
    active_digest = repository.load_run(RUN_ID).active_model_digest
    adapter._write_active_pointer(
        model_version="active-v1",
        artifact_digest=active_digest,
        directory=staging_root / "active-v1",
        preprocessing_version="model-input-v2-redacted",
    )
    original_deploy = adapter.deploy

    def activate_then_terminate(plan):
        original_deploy(plan)
        raise SystemExit("simulated process termination")

    adapter.deploy = activate_then_terminate
    with pytest.raises(SystemExit):
        control.deploy(
            run_id=RUN_ID,
            expected_candidate_version="candidate-v1",
            actor_id="admin-1",
            actor_role="ADMIN",
        )

    restarted_adapter = LocalStagingAdapter(
        staging_root=staging_root,
        archive_root=archive_root,
        load_validator=lambda _path, expected: expected,
        reload_callback=lambda _path, expected: expected,
        clock=lambda: NOW,
    )
    restarted = RetrainingControlUseCase(
        NoopDependency(),
        repository,
        NoopDependency(),
        NoopDependency(),
        active_model_version="candidate-v1",
        active_model_digest=compute_artifact_digest(staging_root / "candidate-v1"),
        active_model_input_version="model-input-v2-redacted",
        staging_adapter=restarted_adapter,
        clock=lambda: NOW,
    )

    rolled_back = restarted.rollback(
        run_id=RUN_ID,
        previous_staging_version="active-v1",
        reason="Restore the known-good model after an interrupted deployment.",
        actor_id="admin-1",
        actor_role="ADMIN",
    )

    assert rolled_back.state is RunState.ROLLED_BACK
    assert restarted_adapter.read_active_pointer().model_version == "active-v1"
    assert (staging_root / "active-v1").is_dir()
    assert not (staging_root / "candidate-v1").exists()


def test_unclean_rollback_after_physical_restore_is_reconciled_after_restart(
    tmp_path: Path,
):
    control, repository, staging_root, archive_root, _, _, adapter = _make_control(
        tmp_path
    )
    control.deploy(
        run_id=RUN_ID,
        expected_candidate_version="candidate-v1",
        actor_id="admin-1",
        actor_role="ADMIN",
    )
    original_rollback = adapter.rollback

    def restore_then_terminate(record, *, requested_previous_version):
        original_rollback(
            record, requested_previous_version=requested_previous_version
        )
        raise SystemExit("simulated process termination")

    adapter.rollback = restore_then_terminate
    with pytest.raises(SystemExit):
        control.rollback(
            run_id=RUN_ID,
            previous_staging_version="active-v1",
            reason="Restore the known-good model before the process exits.",
            actor_id="admin-1",
            actor_role="ADMIN",
        )

    restarted_adapter = LocalStagingAdapter(
        staging_root=staging_root,
        archive_root=archive_root,
        load_validator=lambda _path, expected: expected,
        reload_callback=lambda _path, expected: expected,
        clock=lambda: NOW,
    )
    restarted = RetrainingControlUseCase(
        NoopDependency(),
        repository,
        NoopDependency(),
        NoopDependency(),
        active_model_version="active-v1",
        active_model_digest=repository.load_run(RUN_ID).active_model_digest,
        active_model_input_version="model-input-v2-redacted",
        staging_adapter=restarted_adapter,
        clock=lambda: NOW,
    )

    reconciled = restarted.rollback(
        run_id=RUN_ID,
        previous_staging_version="active-v1",
        reason="Finalize the interrupted rollback record.",
        actor_id="admin-1",
        actor_role="ADMIN",
    )

    assert reconciled.state is RunState.ROLLED_BACK
    assert restarted_adapter.read_active_pointer().model_version == "active-v1"
    assert not (staging_root / "candidate-v1").exists()


def test_deploy_pointer_publication_termination_keeps_previous_pointer_valid(
    tmp_path: Path,
):
    _, repository, staging_root, _, _, _, adapter = _make_control(tmp_path)
    active_digest = repository.load_run(RUN_ID).active_model_digest
    adapter._write_active_pointer(
        model_version="active-v1",
        artifact_digest=active_digest,
        directory=staging_root / "active-v1",
        preprocessing_version="model-input-v2-redacted",
    )
    plan = adapter.prepare_deployment(
        artifact_root=tmp_path / "runs",
        run_id=RUN_ID,
        candidate_model_version="candidate-v1",
        candidate_model_digest=repository.load_run(RUN_ID).candidate_model_digest,
        active_model_version="active-v1",
        active_model_digest=active_digest,
        expected_preprocessing_version="model-input-v2-redacted",
    )
    original_write = adapter._write_active_pointer

    def terminate_candidate_pointer(*, model_version, **kwargs):
        if model_version == "candidate-v1":
            raise SystemExit("simulated pointer publication termination")
        return original_write(model_version=model_version, **kwargs)

    adapter._write_active_pointer = terminate_candidate_pointer
    with pytest.raises(SystemExit):
        adapter.deploy(plan)

    pointer = adapter.read_active_pointer()
    assert pointer.model_version == "active-v1"
    assert (staging_root / "active-v1").is_dir()
    assert (staging_root / "candidate-v1").is_dir()


def test_rollback_pointer_publication_termination_keeps_candidate_pointer_valid(
    tmp_path: Path,
):
    control, repository, staging_root, archive_root, _, _, adapter = _make_control(
        tmp_path
    )
    active_digest = repository.load_run(RUN_ID).active_model_digest
    adapter._write_active_pointer(
        model_version="active-v1",
        artifact_digest=active_digest,
        directory=staging_root / "active-v1",
        preprocessing_version="model-input-v2-redacted",
    )
    control.deploy(
        run_id=RUN_ID,
        expected_candidate_version="candidate-v1",
        actor_id="admin-1",
        actor_role="ADMIN",
    )
    deployment = StagingDeploymentRecord.from_payload(
        json.loads(
            (tmp_path / "runs" / RUN_ID / "staging" / "deployment.json").read_text()
        )
    )
    original_write = adapter._write_active_pointer

    def terminate_previous_pointer(*, model_version, **kwargs):
        if model_version == "active-v1":
            raise SystemExit("simulated pointer publication termination")
        return original_write(model_version=model_version, **kwargs)

    adapter._write_active_pointer = terminate_previous_pointer
    with pytest.raises(SystemExit):
        adapter.rollback(
            deployment,
            requested_previous_version="active-v1",
        )

    pointer = adapter.read_active_pointer()
    assert pointer.model_version == "candidate-v1"
    assert (staging_root / "candidate-v1").is_dir()
    assert (staging_root / "active-v1").is_dir()


def test_rollback_audit_failure_enters_recovery_and_reconciles_known_good_pointer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    control, repository, staging_root, _, _, _, _ = _make_control(tmp_path)
    control.deploy(
        run_id=RUN_ID,
        expected_candidate_version="candidate-v1",
        actor_id="admin-1",
        actor_role="ADMIN",
    )
    original_publish = repository.publish_json_artifact

    def fail_after_rollback(run_id, artifact_path, payload, **kwargs):
        if artifact_path == "staging/rollback-result.json":
            raise ArtifactRepositoryError("simulated rollback audit failure")
        return original_publish(run_id, artifact_path, payload, **kwargs)

    monkeypatch.setattr(repository, "publish_json_artifact", fail_after_rollback)

    with pytest.raises(RetrainingControlError, match="recovery"):
        control.rollback(
            run_id=RUN_ID,
            previous_staging_version="active-v1",
            reason="Restore the known-good local staging version.",
            actor_id="admin-1",
            actor_role="ADMIN",
        )

    assert repository.load_run(RUN_ID).state is RunState.RECOVERY_REQUIRED
    assert (
        json.loads((staging_root / "active_model.json").read_text())["model_version"]
        == "active-v1"
    )

    monkeypatch.setattr(repository, "publish_json_artifact", original_publish)
    reconciled = control.rollback(
        run_id=RUN_ID,
        previous_staging_version="active-v1",
        reason="Finalize the recoverable rollback record.",
        actor_id="admin-1",
        actor_role="ADMIN",
    )

    assert reconciled.state is RunState.ROLLED_BACK


def test_staging_adapter_rejects_production_paths(tmp_path: Path):
    with pytest.raises(ValueError, match="production"):
        LocalStagingAdapter(
            staging_root=tmp_path / "model_registry" / "production",
            archive_root=tmp_path / "archive",
        )
