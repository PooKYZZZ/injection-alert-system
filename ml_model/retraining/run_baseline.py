"""Run the current staged-model baseline controls without promotion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from ml_model.evaluation.golden_controls import (
    evaluate_golden_controls,
    load_golden_controls,
)
from ml_model.retraining.experiment_contract import load_experiment_config, sha256_file
from ml_model.retraining.prediction_artifacts import (
    records_from_golden_evaluation,
    write_prediction_artifact,
)


def extract_baseline_metrics(
    eval_report: Mapping[str, Any],
    *,
    summary_metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize existing evaluation metadata without inventing missing rates."""

    summary = summary_metrics or {}
    macro = eval_report.get("macro avg", {})
    normal = eval_report.get("Normal", {})
    per_class = eval_report.get("per_class", {})
    if not isinstance(per_class, Mapping) or not per_class:
        per_class = {
            label: value
            for label, value in eval_report.items()
            if label not in {"accuracy", "macro avg", "weighted avg"}
            and isinstance(value, Mapping)
        }
    supported = {
        str(label): float(values.get("recall"))
        for label, values in per_class.items()
        if label != "Normal"
        and isinstance(values, Mapping)
        and values.get("recall") is not None
    }
    normal_false_positive_rate = eval_report.get("normal_false_positive_rate")
    if normal_false_positive_rate is None:
        normal_false_positive_rate = summary.get("normal_false_positive_rate")
    attack_escape_rate = eval_report.get("attack_escape_rate")
    if attack_escape_rate is None:
        attack_escape_rate = summary.get("attack_escape_rate")
    macro_f1 = eval_report.get("macro_f1")
    if macro_f1 is None:
        macro_f1 = macro.get("f1-score")
    if macro_f1 is None:
        macro_f1 = summary.get("test_macro_f1")
    return {
        "normal_false_positive_rate": _optional_float(normal_false_positive_rate),
        "attack_escape_rate": _optional_float(attack_escape_rate),
        "macro_f1": _optional_float(macro_f1),
        "normal_recall": _optional_float(normal.get("recall")),
        "supported_attack_recall": supported,
    }


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _missing_baseline_metrics(
    metrics: Mapping[str, Any], label_names: tuple[str, ...]
) -> list[str]:
    missing = [
        key
        for key in (
            "normal_false_positive_rate",
            "attack_escape_rate",
            "macro_f1",
            "normal_recall",
        )
        if metrics.get(key) is None
    ]
    required_labels = {label for label in label_names if label != "Normal"}
    missing_attack_recall = sorted(
        label
        for label in required_labels
        if label not in metrics.get("supported_attack_recall", {})
    )
    if missing_attack_recall:
        missing.append("supported_attack_recall:" + ",".join(missing_attack_recall))
    return missing


def evaluate_baseline_gate(
    *,
    metrics: Mapping[str, Any],
    label_names: tuple[str, ...],
    service_loaded: bool,
    golden_passed: bool,
    reload_verified: bool,
) -> dict[str, Any]:
    """Return the complete, fail-closed gate for a frozen baseline artifact."""

    missing_metrics = _missing_baseline_metrics(metrics, label_names)
    checks = {
        "metrics_complete": not missing_metrics,
        "model_loaded": bool(service_loaded),
        "golden_controls_passed": bool(golden_passed),
        "local_reload_verified": bool(reload_verified),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "missing_required_metrics": missing_metrics,
    }


def _failed_golden_result(
    controls: Any,
    reason: str,
) -> dict[str, Any]:
    return {
        "passed": False,
        "cases": [],
        "category_results": {},
        "mandatory_failures": [reason],
        "manifest_sha256": str(controls.manifest["manifest_sha256"]),
        "manifest_file_sha256": sha256_file(controls.manifest_path),
    }


