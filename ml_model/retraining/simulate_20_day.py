"""Controlled cumulative retraining simulation orchestration."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from ml_model.evaluation.evaluate import evaluate_run_bundle
from ml_model.evaluation.golden_controls import (
    GoldenControlSet,
    evaluate_golden_controls,
    load_golden_controls,
)
from ml_model.preprocessing.dataset_io import (
    load_dataset_file_manifest,
    validate_dataset_preprocessing,
)
from ml_model.retraining.experiment_contract import (
    AcceptanceTolerances,
    ExperimentConfig,
    load_experiment_config,
    sha256_file,
)
from ml_model.retraining.integrity import validate_candidate_contract
from ml_model.retraining.prediction_artifacts import (
    records_from_golden_evaluation,
    write_prediction_artifact,
)
from ml_model.retraining.report_simulation import (
    write_simulation_markdown,
    write_simulation_report,
)
from ml_model.retraining.snapshots import (
    ContaminationIndex,
    SnapshotResult,
    build_cumulative_snapshot,
    load_historical_frames,
    validate_snapshot_integrity,
)
from ml_model.retraining.statistical_evidence import build_statistical_evidence
from ml_model.retraining.validate_batch import (
    BatchValidationReport,
    validate_batch_file,
)

# Backend acceptance probe for the actual target application. The historical
# /api/users regression remains in golden-v2, but it is not an LRP route and
# must not be the simulator's primary backend probe.
TARGET_BACKEND_REQUEST = "GET /records/search?query=Maple"
SMOKE_REQUESTS = (
    "GET /smoke/health/check",
    "POST /control/items/create",
    "PUT /fixture/search/update",
    "DELETE /sample/events/remove",
    "PATCH /synthetic/roles/rename",
    "GET /orchestration/teams/list",
    "POST /evidence/projects/add",
    "PUT /validation/reports/refresh",
    "DELETE /testing/alerts/clear",
    "PATCH /contract/users/rotate",
    "GET /integrity/audit/read",
    "POST /pipeline/status/write",
    "PUT /snapshot/metrics/replace",
    "DELETE /candidate/profile/remove",
    "PATCH /artifact/catalog/patch",
    "GET /quarantine/assets/list",
    "POST /baseline/billing/check",
    "PUT /manifest/settings/update",
    "DELETE /registry/sessions/revoke",
    "PATCH /simulation/notifications/send",
)


TrainHook = Callable[..., Path]
EvaluateHook = Callable[..., Mapping[str, Any]]
PackageHook = Callable[..., Path]
ReloadHook = Callable[..., bool]
GoldenHook = Callable[..., Mapping[str, Any]]
BackendHook = Callable[..., Mapping[str, Any]]


@dataclass(frozen=True)
class SimulationHooks:
    train: TrainHook | None = None
    evaluate: EvaluateHook | None = None
    package: PackageHook | None = None
    reload: ReloadHook | None = None
    golden: GoldenHook | None = None
    backend: BackendHook | None = None


@dataclass(frozen=True)
class AcceptanceGateResult:
    passed: bool
    checks: dict[str, bool]
    failures: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": self.checks,
            "failures": list(self.failures),
        }


@dataclass(frozen=True)
class SimulationReport:
    experiment: dict[str, Any]
    status: str
    days: tuple[dict[str, Any], ...]
    baseline_status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment": self.experiment,
            "status": self.status,
            "baseline_status": self.baseline_status,
            "days": list(self.days),
        }


def _metric(payload: Mapping[str, Any], key: str) -> float:
    value = payload.get(key)
    if value is None:
        raise ValueError(f"candidate metrics are missing {key}")
    return float(value)


REQUIRED_BASELINE_METRICS = {
    "normal_false_positive_rate",
    "attack_escape_rate",
    "macro_f1",
    "normal_recall",
    "supported_attack_recall",
}


def normalize_baseline_metrics(payload: Mapping[str, Any]) -> dict[str, Any]:
    metrics = payload.get("metrics", payload)
    if not isinstance(metrics, Mapping):
        raise ValueError("baseline metrics must be a JSON object")
    missing = sorted(
        key
        for key in REQUIRED_BASELINE_METRICS
        if key not in metrics or metrics[key] is None
    )
    if missing:
        raise ValueError(f"baseline is missing required metrics: {missing}")
    supported_attack_recall = metrics["supported_attack_recall"]
    if not isinstance(supported_attack_recall, Mapping):
        raise ValueError("baseline supported_attack_recall must be a JSON object")
    normalized = {
        "normal_false_positive_rate": float(metrics["normal_false_positive_rate"]),
        "attack_escape_rate": float(metrics["attack_escape_rate"]),
        "macro_f1": float(metrics["macro_f1"]),
        "normal_recall": float(metrics["normal_recall"]),
        "supported_attack_recall": dict(supported_attack_recall),
    }
    prediction_artifact = payload.get("prediction_artifact")
    if prediction_artifact is not None:
        normalized["prediction_artifact"] = str(prediction_artifact)
    return normalized


def validate_frozen_baseline_report(
    payload: Mapping[str, Any],
    *,
    allow_smoke: bool = False,
) -> None:
    """Reject incomplete or synthetic baseline reports for native runs."""

    if allow_smoke:
        return
    required_state = {
        "status": "PASS",
        "baseline_status": "FROZEN",
        "model_quality_conclusion": "READY_FOR_EXPERIMENT",
    }
    mismatches = {
        key: payload.get(key)
        for key, expected in required_state.items()
        if payload.get(key) != expected
    }
    gate = payload.get("baseline_gate")
    if not isinstance(gate, Mapping) or gate.get("passed") is not True:
        mismatches["baseline_gate"] = gate
    if mismatches:
        details = ", ".join(
            f"{key}={value!r}" for key, value in sorted(mismatches.items())
        )
        raise ValueError(
            "a real retraining simulation requires a frozen baseline: " + details
        )


def validate_baseline_attack_recall_completeness(
    baseline: Mapping[str, Any], required_attack_labels: Iterable[str]
) -> None:
    supported_attack_recall = baseline.get("supported_attack_recall", {})
    missing = sorted(
        label
        for label in required_attack_labels
        if label not in supported_attack_recall
    )
    if missing:
        raise ValueError(
            "baseline is missing supported attack recall metrics: " + ", ".join(missing)
        )


def evaluate_acceptance_gates(
    *,
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    golden: Mapping[str, Any],
    package_passed: bool,
    reload_passed: bool,
    backend_passed: bool,
    candidate_contract: Mapping[str, Any] | None = None,
    statistical_evidence: Mapping[str, Any] | None = None,
    tolerances: AcceptanceTolerances | None = None,
) -> AcceptanceGateResult:
    tolerances = tolerances or AcceptanceTolerances()
    checks: dict[str, bool] = {
        "golden_controls": bool(golden.get("passed")),
        "packaging": bool(package_passed),
        "reload": bool(reload_passed),
        "backend": bool(backend_passed),
    }
    if candidate_contract is not None:
        checks["contract_integrity"] = bool(candidate_contract.get("passed"))
    if statistical_evidence is not None:
        checks["statistical_evidence"] = (
            statistical_evidence.get("status") == "COMPUTED"
        )
    checks["normal_false_positive_rate"] = _metric(
        candidate, "normal_false_positive_rate"
    ) <= (
        _metric(baseline, "normal_false_positive_rate")
        + tolerances.normal_false_positive_tolerance
    )
    checks["attack_escape_rate"] = _metric(candidate, "attack_escape_rate") <= (
        _metric(baseline, "attack_escape_rate") + tolerances.attack_escape_tolerance
    )
    checks["macro_f1"] = _metric(candidate, "macro_f1") >= (
        _metric(baseline, "macro_f1") - tolerances.macro_f1_drop_tolerance
    )
    checks["normal_recall"] = (
        _metric(candidate, "normal_recall") >= tolerances.normal_recall_minimum
    )
    baseline_attack = dict(baseline.get("supported_attack_recall", {}))
    candidate_attack = dict(candidate.get("supported_attack_recall", {}))
    for label, baseline_recall in sorted(baseline_attack.items()):
        checks[f"supported_attack_recall:{label}"] = float(
            candidate_attack.get(label, -1.0)
        ) >= (
            float(baseline_recall) - tolerances.supported_attack_recall_drop_tolerance
        )
    failures = tuple(key for key, passed in checks.items() if not passed)
    return AcceptanceGateResult(not failures, checks, failures)


def _extract_candidate_metrics(run_dir: Path) -> dict[str, Any]:
    summaries = sorted(Path(run_dir).glob("**/summary_metrics.json"))
    if not summaries:
        raise FileNotFoundError(f"no seed summary_metrics.json found under {run_dir}")
    selected = next(
        (path for path in summaries if "seed_2026" in str(path)), summaries[0]
    )
    summary = json.loads(selected.read_text(encoding="utf-8"))
    per_class_path = selected.parent / "per_class_metrics.json"
    per_class = (
        json.loads(per_class_path.read_text(encoding="utf-8"))
        if per_class_path.is_file()
        else []
    )
    supported = {
        str(row["label_name"]): float(row["recall"])
        for row in per_class
        if isinstance(row, dict)
        and row.get("label_name") != "Normal"
        and row.get("recall") is not None
    }
    return {
        "normal_false_positive_rate": float(summary["normal_false_positive_rate"]),
        "attack_escape_rate": float(summary["attack_escape_rate"]),
        "macro_f1": float(summary["test_macro_f1"]),
        "normal_recall": float(
            next(
                (
                    row["recall"]
                    for row in per_class
                    if row.get("label_name") == "Normal"
                ),
                0.0,
            )
        ),
        "supported_attack_recall": supported,
        "calibration": {
            "ece": summary.get("test_ece_calibrated"),
            "latency_mean_ms": summary.get("inference_latency_mean_ms"),
        },
    }


def _default_train(
    *, config: ExperimentConfig, snapshot_dir: Path, day_dir: Path, day: int
) -> Path:
    from dataclasses import replace

    from ml_model.training.config import TrainingConfig, load_training_config
    from ml_model.training.train import run_training

    if config.training_config is not None and config.training_config.is_file():
        training = load_training_config(
            config.training_config, project_root=config.project_root
        )
    else:
        training = TrainingConfig(
            dataset_version=config.historical_dataset_version,
            preprocessing_version=config.preprocessing_version,
            models=("distilbert",),
            model_revision=config.model_revision,
            seeds=(config.daily_seed,),
            device="auto",
            precision="auto",
            epochs=config.max_epochs,
            resume=False,
        )
    training = replace(
        training,
        dataset_version=config.historical_dataset_version,
        preprocessing_version=config.preprocessing_version,
        model_revision=config.model_revision,
        models=("distilbert",),
        seeds=(config.daily_seed,),
        epochs=config.max_epochs,
        data_dir=snapshot_dir,
        output_dir=day_dir / "training_run",
        resume=False,
        prepare_only=False,
    ).validate()
    return run_training(training)


def _find_seed_dir(run_dir: Path, seed: int) -> Path:
    candidates = sorted(Path(run_dir).glob(f"**/seed_{seed}"))
    if not candidates:
        raise FileNotFoundError(f"seed directory for {seed} not found under {run_dir}")
    return candidates[0]


def _default_package(
    *, run_dir: Path, day_dir: Path, config: ExperimentConfig, day: int
) -> Path:
    from ml_model.export.package_serving_artifact import package_serving_artifact
    from ml_model.export.promote_final_training_run import (
        build_config_used,
        build_eval_report,
        extract_state_dict_checkpoint,
        resolve_repo_commit,
        write_eval_provenance_files,
        write_json,
        write_text,
    )

    source_dir = _find_seed_dir(run_dir, config.daily_seed)
    checkpoint_candidates = sorted(source_dir.glob("checkpoint/best_distilbert*"))
    if not checkpoint_candidates:
        raise FileNotFoundError(
            f"best DistilBERT checkpoint not found under {source_dir}"
        )
    config_metadata = json.loads(
        (source_dir / "config_metadata.json").read_text(encoding="utf-8")
    )
    summary_metrics = json.loads(
        (source_dir / "summary_metrics.json").read_text(encoding="utf-8")
    )
    per_class_metrics = json.loads(
        (source_dir / "per_class_metrics.json").read_text(encoding="utf-8")
    )
    calibration = json.loads(
        (source_dir / "calibration.json").read_text(encoding="utf-8")
    )
    model_version = f"distilbert_{config.version}_day_{day:02d}"
    candidate_registry = day_dir / "candidate_registry"
    candidate_run = candidate_registry / "staging" / model_version
    candidate_run.mkdir(parents=True, exist_ok=False)
    extract_state_dict_checkpoint(
        checkpoint_candidates[0],
        candidate_run / "best_distilbert_ckpt.pt",
        normalize_for_packager=True,
        architecture=str(config_metadata.get("architecture")),
    )
    write_json(
        candidate_run / "config_used.json",
        build_config_used(config_metadata=config_metadata, model_version=model_version),
    )
    write_json(
        candidate_run / "eval_report.json",
        build_eval_report(
            summary_metrics=summary_metrics, per_class_metrics=per_class_metrics
        ),
    )
    write_text(
        candidate_run / "git_hash.txt", resolve_repo_commit(config.project_root) + "\n"
    )
    eval_root = candidate_registry / "eval"
    eval_root.mkdir(parents=True, exist_ok=True)
    eval_dir = eval_root / f"day_{day:02d}_calibration"
    eval_dir.mkdir()
    write_eval_provenance_files(
        eval_root=eval_root,
        model_key="distilbert",
        run_dir_name=model_version,
        temperature=float(calibration["temperature"]),
        repo_commit=resolve_repo_commit(config.project_root),
        dataset_version=config.historical_dataset_version,
        artifact_packaging_pipeline_passed=False,
        local_reload_validated=False,
        quality_gates_passed=False,
        eval_run_dir=eval_dir,
    )
    return package_serving_artifact(
        model_key="distilbert",
        run_dir_name=model_version,
        discover_latest=False,
        overwrite=True,
        strict=True,
        calibration_eval_run_dir=eval_dir,
        model_registry_path=candidate_registry,
        repo_root=config.project_root,
        confidence_thresholds=config.confidence_thresholds,
        response_actions=config.response_actions,
        notes="offline controlled retraining candidate; never automatically promoted",
    )


def _default_reload(*, artifact_path: Path, config: ExperimentConfig, day: int) -> bool:
    del config, day
    from web_app.config import Settings
    from web_app.services.model_service import ModelService

    settings = Settings(
        database_url="sqlite+aiosqlite://",
        app_env="development",
        model_path="unused",
        model_registry_path=str(artifact_path),
        api_secret_key="controlled-retraining-local-check",
    )
    return ModelService(settings).loaded


def _default_golden(
    *,
    artifact_path: Path,
    controls: GoldenControlSet | None,
    config: ExperimentConfig,
    day: int,
) -> Mapping[str, Any]:
    del day
    if controls is None:
        return {"passed": False, "error": "golden controls were not loaded"}
    from web_app.config import Settings
    from web_app.services.model_service import ModelService

    service = ModelService(
        Settings(
            database_url="sqlite+aiosqlite://",
            app_env="development",
            model_path="unused",
            model_registry_path=str(artifact_path),
            api_secret_key="controlled-retraining-local-check",
        )
    )
    evaluation = evaluate_golden_controls(
        controls,
        service.predict,
        confidence_thresholds=config.confidence_thresholds,
        response_actions=config.response_actions,
    ).to_dict()
    prediction_path = artifact_path.parent / f"{artifact_path.name}.predictions.json"
    write_prediction_artifact(
        prediction_path,
        records_from_golden_evaluation(
            controls.cases,
            evaluation,
            model_version=service.model_version or artifact_path.name,
            dataset_version=config.historical_dataset_version,
            golden_version=config.golden_version,
        ),
        model_version=service.model_version or artifact_path.name,
        dataset_version=config.historical_dataset_version,
        golden_version=config.golden_version,
        golden_manifest_sha256=str(evaluation["manifest_sha256"]),
        model_artifact_sha256=sha256_file(
            artifact_path / "serving_manifest.json"
        ),
    )
    return {**evaluation, "prediction_artifact": str(prediction_path)}


def _resolve_prediction_artifact(value: Any, config: ExperimentConfig) -> Path:
    path = Path(str(value)).expanduser()
    return (
        path.resolve() if path.is_absolute() else (config.project_root / path).resolve()
    )


def _default_backend(
    *, artifact_path: Path, config: ExperimentConfig, day: int
) -> Mapping[str, Any]:
    del day
    from web_app.application.triage_use_case import TriageUseCase
    from web_app.config import Settings
    from web_app.services.model_service import ModelService

    service = ModelService(
        Settings(
            database_url="sqlite+aiosqlite://",
            app_env="development",
            model_path="unused",
            model_registry_path=str(artifact_path),
            api_secret_key="controlled-retraining-local-check",
        )
    )
    result = service.predict(TARGET_BACKEND_REQUEST)
    action = TriageUseCase._action_for(
        prediction=str(result["prediction"]),
        confidence_level=str(result["confidence_tier"]),
    )
    configured_action = config.action_for(
        str(result["prediction"]), str(result["confidence_tier"])
    )
    return {
        "passed": (
            result["prediction"] == "Normal"
            and action == "ALLOWED"
            and action == configured_action
        ),
        "request": TARGET_BACKEND_REQUEST,
        "prediction": result["prediction"],
        "action": action,
        "configured_action": configured_action,
    }


def _bool_result(value: Mapping[str, Any] | bool) -> bool:
    return bool(value.get("passed")) if isinstance(value, Mapping) else bool(value)


def _write_day_report(day_dir: Path, payload: Mapping[str, Any]) -> None:
    day_dir.mkdir(parents=True, exist_ok=True)
    (day_dir / "day_report.json").write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _assert_safe_simulation_output(output_root: Path, project_root: Path) -> None:
    protected_root = (project_root / "ml_model" / "model_registry").resolve()
    if output_root == protected_root or protected_root in output_root.parents:
        raise ValueError(
            f"simulation output must not be inside the model registry: {output_root}"
        )


def _write_blocked_following_days(
    output_root: Path,
    day_reports: list[dict[str, Any]],
    *,
    failed_day: int,
    last_day: int,
) -> None:
    for remaining_day in range(failed_day + 1, last_day + 1):
        skipped_dir = output_root / f"day_{remaining_day:02d}"
        skipped = {
            "day": remaining_day,
            "status": "NOT_RUN",
            "stage": "blocked_by_previous_day",
            "blocked_by_day": failed_day,
        }
        _write_day_report(skipped_dir, skipped)
        day_reports.append(skipped)


def run_simulation(
    *,
    config_path: Path | str,
    historical_data_dir: Path | str,
    daily_batch_dir: Path | str,
    output_dir: Path | str,
    days: Iterable[int] | None = None,
    baseline: Mapping[str, Any] | None,
    golden_texts: Iterable[str] | None = None,
    allow_test_overrides: bool = False,
    controlled_simulation: bool = False,
    hooks: SimulationHooks | None = None,
    active_registry_dir: Path | str | None = None,
    _smoke_mode: bool = False,
) -> SimulationReport:
    try:
        config = load_experiment_config(config_path)
    except FileNotFoundError:
        config = load_experiment_config(
            config_path,
            project_root=Path(config_path).resolve().parent,
        )
    output_root = Path(output_dir).expanduser().resolve()
    _assert_safe_simulation_output(output_root, config.project_root)
    active_root = (
        Path(active_registry_dir).expanduser().resolve()
        if active_registry_dir
        else None
    )
    if active_root is not None and (
        output_root == active_root or active_root in output_root.parents
    ):
        raise ValueError(
            "simulation output must not be inside the active model registry"
        )
    if baseline is None:
        raise ValueError("a frozen baseline is required before candidate simulation")
    if controlled_simulation and _smoke_mode:
        raise ValueError(
            "controlled simulation cannot be combined with orchestration smoke mode"
        )
    validate_frozen_baseline_report(
        baseline,
        allow_smoke=_smoke_mode or allow_test_overrides,
    )
    baseline = normalize_baseline_metrics(baseline)
    if golden_texts is not None and not allow_test_overrides:
        raise ValueError("golden_texts overrides require allow_test_overrides=True")
    requested_days = tuple(sorted({int(day) for day in (days or range(1, 21))}))
    if not requested_days or any(day < 1 or day > 20 for day in requested_days):
        raise ValueError("days must contain values from 1 through 20")
    last_day = max(requested_days)
    days_to_process = tuple(range(1, last_day + 1))
    is_complete_experiment = days_to_process == tuple(range(1, 21))
    hooks = hooks or SimulationHooks()
    if not allow_test_overrides:
        validate_baseline_attack_recall_completeness(
            baseline,
            (label for label in config.label_names if label != "Normal"),
        )
        config.validate_runtime_inputs(
            historical_data_dir=historical_data_dir,
            daily_batch_dir=daily_batch_dir,
            days=days_to_process,
        )
        validate_dataset_preprocessing(
            Path(historical_data_dir).expanduser().resolve(),
            expected_dataset_version=config.historical_dataset_version,
            expected_preprocessing_version=config.preprocessing_version,
        )
        load_dataset_file_manifest(Path(historical_data_dir).expanduser().resolve())
    controls: GoldenControlSet | None = (
        None
        if allow_test_overrides and golden_texts is not None
        else load_golden_controls(config.golden_manifest_file)
    )
    historical_frames = load_historical_frames(historical_data_dir)
    contamination_index = ContaminationIndex.from_historical_frames(
        historical_frames
    )
    cumulative_samples: list[dict[str, Any]] = []
    day_reports: list[dict[str, Any]] = []
    for day in days_to_process:
        day_dir = output_root / f"day_{day:02d}"
        batch_path = (
            Path(daily_batch_dir).expanduser().resolve() / f"day_{day:02d}.jsonl"
        )
        day_result: dict[str, Any] = {
            "day": day,
            "status": "REJECTED",
            "stage": "batch_validation",
        }
        try:
            batch_report: BatchValidationReport = validate_batch_file(
                batch_path,
                expected_preprocessing_version=config.preprocessing_version,
                expected_batch_day=day,
                golden_controls=controls,
                golden_texts=golden_texts if controls is None else None,
                allow_synthetic_fixtures=(
                    controlled_simulation or allow_test_overrides
                ),
                quarantine_dir=day_dir / "quarantine",
            )
            day_result["batch_validation"] = batch_report.to_dict()
            day_result["input_hash"] = batch_report.input_sha256
            if not batch_report.passed:
                day_result["error"] = "; ".join(
                    row["reason"] for row in batch_report.rejected_samples
                )
                _write_day_report(day_dir, day_result)
                day_reports.append(day_result)
                _write_blocked_following_days(
                    output_root,
                    day_reports,
                    failed_day=day,
                    last_day=last_day,
                )
                break
            cumulative_samples.extend(batch_report.accepted_samples)
        except Exception as exc:
            day_result["error"] = str(exc)
            if getattr(exc, "report", None) is not None:
                day_result["contamination"] = exc.report
            _write_day_report(day_dir, day_result)
            day_reports.append(day_result)
            _write_blocked_following_days(
                output_root,
                day_reports,
                failed_day=day,
                last_day=last_day,
            )
            break

        try:
            snapshot: SnapshotResult = build_cumulative_snapshot(
                historical_data_dir=historical_data_dir,
                cumulative_samples=cumulative_samples,
                new_samples=batch_report.accepted_samples,
                contamination_index=contamination_index,
                output_root=day_dir / "snapshots",
                day=day,
                dataset_version=config.historical_dataset_version,
                preprocessing_version=config.preprocessing_version,
                project_root=config.project_root,
                historical_frames=historical_frames,
            )
            snapshot_integrity = validate_snapshot_integrity(snapshot.snapshot_dir)
            day_result["stage"] = "training"
            day_result["snapshot_hash"] = snapshot.output_hash
            day_result["snapshot"] = snapshot.manifest
            day_result["snapshot_integrity"] = snapshot_integrity
        except Exception as exc:
            day_result["error"] = str(exc)
            if getattr(exc, "report", None) is not None:
                day_result["contamination"] = exc.report
            _write_day_report(day_dir, day_result)
            day_reports.append(day_result)
            _write_blocked_following_days(
                output_root,
                day_reports,
                failed_day=day,
                last_day=last_day,
            )
            break

        try:
            train_hook = hooks.train or _default_train
            run_dir = Path(
                train_hook(
                    config=config,
                    snapshot_dir=snapshot.snapshot_dir,
                    day_dir=day_dir,
                    day=day,
                )
            ).resolve()
            day_result["stage"] = "evaluation"
            evaluate_hook = hooks.evaluate or (
                lambda **kwargs: {
                    **evaluate_run_bundle(kwargs["run_dir"]),
                    "metrics": _extract_candidate_metrics(kwargs["run_dir"]),
                }
            )
            evaluation = dict(evaluate_hook(run_dir=run_dir, config=config, day=day))
            if evaluation.get("status") not in (None, "complete"):
                raise RuntimeError("incomplete training run bundle")
            raw_metrics = evaluation.get("metrics")
            metrics = (
                dict(raw_metrics)
                if isinstance(raw_metrics, Mapping)
                else _extract_candidate_metrics(run_dir)
            )
            day_result["evaluation"] = evaluation
            day_result["stage"] = "packaging"
            package_hook = hooks.package or _default_package
            artifact_path = Path(
                package_hook(run_dir=run_dir, day_dir=day_dir, config=config, day=day)
            ).resolve()
            candidate_contract = (
                {
                    "passed": True,
                    "mode": "explicit_test_override",
                    "checks": {},
                    "failures": [],
                }
                if allow_test_overrides
                else validate_candidate_contract(
                    config=config,
                    artifact_dir=artifact_path,
                    snapshot_manifest=snapshot.manifest,
                ).to_dict()
            )
            day_result["candidate_contract"] = candidate_contract
            if not candidate_contract["passed"]:
                day_result["statistical_evidence"] = build_statistical_evidence({})
                day_result.update(
                    {
                        "stage": "candidate_contract",
                        "acceptance": {
                            "passed": False,
                            "checks": {"contract_integrity": False},
                            "failures": ["contract_integrity"],
                        },
                        "status": "REJECTED",
                    }
                )
            else:
                day_result["stage"] = "reload"
                reload_hook = hooks.reload or _default_reload
                reload_passed = bool(
                    reload_hook(artifact_path=artifact_path, config=config, day=day)
                )
                day_result["stage"] = "golden_controls"
                golden_hook = hooks.golden or _default_golden
                golden_result = dict(
                    golden_hook(
                        artifact_path=artifact_path,
                        controls=controls,
                        config=config,
                        day=day,
                    )
                )
                evidence_payload = (
                    dict(evaluation)
                    if _smoke_mode or allow_test_overrides
                    else {}
                )
                baseline_artifact = baseline.get("prediction_artifact")
                candidate_artifact = golden_result.get("prediction_artifact")
                if baseline_artifact is not None:
                    evidence_payload["baseline_artifact"] = (
                        _resolve_prediction_artifact(baseline_artifact, config)
                    )
                if candidate_artifact is not None:
                    evidence_payload["candidate_artifact"] = (
                        _resolve_prediction_artifact(candidate_artifact, config)
                    )
                day_result["statistical_evidence"] = build_statistical_evidence(
                    evidence_payload
                )
                day_result["stage"] = "backend"
                backend_hook = hooks.backend or _default_backend
                backend_result = dict(
                    backend_hook(artifact_path=artifact_path, config=config, day=day)
                )
                gates = evaluate_acceptance_gates(
                    baseline=baseline,
                    candidate=metrics,
                    golden=golden_result,
                    package_passed=artifact_path.is_dir(),
                    reload_passed=reload_passed,
                    backend_passed=_bool_result(backend_result),
                    candidate_contract=candidate_contract,
                    statistical_evidence=(
                        day_result["statistical_evidence"]
                        if not _smoke_mode and not allow_test_overrides
                        else None
                    ),
                    tolerances=config.acceptance,
                )
            day_result.update(
                {
                    "stage": day_result.get("stage", "acceptance_gates"),
                    "run_dir": str(run_dir),
                    "artifact_path": str(artifact_path),
                    "metrics": metrics,
                }
            )
            if candidate_contract["passed"]:
                day_result.update(
                    {
                        "stage": "acceptance_gates",
                        "reload_passed": reload_passed,
                        "golden": golden_result,
                        "backend": backend_result,
                        "acceptance": gates.to_dict(),
                        "status": "ACCEPTED" if gates.passed else "REJECTED",
                    }
                )
        except Exception as exc:
            day_result["error"] = str(exc)
        _write_day_report(day_dir, day_result)
        day_reports.append(day_result)
        if day_result.get("status") != "ACCEPTED":
            _write_blocked_following_days(
                output_root,
                day_reports,
                failed_day=day,
                last_day=last_day,
            )
            break

    all_accepted = bool(day_reports) and all(
        day.get("status") == "ACCEPTED" for day in day_reports
    )
    training_attempted = any(
        day.get("stage")
        in {
            "training",
            "evaluation",
            "packaging",
            "reload",
            "golden_controls",
            "backend",
            "acceptance_gates",
        }
        for day in day_reports
    )
    if _smoke_mode:
        final_status = "SMOKE_SUCCESS" if all_accepted else "BLOCKED"
    elif is_complete_experiment and all_accepted:
        final_status = "SUCCESS"
    elif all_accepted:
        final_status = "PARTIAL"
    else:
        final_status = "BLOCKED"
    report = SimulationReport(
        experiment={
            "name": config.name,
            "version": config.version,
            "contract_hash": config.contract_hash,
            "scope": "controlled offline 20-day retraining simulation",
            "execution_mode": (
                "synthetic_orchestration_smoke"
                if _smoke_mode
                else (
                    "controlled_fixture_training_simulation"
                    if controlled_simulation
                    else "native_training_simulation"
                )
            ),
            "real_training_status": (
                "NOT_RUN" if _smoke_mode or not training_attempted else "ATTEMPTED"
            ),
            "model_quality_conclusion": (
                "NOT_PERMITTED"
                if _smoke_mode
                else (
                    "CONTROLLED_SIMULATION_ONLY"
                    if controlled_simulation
                    else "PENDING_ACCEPTANCE_GATES"
                )
            ),
        },
        status=final_status,
        days=tuple(day_reports),
        baseline_status="SMOKE_SYNTHETIC" if _smoke_mode else "FROZEN",
    )
    write_simulation_report(output_root, report.to_dict())
    write_simulation_markdown(output_root, report.to_dict())
    return report


def run_smoke(
    *,
    config_path: Path | str,
    output_dir: Path | str,
    days: Iterable[int] = (1, 2),
) -> SimulationReport:
    """Run a tiny no-network orchestration smoke with synthetic adapters."""

    import pandas as pd

    requested_days = tuple(sorted({int(day) for day in days}))
    if not requested_days:
        raise ValueError("smoke requires at least one day")
    with tempfile.TemporaryDirectory(prefix="retraining-20-day-smoke-") as temp_dir:
        root = Path(temp_dir)
        historical = root / "historical"
        historical.mkdir()
        historical_frame = pd.DataFrame(
            [
                {"combined_payload": "GET /health", "final_label": "Normal"},
                {
                    "combined_payload": "GET /items?id=1 UNION SELECT",
                    "final_label": "SQL Injection",
                },
            ]
        )
        for split in ("train", "validation", "test"):
            historical_frame.to_parquet(historical / f"{split}.parquet", index=False)
        batches = root / "batches"
        batches.mkdir()
        for day in range(1, max(requested_days) + 1):
            model_input_text = SMOKE_REQUESTS[day - 1]
            (batches / f"day_{int(day):02d}.jsonl").write_text(
                json.dumps(
                    {
                        "sample_id": f"smoke-day-{day}",
                        "model_input_text": model_input_text,
                        "model_input_hash": hashlib.sha256(
                            model_input_text.encode("utf-8")
                        ).hexdigest(),
                        "ground_truth_label": "Normal",
                        "batch_day": int(day),
                        "source_type": "synthetic_smoke",
                        "is_synthetic": True,
                        "review_status": "curated_simulation_fixture",
                        "provenance_id": f"smoke:{day}",
                        "preprocessing_version": "http-preprocessor-v1",
                    },
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

        def smoke_train(*, day_dir: Path, **_: Any) -> Path:
            run_dir = day_dir / "smoke_training_run"
            run_dir.mkdir(parents=True, exist_ok=True)
            return run_dir

        def smoke_evaluate(**_: Any) -> Mapping[str, Any]:
            return {
                "status": "complete",
                "metrics": {
                    "normal_false_positive_rate": 0.0,
                    "attack_escape_rate": 0.0,
                    "macro_f1": 1.0,
                    "normal_recall": 1.0,
                    "supported_attack_recall": {"SQL Injection": 1.0},
                },
            }

        def smoke_package(*, day_dir: Path, **_: Any) -> Path:
            artifact = day_dir / "smoke_candidate_artifact"
            artifact.mkdir(parents=True, exist_ok=True)
            (artifact / "serving_manifest.json").write_text(
                '{"local_reload_verified":true}\n', encoding="utf-8"
            )
            return artifact

        return run_simulation(
            config_path=config_path,
            historical_data_dir=historical,
            daily_batch_dir=batches,
            output_dir=output_dir,
            days=requested_days,
            baseline={
                "normal_false_positive_rate": 0.0,
                "attack_escape_rate": 0.0,
                "macro_f1": 1.0,
                "normal_recall": 1.0,
                "supported_attack_recall": {"SQL Injection": 1.0},
            },
            golden_texts=set(),
            allow_test_overrides=True,
            hooks=SimulationHooks(
                train=smoke_train,
                evaluate=smoke_evaluate,
                package=smoke_package,
                reload=lambda **_: True,
                golden=lambda **_: {"passed": True, "mode": "smoke"},
                backend=lambda **_: {"passed": True, "mode": "smoke"},
            ),
            _smoke_mode=True,
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--historical-data-dir", type=Path)
    parser.add_argument("--daily-batch-dir", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, help="Frozen baseline metrics JSON")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run the two-day synthetic orchestration smoke",
    )
    parser.add_argument(
        "--controlled-simulation",
        action="store_true",
        help=(
            "Allow explicitly marked curated simulation fixtures; results are "
            "controlled-simulation evidence, not production retraining evidence"
        ),
    )
    parser.add_argument("--days", nargs="+", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.smoke:
        report = run_smoke(
            config_path=args.config,
            output_dir=args.output_dir,
            days=args.days or (1, 2),
        )
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0 if report.status == "SMOKE_SUCCESS" else 2
    if (
        args.historical_data_dir is None
        or args.daily_batch_dir is None
        or args.baseline is None
    ):
        raise SystemExit(
            "--historical-data-dir, --daily-batch-dir, and --baseline are "
            "required unless --smoke is used"
        )
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    report = run_simulation(
        config_path=args.config,
        historical_data_dir=args.historical_data_dir,
        daily_batch_dir=args.daily_batch_dir,
        output_dir=args.output_dir,
        days=args.days,
        baseline=baseline,
        controlled_simulation=args.controlled_simulation,
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0 if report.status == "SUCCESS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
