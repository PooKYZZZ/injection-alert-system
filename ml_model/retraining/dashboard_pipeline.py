"""Stage-oriented local dashboard pipeline adapters.

The smoke adapter is deliberately honest: it exercises queue/artifact
ordering and marks native training/evaluation evidence ``NOT_RUN``. The native
adapter runs the fixed laptop profile only inside the existing isolated worker
boundary and leaves activation to the explicit staging control plane.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ml_model.preprocessing.model_input import MODEL_INPUT_VERSION
from ml_model.project_paths import PROJECT_ROOT
from ml_model.retraining.dashboard_contracts import (
    CANONICAL_LABELS,
    ComparisonResponse,
    EvaluationProvenance,
    EvidenceStatus,
    GateStatus,
    MetricKind,
    ModelReference,
    RunState,
    canonical_json,
    get_run_artifact_directory,
)
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    RetrainingRunArtifactRepository,
    RetrainingRunRecord,
    InvalidRunTransition,
)

NATIVE_PROFILE_PATH = (
    Path(__file__).resolve().parents[1]
    / "configs"
    / "training"
    / "laptop_smoke_v2.toml"
)
# The dashboard export, dataset snapshot, training profile, evaluation, and
# candidate manifest must share the same serving contract. Keep this alias for
# the pipeline's existing metadata field names, but source it from the
# authoritative model-input module rather than duplicating a version string.
NATIVE_PREPROCESSING_VERSION = MODEL_INPUT_VERSION
NATIVE_EVALUATION_SPLIT = "frozen_test"
NATIVE_MODEL_KEY = "distilbert"
NATIVE_MODEL_VERSION_PREFIX = "distilbert_dashboard_"


class PipelineFailure(RuntimeError):
    """Bounded pipeline failure classified by the worker for recovery."""

    def __init__(self, code: str, *, retryable: bool, message: str | None = None):
        self.code = code
        self.retryable = retryable
        self.safe_message = (
            (message or code).replace("\r", " ").replace("\n", " ")[:500]
        )
        super().__init__(self.safe_message)


@dataclass(frozen=True, slots=True)
class PipelineResult:
    terminal_state: RunState
    evidence_status: str


Heartbeat = Callable[[], None]


class SmokeDashboardPipeline:
    """Publish inspectable stage artifacts without native quality claims."""

    def execute(
        self,
        run: RetrainingRunRecord,
        repository: RetrainingRunArtifactRepository,
        heartbeat: Heartbeat,
    ) -> PipelineResult:
        worker_id = run.worker_id
        try:
            heartbeat()
            repository.publish_json_artifact(
                run.run_id,
                "stages/export.json",
                {
                    "stage": "export",
                    "status": "CONTROLLED_SMOKE",
                    "approved_sample_count": run.approved_sample_count,
                    "source_review_count": len(run.source_review_revisions),
                },
                stage="export",
                worker_id=worker_id,
            )
            repository.complete_stage(
                run.run_id,
                next_state=RunState.DATASET_VALIDATED,
                required_artifacts=("stages/export.json",),
                worker_id=worker_id,
                stage="dataset_validated",
            )
            heartbeat()
            repository.publish_json_artifact(
                run.run_id,
                "stages/dataset.json",
                {
                    "stage": "dataset",
                    "status": "CONTROLLED_SMOKE",
                    "dataset_version": f"dashboard-smoke-{run.run_id}",
                    "source_dataset_version": run.source_dataset_version,
                    "preprocessing_version": "NOT_RUN",
                },
                stage="dataset",
                worker_id=worker_id,
            )
            repository.complete_stage(
                run.run_id,
                next_state=RunState.TRAINING,
                required_artifacts=("stages/dataset.json",),
                worker_id=worker_id,
                stage="training",
            )
            heartbeat()
            repository.publish_json_artifact(
                run.run_id,
                "stages/training.json",
                {
                    "stage": "training",
                    "training_status": "NOT_RUN",
                    "model_quality_conclusion": "NOT_PERMITTED",
                },
                stage="training",
                worker_id=worker_id,
            )
            repository.complete_stage(
                run.run_id,
                next_state=RunState.EVALUATING,
                required_artifacts=("stages/training.json",),
                worker_id=worker_id,
                stage="evaluating",
            )
            heartbeat()
            repository.publish_json_artifact(
                run.run_id,
                "stages/evaluation.json",
                {
                    "stage": "evaluation",
                    "evidence_status": "NOT_RUN",
                    "gate_status": "NOT_ENOUGH_EVIDENCE",
                    "native_training_status": "NOT_RUN",
                },
                stage="evaluation",
                worker_id=worker_id,
            )
            repository.publish_json_artifact(
                run.run_id,
                "stages/comparison.json",
                {
                    "stage": "evidence_comparison",
                    "comparison_status": "NOT_RUN",
                    "gate_status": "NOT_ENOUGH_EVIDENCE",
                    "candidate_model_digest": None,
                    "active_model_digest": run.active_model_digest,
                },
                stage="evidence_comparison",
                worker_id=worker_id,
            )
            repository.complete_stage(
                run.run_id,
                next_state=RunState.NOT_ENOUGH_EVIDENCE,
                required_artifacts=(
                    "stages/evaluation.json",
                    "stages/comparison.json",
                ),
                worker_id=worker_id,
                stage="evidence_comparison",
            )
        except PipelineFailure:
            raise
        except Exception as exc:
            raise PipelineFailure(
                "SMOKE_PIPELINE_FAILED",
                retryable=False,
                message=type(exc).__name__,
            ) from exc
        return PipelineResult(
            terminal_state=RunState.NOT_ENOUGH_EVIDENCE,
            evidence_status="NOT_RUN",
        )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("metadata must be a JSON object")
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _validate_manifest_digest(payload: Mapping[str, Any], field: str) -> None:
    recorded = payload.get(field)
    if not isinstance(recorded, str) or len(recorded) != 64:
        raise ValueError(f"{field} is missing")
    without_digest = dict(payload)
    without_digest.pop(field, None)
    if _sha256_bytes(canonical_json(without_digest).encode("utf-8")) != recorded:
        raise ValueError(f"{field} does not match metadata")


def _load_export(
    *,
    run: RetrainingRunRecord,
    run_dir: Path,
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    manifest_path = run_dir / "export" / "export_manifest.json"
    samples_path = run_dir / "export" / "approved_samples.jsonl"
    if not manifest_path.is_file() or not samples_path.is_file():
        raise PipelineFailure(
            "EXPORT_ARTIFACT_MISSING",
            retryable=False,
            message="validated approved-sample export is missing",
        )
    try:
        manifest = _read_json(manifest_path)
        _validate_manifest_digest(manifest, "manifest_sha256")
        if manifest.get("run_id") != run.run_id:
            raise ValueError("export run identity does not match")
        if manifest.get("source_dataset_version") != run.source_dataset_version:
            raise ValueError("export source dataset does not match run")
        if manifest.get("preprocessing_version") != NATIVE_PREPROCESSING_VERSION:
            raise ValueError("export preprocessing identity is unsupported")
        if manifest.get("status") not in {
            "READY",
            "EMPTY",
            "QUARANTINED_FOR_REVIEW",
        }:
            raise ValueError("export status is invalid")
        samples = []
        from ml_model.retraining.dashboard_contracts import ExportedSample

        for line in samples_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            sample_payload = json.loads(line)
            if not isinstance(sample_payload, dict):
                raise ValueError("export sample is invalid")
            samples.append(ExportedSample(**sample_payload))
        if int(manifest.get("row_count", -1)) != len(samples):
            raise ValueError("export row count does not match samples")
        expected_revisions = sorted(
            f"{sample.traffic_log_id}:{sample.review_revision}" for sample in samples
        )
        if expected_revisions != sorted(run.source_review_revisions):
            raise ValueError("export review snapshot does not match run")
        if manifest.get("files", {}).get("approved_samples.jsonl") != _sha256_file(
            samples_path
        ):
            raise ValueError("export sample digest does not match manifest")
    except PipelineFailure:
        raise
    except (OSError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise PipelineFailure(
            "EXPORT_ARTIFACT_INVALID",
            retryable=False,
            message="approved-sample export failed validation",
        ) from exc
    return manifest, tuple(samples)


def _load_existing_dataset(
    *,
    dataset_dir: Path,
    run_id: str,
    source_dataset_version: str,
    preprocessing_version: str,
):
    from ml_model.preprocessing.dataset_io import (
        load_dataset_file_manifest,
        validate_dataset_preprocessing,
    )
    from ml_model.retraining.dashboard_dataset import DashboardDatasetResult

    manifest_path = dataset_dir / "dataset_manifest.json"
    if not dataset_dir.is_dir() or not manifest_path.is_file():
        raise ValueError("existing dataset snapshot is incomplete")
    manifest = _read_json(manifest_path)
    _validate_manifest_digest(manifest, "manifest_sha256")
    if manifest.get("run_id") != run_id:
        raise ValueError("dataset run identity does not match")
    if manifest.get("source_dataset_version") != source_dataset_version:
        raise ValueError("dataset source identity does not match")
    if manifest.get("preprocessing_version") != preprocessing_version:
        raise ValueError("dataset preprocessing identity does not match")
    validate_dataset_preprocessing(
        dataset_dir,
        expected_dataset_version=str(manifest.get("dataset_version", "")),
        expected_preprocessing_version=preprocessing_version,
        expected_text_column="combined_payload",
    )
    load_dataset_file_manifest(dataset_dir)
    return DashboardDatasetResult(
        dataset_dir=dataset_dir,
        dataset_version=str(manifest["dataset_version"]),
        manifest=manifest,
    )


def _remove_generated_directory(path: Path, *, run_dir: Path) -> None:
    resolved = path.resolve()
    if resolved.parent != run_dir.resolve() or path.is_symlink():
        raise ValueError("generated run directory is outside the run boundary")
    if path.exists():
        shutil.rmtree(path)


def _read_existing_stage_artifact(
    repository: RetrainingRunArtifactRepository,
    *,
    run_id: str,
    run_dir: Path,
    relative_path: str,
) -> dict[str, Any] | None:
    if not (run_dir / relative_path).exists():
        return None
    return repository.read_json_artifact(run_id, relative_path)


def _find_training_source(training_dir: Path) -> dict[str, Path] | None:
    candidates: list[dict[str, Path]] = []
    for config_path in sorted(training_dir.rglob("config_metadata.json")):
        source_dir = config_path.parent
        checkpoint_paths = sorted(
            (source_dir / "checkpoint").glob(
                "best_distilbert_weighted_ce_seed*.pt"
            )
        )
        required = {
            "config_metadata.json": config_path,
            "summary_metrics.json": source_dir / "summary_metrics.json",
            "per_class_metrics.json": source_dir / "per_class_metrics.json",
            "calibration.json": source_dir / "calibration.json",
            "checkpoint": checkpoint_paths[0] if len(checkpoint_paths) == 1 else None,
        }
        if all(path is not None and path.is_file() for path in required.values()):
            candidates.append({key: path for key, path in required.items() if path})
    if len(candidates) > 1:
        raise ValueError("training output contains multiple native model sources")
    return candidates[0] if candidates else None


def _load_training_source(training_dir: Path) -> dict[str, Path]:
    source = _find_training_source(training_dir)
    if source is None:
        raise PipelineFailure(
            "NATIVE_TRAINING_OUTPUT_INCOMPLETE",
            retryable=True,
            message="native training output is incomplete",
        )
    return source


def _training_config_for_run(
    *,
    dataset_dir: Path,
    dataset_version: str,
    training_dir: Path,
    profile_path: Path,
):
    from dataclasses import replace as dataclass_replace

    from ml_model.training.config import load_training_config

    config = load_training_config(profile_path)
    if config.preprocessing_version != NATIVE_PREPROCESSING_VERSION:
        raise PipelineFailure(
            "NATIVE_PROFILE_INVALID",
            retryable=False,
            message="native profile preprocessing is unsupported",
        )
    return dataclass_replace(
        config,
        dataset_version=dataset_version,
        data_dir=dataset_dir,
        output_dir=training_dir,
        resume=False,
        prepare_only=False,
    ).validate()


def _run_native_training(config):
    """Call the maintained training entrypoint from the isolated worker child."""

    from ml_model.training.train import run_training

    return run_training(config)


def _build_candidate_artifact(
    *,
    run: RetrainingRunRecord,
    run_dir: Path,
    training_dir: Path,
    project_root: Path,
    dataset_version: str,
):
    from ml_model.export.package_serving_artifact import (
        load_training_summary,
        package_serving_artifact,
    )
    from ml_model.export.promote_final_training_run import (
        build_config_used,
        build_eval_report,
        extract_calibration_temperature,
        extract_state_dict_checkpoint,
        resolve_repo_commit,
        validate_native_promotion_metadata,
        write_eval_provenance_files,
        write_json,
        write_text,
    )

    source = _load_training_source(training_dir)
    config_metadata = _read_json(source["config_metadata.json"])
    if (
        config_metadata.get("dataset_version") != dataset_version
        or config_metadata.get("preprocessing_version")
        != NATIVE_PREPROCESSING_VERSION
    ):
        raise PipelineFailure(
            "NATIVE_TRAINING_IDENTITY_MISMATCH",
            retryable=False,
            message="native training identity does not match dataset snapshot",
        )
    try:
        validate_native_promotion_metadata(config_metadata)
        summary_snapshot = load_training_summary(source["summary_metrics.json"])
        per_class_metrics = json.loads(
            source["per_class_metrics.json"].read_text(encoding="utf-8")
        )
        calibration_payload = _read_json(source["calibration.json"])
        if not isinstance(per_class_metrics, list):
            raise ValueError("per-class metrics must be a list")
        temperature = extract_calibration_temperature(calibration_payload)
    except (OSError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        raise PipelineFailure(
            "NATIVE_TRAINING_METADATA_INVALID",
            retryable=False,
            message="native training metadata failed validation",
        ) from exc

    candidate_version = f"{NATIVE_MODEL_VERSION_PREFIX}{run.run_id}"
    candidate_dir = run_dir / "candidate_model"
    evaluation_root = run_dir / "candidate_evaluation"
    if run.candidate_model_digest is not None:
        if not candidate_dir.is_dir() or not (
            candidate_dir / "serving_manifest.json"
        ).is_file():
            raise PipelineFailure(
                "NATIVE_CANDIDATE_IDENTITY_CHANGED",
                retryable=False,
                message="native candidate artifact is missing from the run",
            )
        manifest = _read_json(candidate_dir / "serving_manifest.json")
        if manifest.get("model_version") != candidate_version:
            raise PipelineFailure(
                "NATIVE_CANDIDATE_IDENTITY_CHANGED",
                retryable=False,
                message="native candidate artifact version no longer matches the run",
            )
        from ml_model.retraining.content_digest import compute_content_digest

        candidate_digest = compute_content_digest(candidate_dir)
        if candidate_digest != run.candidate_model_digest:
            raise PipelineFailure(
                "NATIVE_CANDIDATE_IDENTITY_CHANGED",
                retryable=False,
                message="native candidate artifact no longer matches the run",
            )
        return candidate_dir, candidate_version, candidate_digest
    if candidate_dir.exists():
        _remove_generated_directory(candidate_dir, run_dir=run_dir)
    candidate_dir.mkdir(parents=True, exist_ok=False)
    if evaluation_root.exists():
        _remove_generated_directory(evaluation_root, run_dir=run_dir)
    evaluation_root.mkdir(parents=True, exist_ok=False)
    eval_run_dir = evaluation_root / "native"
    eval_run_dir.mkdir(parents=True, exist_ok=False)
    repo_commit = resolve_repo_commit(project_root)

    config_used = build_config_used(
        config_metadata=config_metadata,
        model_version=candidate_version,
    )
    eval_report = build_eval_report(
        summary_metrics=summary_snapshot.metrics,
        per_class_metrics=per_class_metrics,
    )
    write_json(candidate_dir / "config_used.json", config_used)
    write_json(candidate_dir / "eval_report.json", eval_report)
    write_text(candidate_dir / "git_hash.txt", repo_commit + "\n")
    from ml_model.export.package_serving_artifact import stage_training_summary_for_packaging

    stage_training_summary_for_packaging(
        candidate_run=candidate_dir,
        summary_snapshot=summary_snapshot,
    )
    extract_state_dict_checkpoint(
        source["checkpoint"],
        candidate_dir / "best_distilbert_ckpt.pt",
        normalize_for_packager=True,
        architecture=str(config_metadata.get("architecture")),
    )
    write_eval_provenance_files(
        eval_root=evaluation_root,
        model_key=NATIVE_MODEL_KEY,
        run_dir_name=candidate_version,
        temperature=temperature,
        repo_commit=repo_commit,
        dataset_version=dataset_version,
        artifact_packaging_pipeline_passed=False,
        local_reload_validated=False,
        quality_gates_passed=False,
        eval_run_dir=eval_run_dir,
    )
    try:
        package_serving_artifact(
            model_key=NATIVE_MODEL_KEY,
            run_dir_name=candidate_version,
            run_dir_path=candidate_dir,
            evaluation_root=evaluation_root,
            calibration_eval_run_dir=eval_run_dir,
            repo_root=project_root,
            overwrite=True,
            strict=True,
            notes="dashboard-triggered native laptop candidate; activation remains explicit",
            training_summary_snapshot=summary_snapshot,
        )
    except (OSError, TypeError, ValueError, RuntimeError) as exc:
        raise PipelineFailure(
            "NATIVE_PACKAGING_FAILED",
            retryable=False,
            message="native candidate packaging failed validation",
        ) from exc
    from ml_model.retraining.content_digest import compute_content_digest

    return candidate_dir, candidate_version, compute_content_digest(candidate_dir)


def _resolve_active_model_path(
    *, project_root: Path, run: RetrainingRunRecord
) -> Path:
    from ml_model.retraining.content_digest import compute_content_digest

    staging_root = (project_root / "ml_model" / "model_registry" / "staging").resolve()
    candidates = sorted(
        path
        for path in staging_root.glob(f"{NATIVE_MODEL_KEY}_*")
        if path.is_dir() and not path.is_symlink()
    )
    for path in candidates:
        try:
            manifest = _read_json(path / "serving_manifest.json")
            if manifest.get("model_version") != run.active_model_version:
                continue
            if compute_content_digest(path) != run.active_model_digest:
                continue
            return path
        except (OSError, TypeError, ValueError):
            continue
    raise PipelineFailure(
        "ACTIVE_MODEL_IDENTITY_INVALID",
        retryable=False,
        message="active model identity could not be verified",
    )


def _evaluation_rows(
    *,
    training_dir: Path,
    dataset_dir: Path,
    max_test_samples: int | None,
    seed: int,
) -> tuple[list[str], list[str], str]:
    import pandas as pd

    from ml_model.preprocessing.dataset_io import load_data_splits
    from ml_model.preprocessing.model_input import MODEL_INPUT_TEXT_COLUMN
    from ml_model.training.train import _limit_split

    rows_path = training_dir / "evaluated_test_rows.csv"
    if not rows_path.is_file():
        raise PipelineFailure(
            "NATIVE_EVALUATION_ROWS_MISSING",
            retryable=False,
            message="native evaluation rows are missing",
        )
    try:
        evaluated = pd.read_csv(rows_path, usecols=[MODEL_INPUT_TEXT_COLUMN, "final_label"])
        _, _, frozen_test = load_data_splits(
            dataset_dir, MODEL_INPUT_TEXT_COLUMN, "final_label"
        )
        expected = _limit_split(
            frozen_test,
            "final_label",
            max_test_samples or len(frozen_test),
            seed + 2,
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise PipelineFailure(
            "NATIVE_EVALUATION_SPLIT_INVALID",
            retryable=False,
            message="native evaluation split could not be verified",
        ) from exc
    expected_rows = list(
        zip(
            expected[MODEL_INPUT_TEXT_COLUMN].astype(str),
            expected["final_label"].astype(str),
            strict=True,
        )
    )
    actual_rows = list(
        zip(
            evaluated[MODEL_INPUT_TEXT_COLUMN].astype(str),
            evaluated["final_label"].astype(str),
            strict=True,
        )
    )
    if actual_rows != expected_rows:
        raise PipelineFailure(
            "NATIVE_EVALUATION_SPLIT_MISMATCH",
            retryable=False,
            message="native evaluation rows do not match frozen test split",
        )
    labels = [label for _text, label in actual_rows]
    texts = [text for text, _label in actual_rows]
    if not labels or any(label not in CANONICAL_LABELS for label in labels):
        raise PipelineFailure(
            "NATIVE_EVALUATION_LABELS_INVALID",
            retryable=False,
            message="native evaluation labels are invalid",
        )
    rows_digest = _sha256_bytes(
        canonical_json(
            [
                {
                    "model_input_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "verified_label": label,
                }
                for text, label in actual_rows
            ]
        ).encode("utf-8")
    )
    return texts, labels, rows_digest


def _predict_rows(*, model_path: Path, texts: Sequence[str]) -> list[str]:
    from ml_model.inference.predict_attack import load_model, predict_attack

    try:
        model, tokenizer, temperature = load_model(
            NATIVE_MODEL_KEY, staging_dir=model_path, device="cpu"
        )
        return [
            str(
                predict_attack(
                    text,
                    model,
                    tokenizer,
                    device="cpu",
                    temperature=temperature,
                    return_latency=False,
                )["label"]
            )
            for text in texts
        ]
    except (OSError, RuntimeError, TypeError, ValueError, KeyError) as exc:
        raise PipelineFailure(
            "NATIVE_EVALUATION_FAILED",
            retryable=False,
            message="native model evaluation failed",
        ) from exc


def _native_metrics(
    *, labels: Sequence[str], predictions: Sequence[str], evaluation_digest: str
) -> dict[str, Any]:
    from ml_model.retraining.dashboard_compare import calculate_ground_truth_metrics

    metrics = calculate_ground_truth_metrics(
        labels,
        predictions,
        evaluation_split=NATIVE_EVALUATION_SPLIT,
        evaluation_digest=evaluation_digest,
    )
    return {
        name: replace(
            metric,
            evidence_status=EvidenceStatus.NATIVE,
            metric_kind=MetricKind.NATIVE_EVALUATION,
        )
        for name, metric in metrics.items()
    }


def _evaluate_candidate(
    *,
    run: RetrainingRunRecord,
    dataset_result: Any,
    candidate_path: Path,
    candidate_version: str,
    candidate_digest: str,
    training_config: Any,
    project_root: Path,
) -> tuple[ComparisonResponse, str, dict[str, Any], dict[str, Any]]:
    active_path = _resolve_active_model_path(project_root=project_root, run=run)
    texts, labels, rows_digest = _evaluation_rows(
        training_dir=candidate_path.parent / "training",
        dataset_dir=dataset_result.dataset_dir,
        max_test_samples=training_config.max_test_samples,
        seed=int(training_config.seeds[0]),
    )
    from ml_model.retraining.content_digest import compute_content_digest

    active_digest = compute_content_digest(active_path)
    if active_digest != run.active_model_digest:
        raise PipelineFailure(
            "ACTIVE_MODEL_DIGEST_CHANGED",
            retryable=False,
            message="active model changed during native evaluation",
        )
    evaluation_digest = _sha256_bytes(
        canonical_json(
            {
                "dataset_version": dataset_result.dataset_version,
                "dataset_digest": compute_content_digest(dataset_result.dataset_dir),
                "source_dataset_version": run.source_dataset_version,
                "source_dataset_digest": run.source_dataset_digest,
                "preprocessing_version": NATIVE_PREPROCESSING_VERSION,
                "evaluation_split": NATIVE_EVALUATION_SPLIT,
                "rows_digest": rows_digest,
                "active_model_digest": run.active_model_digest,
                "candidate_model_digest": candidate_digest,
                "pipeline_fingerprint": run.pipeline_fingerprint,
                "training_profile": training_config.to_dict(),
            }
        ).encode("utf-8")
    )
    active_predictions = _predict_rows(model_path=active_path, texts=texts)
    candidate_predictions = _predict_rows(model_path=candidate_path, texts=texts)
    active_metrics = _native_metrics(
        labels=labels,
        predictions=active_predictions,
        evaluation_digest=evaluation_digest,
    )
    candidate_metrics = _native_metrics(
        labels=labels,
        predictions=candidate_predictions,
        evaluation_digest=evaluation_digest,
    )
    from ml_model.retraining.dashboard_compare import compare_candidate_metrics

    comparison = compare_candidate_metrics(
        active_metrics=active_metrics,
        candidate_metrics=candidate_metrics,
        active_model=ModelReference(run.active_model_version, run.active_model_digest),
        candidate_model=ModelReference(candidate_version, candidate_digest),
        provenance=EvaluationProvenance(
            dataset_version=dataset_result.dataset_version,
            dataset_digest=compute_content_digest(dataset_result.dataset_dir),
            evaluation_digest=evaluation_digest,
            evaluation_split=NATIVE_EVALUATION_SPLIT,
            active_model_digest=run.active_model_digest,
            candidate_model_digest=candidate_digest,
        ),
    )
    evaluation_payload = {
        "stage": "evaluation",
        "evidence_status": "NATIVE",
        "status": comparison.overall_status.value,
        "evaluation_split": NATIVE_EVALUATION_SPLIT,
        "preprocessing_version": NATIVE_PREPROCESSING_VERSION,
        "dataset_version": dataset_result.dataset_version,
        "dataset_digest": compute_content_digest(dataset_result.dataset_dir),
        "evaluation_digest": evaluation_digest,
        "active_model_digest": run.active_model_digest,
        "candidate_model_digest": candidate_digest,
        "metrics": {
            "active": {name: metric.to_dict() for name, metric in active_metrics.items()},
            "candidate": {
                name: metric.to_dict() for name, metric in candidate_metrics.items()
            },
        },
    }
    comparison_payload = {
        "stage": "evidence_comparison",
        **comparison.to_dict(),
    }
    return comparison, evaluation_digest, evaluation_payload, comparison_payload


class NativeDashboardPipeline:
    """Run one server-profiled native training/evaluation flow in the worker child."""

    def __init__(
        self,
        *,
        project_root: Path | str | None = None,
        profile_path: Path | str | None = None,
    ) -> None:
        configured_root = (
            project_root or os.environ.get("IAS_PROJECT_ROOT") or PROJECT_ROOT
        )
        self._project_root = Path(configured_root).expanduser().resolve()
        self._profile_path = Path(profile_path or NATIVE_PROFILE_PATH).expanduser().resolve()

    def execute(
        self,
        run: RetrainingRunRecord,
        repository: RetrainingRunArtifactRepository,
        heartbeat: Heartbeat,
    ) -> PipelineResult:
        worker_id = run.worker_id
        run_dir = get_run_artifact_directory(repository.root, run.run_id)
        try:
            heartbeat()
            export_manifest, exported_samples = _load_export(run=run, run_dir=run_dir)
            repository.publish_json_artifact(
                run.run_id,
                "stages/export.json",
                {
                    "stage": "export",
                    "status": export_manifest["status"],
                    "approved_sample_count": len(exported_samples),
                    "source_review_count": len(run.source_review_revisions),
                    "source_dataset_version": run.source_dataset_version,
                    "preprocessing_version": NATIVE_PREPROCESSING_VERSION,
                    "export_manifest_sha256": _sha256_file(
                        run_dir / "export" / "export_manifest.json"
                    ),
                    "approved_samples_sha256": _sha256_file(
                        run_dir / "export" / "approved_samples.jsonl"
                    ),
                },
                stage="export",
                worker_id=worker_id,
            )
            if export_manifest["status"] == "EMPTY":
                repository.complete_stage(
                    run.run_id,
                    next_state=RunState.SKIPPED_NO_APPROVED_DATA,
                    required_artifacts=("stages/export.json",),
                    worker_id=worker_id,
                    stage="preflight",
                )
                return PipelineResult(RunState.SKIPPED_NO_APPROVED_DATA, "NOT_ENOUGH_EVIDENCE")
            if export_manifest["status"] == "QUARANTINED_FOR_REVIEW":
                repository.complete_stage(
                    run.run_id,
                    next_state=RunState.QUARANTINED_FOR_REVIEW,
                    required_artifacts=("stages/export.json",),
                    worker_id=worker_id,
                    stage="preflight",
                )
                return PipelineResult(RunState.QUARANTINED_FOR_REVIEW, "NOT_ENOUGH_EVIDENCE")

            repository.complete_stage(
                run.run_id,
                next_state=RunState.DATASET_VALIDATED,
                required_artifacts=("stages/export.json",),
                worker_id=worker_id,
                stage="dataset_validated",
            )
            heartbeat()
            from ml_model.retraining.dashboard_dataset import build_dashboard_dataset_snapshot
            from ml_model.retraining.content_digest import compute_content_digest

            dataset_dir = run_dir / "dataset"
            if dataset_dir.exists():
                dataset_result = _load_existing_dataset(
                    dataset_dir=dataset_dir,
                    run_id=run.run_id,
                    source_dataset_version=run.source_dataset_version,
                    preprocessing_version=NATIVE_PREPROCESSING_VERSION,
                )
            else:
                dataset_result = build_dashboard_dataset_snapshot(
                    run_id=run.run_id,
                    exported_samples=exported_samples,
                    historical_data_dir=(
                        self._project_root
                        / "data"
                        / "processed"
                        / run.source_dataset_version
                    ),
                    output_root=repository.root,
                    source_dataset_version=run.source_dataset_version,
                    expected_preprocessing_version=NATIVE_PREPROCESSING_VERSION,
                )
            dataset_digest = compute_content_digest(dataset_result.dataset_dir)
            dataset_stage = _read_existing_stage_artifact(
                repository,
                run_id=run.run_id,
                run_dir=run_dir,
                relative_path="stages/dataset.json",
            )
            if run.dataset_digest is not None and dataset_digest != run.dataset_digest:
                raise PipelineFailure(
                    "NATIVE_DATASET_IDENTITY_CHANGED",
                    retryable=False,
                    message="native dataset snapshot no longer matches the run",
                )
            if (
                run.dataset_version is not None
                and dataset_result.dataset_version != run.dataset_version
            ):
                raise PipelineFailure(
                    "NATIVE_DATASET_IDENTITY_CHANGED",
                    retryable=False,
                    message="native dataset version no longer matches the run",
                )
            if dataset_stage is not None:
                if dataset_stage.get("dataset_digest") != dataset_digest:
                    raise PipelineFailure(
                        "NATIVE_DATASET_IDENTITY_CHANGED",
                        retryable=False,
                        message="native dataset stage no longer matches the snapshot",
                    )
                if dataset_stage.get("dataset_version") != dataset_result.dataset_version:
                    raise PipelineFailure(
                        "NATIVE_DATASET_IDENTITY_CHANGED",
                        retryable=False,
                        message="native dataset stage no longer matches the snapshot",
                    )
            repository.update_run_metadata(
                run.run_id,
                worker_id=worker_id,
                dataset_version=dataset_result.dataset_version,
                dataset_digest=dataset_digest,
            )
            repository.publish_json_artifact(
                run.run_id,
                "stages/dataset.json",
                {
                    "stage": "dataset",
                    "status": "VALIDATED",
                    "dataset_version": dataset_result.dataset_version,
                    "dataset_digest": dataset_digest,
                    "source_dataset_version": run.source_dataset_version,
                    "source_dataset_digest": run.source_dataset_digest,
                    "preprocessing_version": NATIVE_PREPROCESSING_VERSION,
                    "holdout_policy": "frozen_historical_validation_test",
                    "dataset_manifest_sha256": dataset_result.manifest["manifest_sha256"],
                    "row_counts": dataset_result.manifest["row_counts"],
                    "historical_data_unchanged": dataset_result.manifest[
                        "historical_data_unchanged"
                    ],
                },
                stage="dataset",
                worker_id=worker_id,
            )
            repository.complete_stage(
                run.run_id,
                next_state=RunState.TRAINING,
                required_artifacts=("stages/dataset.json",),
                worker_id=worker_id,
                stage="training",
            )

            heartbeat()
            training_dir = run_dir / "training"
            training_config = _training_config_for_run(
                dataset_dir=dataset_result.dataset_dir,
                dataset_version=dataset_result.dataset_version,
                training_dir=training_dir,
                profile_path=self._profile_path,
            )
            training_stage = _read_existing_stage_artifact(
                repository,
                run_id=run.run_id,
                run_dir=run_dir,
                relative_path="stages/training.json",
            )
            if training_stage is not None and (
                not training_dir.is_dir() or _find_training_source(training_dir) is None
            ):
                raise PipelineFailure(
                    "NATIVE_TRAINING_IDENTITY_CHANGED",
                    retryable=False,
                    message="native training stage has no matching output",
                )
            if not training_dir.exists():
                _run_native_training(training_config)
            elif _find_training_source(training_dir) is None:
                _remove_generated_directory(training_dir, run_dir=run_dir)
                _run_native_training(training_config)
            training_source = _load_training_source(training_dir)
            training_digest = compute_content_digest(training_dir)
            if training_stage is not None:
                if training_stage.get("training_output_digest") != training_digest:
                    raise PipelineFailure(
                        "NATIVE_TRAINING_IDENTITY_CHANGED",
                        retryable=False,
                        message="native training output no longer matches its stage",
                    )
                if training_stage.get("dataset_version") != dataset_result.dataset_version:
                    raise PipelineFailure(
                        "NATIVE_TRAINING_IDENTITY_CHANGED",
                        retryable=False,
                        message="native training stage dataset no longer matches",
                    )
            repository.publish_json_artifact(
                run.run_id,
                "stages/training.json",
                {
                    "stage": "training",
                    "training_status": "COMPLETE",
                    "entrypoint": "ml_model.training.train.run_training",
                    "profile": self._profile_path.name,
                    "profile_sha256": _sha256_file(self._profile_path),
                    "config_sha256": _sha256_bytes(
                        canonical_json(training_config.to_dict()).encode("utf-8")
                    ),
                    "training_output_digest": training_digest,
                    "training_output": "training",
                    "dataset_version": dataset_result.dataset_version,
                    "preprocessing_version": NATIVE_PREPROCESSING_VERSION,
                    "seed": int(training_config.seeds[0]),
                    "device": training_config.device,
                    "precision": training_config.precision,
                    "sample_limits": {
                        "train": training_config.max_train_samples,
                        "validation": training_config.max_validation_samples,
                        "test": training_config.max_test_samples,
                    },
                    "source_summary_sha256": _sha256_file(
                        training_source["summary_metrics.json"]
                    ),
                },
                stage="training",
                worker_id=worker_id,
            )
            repository.complete_stage(
                run.run_id,
                next_state=RunState.EVALUATING,
                required_artifacts=("stages/training.json",),
                worker_id=worker_id,
                stage="evaluating",
            )

            heartbeat()
            (
                candidate_path,
                candidate_version,
                candidate_digest,
            ) = _build_candidate_artifact(
                run=run,
                run_dir=run_dir,
                training_dir=training_dir,
                project_root=self._project_root,
                dataset_version=dataset_result.dataset_version,
            )
            comparison, evaluation_digest, evaluation_payload, comparison_payload = (
                _evaluate_candidate(
                    run=run,
                    dataset_result=dataset_result,
                    candidate_path=candidate_path,
                    candidate_version=candidate_version,
                    candidate_digest=candidate_digest,
                    training_config=training_config,
                    project_root=self._project_root,
                )
            )
            repository.update_run_metadata(
                run.run_id,
                worker_id=worker_id,
                evaluation_digest=evaluation_digest,
            )
            repository.publish_json_artifact(
                run.run_id,
                "stages/evaluation.json",
                evaluation_payload,
                stage="evaluation",
                worker_id=worker_id,
            )
            repository.publish_json_artifact(
                run.run_id,
                "stages/comparison.json",
                comparison_payload,
                stage="evidence_comparison",
                worker_id=worker_id,
            )
            if comparison.overall_status not in {
                GateStatus.PASS,
                GateStatus.FAIL,
            }:
                _remove_generated_directory(candidate_path, run_dir=run_dir)
                _remove_generated_directory(
                    run_dir / "candidate_evaluation", run_dir=run_dir
                )
                repository.complete_stage(
                    run.run_id,
                    next_state=RunState.NOT_ENOUGH_EVIDENCE,
                    required_artifacts=(
                        "stages/evaluation.json",
                        "stages/comparison.json",
                    ),
                    worker_id=worker_id,
                    stage="evidence_comparison",
                )
                return PipelineResult(RunState.NOT_ENOUGH_EVIDENCE, "NATIVE")

            from ml_model.export.promote_final_training_run import (
                resolve_repo_commit,
                write_eval_provenance_files,
            )

            eval_run_dir = run_dir / "candidate_evaluation" / "native"
            manifest = _read_json(candidate_path / "serving_manifest.json")
            temperature = float(manifest["temperature"])
            write_eval_provenance_files(
                eval_root=run_dir / "candidate_evaluation",
                model_key=NATIVE_MODEL_KEY,
                run_dir_name=candidate_version,
                temperature=temperature,
                repo_commit=(
                    (candidate_path / "git_hash.txt")
                    .read_text(encoding="utf-8")
                    .strip()
                    or resolve_repo_commit(self._project_root)
                ),
                dataset_version=dataset_result.dataset_version,
                artifact_packaging_pipeline_passed=True,
                local_reload_validated=bool(manifest.get("local_reload_verified")),
                quality_gates_passed=comparison.overall_status is GateStatus.PASS,
                eval_run_dir=eval_run_dir,
            )
            repository.update_run_metadata(
                run.run_id,
                worker_id=worker_id,
                candidate_model_version=candidate_version,
                candidate_model_digest=candidate_digest,
            )
            repository.publish_json_artifact(
                run.run_id,
                "stages/candidate.json",
                {
                    "stage": "candidate",
                    "status": "PENDING_APPROVAL",
                    "candidate_model_version": candidate_version,
                    "candidate_model_digest": candidate_digest,
                    "artifact_path": "candidate_model",
                    "serving_manifest_sha256": _sha256_file(
                        candidate_path / "serving_manifest.json"
                    ),
                    "evaluation_provenance": "candidate_evaluation/native",
                    "active_model_unchanged": True,
                },
                stage="candidate",
                worker_id=worker_id,
            )
            repository.complete_stage(
                run.run_id,
                next_state=RunState.PENDING_APPROVAL,
                required_artifacts=(
                    "stages/evaluation.json",
                    "stages/comparison.json",
                    "stages/candidate.json",
                ),
                worker_id=worker_id,
                stage="pending_approval",
            )
            return PipelineResult(RunState.PENDING_APPROVAL, "NATIVE")
        except PipelineFailure:
            raise
        except ModuleNotFoundError as exc:
            raise PipelineFailure(
                "NATIVE_RUNTIME_DEPENDENCY_MISSING",
                retryable=False,
                message="native training dependencies are unavailable",
            ) from exc
        except (OSError, TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise PipelineFailure(
                "NATIVE_PIPELINE_INVALID",
                retryable=False,
                message=type(exc).__name__,
            ) from exc
        except InvalidRunTransition as exc:
            raise PipelineFailure(
                "NATIVE_PIPELINE_STATE_INVALID",
                retryable=False,
                message=str(exc),
            ) from exc
        except RuntimeError as exc:
            raise PipelineFailure(
                "NATIVE_TRAINING_FAILED",
                retryable=True,
                message=type(exc).__name__,
            ) from exc

def run_pipeline_once(
    *,
    repository: RetrainingRunArtifactRepository,
    run_id: str,
    smoke: bool,
) -> PipelineResult:
    run = repository.load_run(run_id)
    if run.state is not RunState.EXPORTING:
        raise PipelineFailure(
            "RUN_NOT_CLAIMED",
            retryable=False,
            message="run must be claimed by a worker before pipeline execution",
        )
    pipeline = SmokeDashboardPipeline() if smoke else NativeDashboardPipeline()
    return pipeline.execute(
        run,
        repository,
        lambda: repository.heartbeat(run_id, worker_id=run.worker_id or ""),
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--smoke", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    repository = RetrainingRunArtifactRepository(args.root)
    try:
        run_pipeline_once(repository=repository, run_id=args.run_id, smoke=args.smoke)
    except PipelineFailure as exc:
        return 20 if exc.retryable else 30
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "NativeDashboardPipeline",
    "PipelineFailure",
    "PipelineResult",
    "SmokeDashboardPipeline",
    "run_pipeline_once",
]
