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


def extract_baseline_metrics(eval_report: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize existing evaluation metadata without inventing missing rates."""

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
    return {
        "normal_false_positive_rate": _optional_float(
            eval_report.get("normal_false_positive_rate")
        ),
        "attack_escape_rate": _optional_float(eval_report.get("attack_escape_rate")),
        "macro_f1": _optional_float(eval_report.get("macro_f1", macro.get("f1-score"))),
        "normal_recall": _optional_float(normal.get("recall")),
        "supported_attack_recall": supported,
    }


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def build_baseline_report(
    *,
    artifact_dir: Path | str,
    config_path: Path | str,
    output_path: Path | str,
) -> dict[str, Any]:
    artifact = Path(artifact_dir).expanduser().resolve()
    config = load_experiment_config(config_path)
    controls = load_golden_controls(config.golden_manifest_file)
    from web_app.config import Settings
    from web_app.services.model_service import ModelService

    service = ModelService(
        Settings(
            database_url="sqlite+aiosqlite://",
            app_env="development",
            model_path="unused",
            model_registry_path=str(artifact),
            api_secret_key="controlled-retraining-baseline-check",
        )
    )
    golden = evaluate_golden_controls(controls, service.predict).to_dict()
    eval_report_path = artifact / "eval_report.json"
    eval_report = (
        json.loads(eval_report_path.read_text(encoding="utf-8"))
        if eval_report_path.is_file()
        else {}
    )
    metrics = extract_baseline_metrics(eval_report)
    manifest_path = artifact / "serving_manifest.json"
    manifest = (
        json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest_path.is_file()
        else {}
    )
    file_hashes = {
        path.name: sha256_file(path)
        for path in sorted(artifact.iterdir())
        if path.is_file()
        and path.suffix.lower() in {".pt", ".safetensors", ".json", ".txt"}
    }
    exact = next(
        (
            case
            for case in golden["cases"]
            if case["case_id"] == "normal-pagination-exact"
        ),
        {},
    )
    missing_metrics = [
        key
        for key in (
            "normal_false_positive_rate",
            "attack_escape_rate",
            "macro_f1",
            "normal_recall",
        )
        if metrics.get(key) is None
    ]
    report = {
        "status": "PASS"
        if service.loaded and golden["passed"] and not missing_metrics
        else "PARTIAL",
        "execution_boundary": "current staged artifact direct ModelService and locked golden controls",
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
        "golden": golden,
        "exact_pagination": exact,
        "packaging_status": "VERIFIED_FROM_MANIFEST"
        if manifest.get("local_reload_verified")
        else "UNKNOWN",
        "backend_status": "PASS" if service.loaded else "FAIL",
        "waf_status": "NOT_RUN",
        "dashboard_status": "NOT_RUN",
    }
    destination = Path(output_path).expanduser().resolve()
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