def _build_golden_scope_summaries(
    controls: Any, golden: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Summarize target-route coverage and retain the legacy regression view."""

    results_by_id = {
        str(result.get("case_id")): result
        for result in golden.get("cases", [])
        if isinstance(result, Mapping)
    }
    target_cases = [
        case for case in controls.cases if case.get("route_scope") == "target_route"
    ]
    target_case_ids = [str(case["case_id"]) for case in target_cases]
    target_results = [results_by_id.get(case_id) for case_id in target_case_ids]
    target_results = [
        result for result in target_results if isinstance(result, Mapping)
    ]
    target_summary = {
        "method": controls.manifest.get("target_method"),
        "route": controls.manifest.get("target_route"),
        "case_count": len(target_case_ids),
        "passed": bool(target_case_ids)
        and len(target_results) == len(target_case_ids)
        and all(bool(result.get("passed")) for result in target_results),
        "failed_case_ids": sorted(
            str(result["case_id"])
            for result in target_results
            if not result.get("passed")
        ),
    }
    legacy_case = next(
        (
            case
            for case in controls.cases
            if case.get("route_scope") == "legacy_regression"
        ),
        None,
    )
    legacy_result = (
        dict(results_by_id.get(str(legacy_case["case_id"]), {}))
        if legacy_case is not None
        else {}
    )
    if legacy_case is not None:
        legacy_result.update(
            {
                "request_method": legacy_case.get("request_method"),
                "request_path": legacy_case.get("request_path"),
                "route_scope": legacy_case.get("route_scope"),
            }
        )
    return target_summary, legacy_result


def build_baseline_report(
    *,
    artifact_dir: Path | str,
    config_path: Path | str,
    output_path: Path | str,
) -> dict[str, Any]:
    artifact = Path(artifact_dir).expanduser().resolve()
    config = load_experiment_config(config_path)
    destination = Path(output_path).expanduser().resolve()
    controls = load_golden_controls(config.golden_manifest_file)
    from web_app.config import Settings
    from web_app.services.model_service import ModelService

    model_load_error = None
    try:
        service = ModelService(
            Settings(
                database_url="sqlite+aiosqlite://",
                app_env="development",
                model_path="unused",
                model_registry_path=str(artifact),
                api_secret_key="controlled-retraining-baseline-check",
            )
        )
    except Exception as exc:
        service = None
        model_load_error = str(exc)
    service_loaded = bool(service is not None and service.loaded)
    if not service_loaded:
        golden = _failed_golden_result(controls, "model_not_loaded")
    else:
        try:
            golden = evaluate_golden_controls(
                controls,
                service.predict,
                confidence_thresholds=config.confidence_thresholds,
                response_actions=config.response_actions,
            ).to_dict()
        except Exception as exc:
            golden = _failed_golden_result(controls, "golden_evaluation_failed")
            golden["error"] = str(exc)
    eval_report_path = artifact / "eval_report.json"
    eval_report = (
        json.loads(eval_report_path.read_text(encoding="utf-8"))
        if eval_report_path.is_file()
        else {}
    )
    summary_metrics_path = artifact / "summary_metrics.json"
    loaded_summary_metrics = (
        json.loads(summary_metrics_path.read_text(encoding="utf-8"))
        if summary_metrics_path.is_file()
        else {}
    )
    summary_metrics = (
        loaded_summary_metrics if isinstance(loaded_summary_metrics, Mapping) else {}
    )
    metrics = extract_baseline_metrics(
        eval_report,
        summary_metrics=summary_metrics,
    )
    manifest_path = artifact / "serving_manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {}
    )
    prediction_path = destination.parent / "baseline_predictions.json"
    model_version = str(manifest.get("model_version", artifact.name))
    prediction_artifact_status = "NOT_WRITTEN"
    prediction_artifact_error = None
    if service_loaded and manifest_path.is_file():
        try:
            write_prediction_artifact(
                prediction_path,
                records_from_golden_evaluation(
                    controls.cases,
                    golden,
                    model_version=model_version,
                    dataset_version=config.historical_dataset_version,
                    golden_version=config.golden_version,
                ),
                model_version=model_version,
                dataset_version=config.historical_dataset_version,
                golden_version=config.golden_version,
                golden_manifest_sha256=str(golden["manifest_sha256"]),
                model_artifact_sha256=sha256_file(manifest_path),
            )
            prediction_artifact_status = "WRITTEN"
        except (OSError, TypeError, ValueError, KeyError) as exc:
            prediction_artifact_error = str(exc)
    else:
        prediction_artifact_error = (
            "model is not loaded"
            if not service_loaded
            else "serving_manifest.json is missing"
        )
    file_hashes = {
        path.name: sha256_file(path)
        for path in sorted(artifact.iterdir())
        if path.is_file()
        and path.suffix.lower() in {".pt", ".safetensors", ".json", ".txt"}
    }
    target_route_controls, legacy_regression = _build_golden_scope_summaries(
        controls, golden
    )
    missing_metrics = _missing_baseline_metrics(metrics, config.label_names)
    baseline_gate = evaluate_baseline_gate(
        metrics=metrics,
        label_names=config.label_names,
        service_loaded=service_loaded,
        golden_passed=bool(golden.get("passed")),
        reload_verified=manifest.get("local_reload_verified") is True,
    )
    baseline_ready = bool(baseline_gate["passed"])
    try:
        prediction_reference = str(prediction_path.relative_to(config.project_root))
    except ValueError:
        prediction_reference = str(prediction_path)
    report = {
        "status": "PASS" if baseline_ready else "PARTIAL",
        "baseline_status": "FROZEN" if baseline_ready else "REQUIRES_LAPTOP",
        "model_quality_conclusion": (
            "READY_FOR_EXPERIMENT" if baseline_ready else "NOT_PERMITTED"
        ),
        "execution_boundary": (
            "current staged artifact direct ModelService and locked golden controls"
        ),
        "training_status": "NOT_RUN",
        "artifact_argument": str(artifact_dir),
        "artifact_identity": {
            "model_version": manifest.get("model_version", artifact.name),
            "model_key": manifest.get("model_key", "distilbert"),
            "model_revision": manifest.get("model_revision"),
            "checkpoint_sha256": manifest.get("checkpoint_sha256"),
            "files_sha256": file_hashes,
        },
        "metrics": metrics,
        "missing_required_metrics": missing_metrics,
        "baseline_gate": baseline_gate,
        "golden": golden,
        "prediction_artifact": (
            prediction_reference if prediction_artifact_status == "WRITTEN" else None
        ),
        "prediction_artifact_status": prediction_artifact_status,
        "prediction_artifact_error": prediction_artifact_error,
        "target_route_controls": target_route_controls,
        "legacy_regression": legacy_regression,
        # Compatibility alias for consumers of the original baseline schema.
        "exact_pagination": legacy_regression,
        "packaging_status": "VERIFIED_FROM_MANIFEST"
        if manifest.get("local_reload_verified")
        else "UNKNOWN",
        "backend_status": "PASS" if service_loaded else "FAIL",
        "backend_error": model_load_error,
        "waf_status": "NOT_RUN",
        "dashboard_status": "NOT_RUN",
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = build_baseline_report(
        artifact_dir=args.artifact_dir,
        config_path=args.config,
        output_path=args.output,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
