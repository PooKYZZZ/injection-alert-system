from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import torch

from ml_model.export.package_serving_artifact import package_serving_artifact
from ml_model.preprocessing.model_input import (
    MODEL_INPUT_HASH_POLICY,
    validate_supported_model_input_version,
)
from ml_model.training.run_contract import require_contract_hash

DEFAULT_LABEL_NAMES = ["Code Injection", "Normal", "Other Attacks", "SQL Injection"]
REQUIRED_FINAL_TRAINING_FILES = (
    "config_metadata.json",
    "summary_metrics.json",
    "per_class_metrics.json",
    "calibration.json",
)
DEFAULT_CHECKPOINT_FILENAME = "best_distilbert_weighted_ce_seed2026.pt"
SUPPORTED_ARCHITECTURES = {
    "distilbert_sequence_classification",
    "transformer",
    "legacy_transformer",
}


class PromotionError(RuntimeError):
    """Raised when promotion inputs or outputs are invalid."""


@dataclass
class PromotionResult:
    active_run_dir: Path
    archived_run_dir: Path | None
    eval_run_dir: Path | None
    dry_run: bool


def validate_final_training_source(
    source_dir: Path,
    checkpoint_filename: str = DEFAULT_CHECKPOINT_FILENAME,
) -> dict[str, Path]:
    source_path = Path(source_dir)
    expected_files = {
        name: source_path / name for name in REQUIRED_FINAL_TRAINING_FILES
    }
    checkpoint_path = source_path / "checkpoint" / checkpoint_filename

    for path in [*expected_files.values(), checkpoint_path]:
        if not path.exists() or not path.is_file():
            raise PromotionError(f"Missing required final-training file: {path}")

    return {
        **expected_files,
        "checkpoint": checkpoint_path,
    }


def validate_label_names(label_names: list[str]) -> list[str]:
    if list(label_names) != DEFAULT_LABEL_NAMES:
        raise PromotionError(
            "Final-training label names do not match serving contract label names."
        )
    return list(DEFAULT_LABEL_NAMES)


def extract_calibration_temperature(calibration_payload: dict[str, Any]) -> float:
    raw_temperature = calibration_payload.get("temperature")
    if raw_temperature is None:
        raise PromotionError("Calibration payload is missing temperature.")

    try:
        temperature = float(raw_temperature)
    except (TypeError, ValueError) as exc:
        raise PromotionError("Calibration payload temperature must be numeric.") from exc

    if not math.isfinite(temperature):
        raise PromotionError("Calibration payload temperature must be finite.")

    return temperature


def archive_existing_run(
    *,
    active_run_dir: Path,
    archive_root: Path,
    archive_suffix: str,
) -> Path:
    active_dir = Path(active_run_dir)
    if not active_dir.exists() or not active_dir.is_dir():
        raise PromotionError(f"Active run directory does not exist: {active_dir}")

    archive_dir = Path(archive_root)
    archive_dir.mkdir(parents=True, exist_ok=True)

    archive_target = archive_dir / f"{active_dir.name}_{archive_suffix}"
    if archive_target.exists():
        raise PromotionError(f"Archive target already exists: {archive_target}")

    moved_path = Path(shutil.move(str(active_dir), str(archive_target)))
    return moved_path


def create_fresh_active_run_dir(active_run_dir: Path) -> Path:
    active_dir = Path(active_run_dir)
    active_dir.mkdir(parents=True, exist_ok=False)
    return active_dir


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


def write_text(path: Path, text: str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return output_path


def build_provenance_payload(
    *,
    model_name: str,
    promoted_version: str,
    checkpoint_sha256: str,
    archived_path: str,
    repo_commit: str,
    calibration_temperature: float,
    validation_gates: dict[str, bool],
    source_checkpoint_path: str = "",
    dataset_version: str = "",
    label_names: list[str] | None = None,
) -> dict[str, Any]:
    effective_label_names = list(label_names or DEFAULT_LABEL_NAMES)
    artifact_packaging_ready = bool(
        validation_gates.get("artifact_packaging_pipeline_passed")
        and validation_gates.get("local_reload_validated")
    )
    quality_gates_passed = bool(validation_gates.get("quality_gates_passed"))
    source_validation_passed = bool(
        validation_gates.get("source_validation_passed")
    )
    checkpoint_hash_recorded = (
        len(checkpoint_sha256) == 64
        and all(
            character in "0123456789abcdefABCDEF"
            for character in checkpoint_sha256
        )
    )
    labels_validated = (
        label_names is not None and effective_label_names == DEFAULT_LABEL_NAMES
    )
    ready_for_promotion = bool(
        artifact_packaging_ready
        and quality_gates_passed
        and source_validation_passed
        and checkpoint_hash_recorded
        and labels_validated
    )
    return {
        "model_name": model_name,
        "promoted_version": promoted_version,
        "generated_at_utc": datetime.now(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z"),
        "checkpoint_identity": {
            "checkpoint_path": source_checkpoint_path,
            "checkpoint_sha256": checkpoint_sha256,
        },
        "dataset_version": dataset_version,
        "repo_commit": repo_commit,
        "calibration_temperature": float(calibration_temperature),
        "label_names": effective_label_names,
        "previous_version_archived_to": archived_path,
        "validation_gates_passed": dict(validation_gates),
        "artifact_packaging_ready": artifact_packaging_ready,
        "quality_gates_passed": quality_gates_passed,
        "source_validation_passed": source_validation_passed,
        "checkpoint_hash_recorded": checkpoint_hash_recorded,
        "labels_validated": labels_validated,
        "ready_for_promotion": ready_for_promotion,
    }


def build_model_card(
    *,
    model_version: str,
    archived_version: str,
    summary_metrics: dict[str, Any],
    label_names: list[str],
) -> str:
    lines = [
        "# DistilBERT Injection Detector",
        "",
        f"## Active version",
        f"- {model_version}",
        "",
        "## Summary metrics",
    ]

    for metric_name, metric_value in summary_metrics.items():
        lines.append(f"- {metric_name}: {metric_value}")

    lines.extend(
        [
            "",
            "## Label names",
            *[f"- {name}" for name in label_names],
            "",
            "## Version history",
            f"- Current active: {model_version}",
            f"- Previous active archived as: {archived_version}",
            "",
        ]
    )
    return "\n".join(lines)


def sha256_file(path: Path) -> str:
    digest = torch.sha256sum(path.read_bytes()) if hasattr(torch, "sha256sum") else None
    if isinstance(digest, str):
        return digest

    import hashlib

    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_repo_commit(repo_root: Path) -> str:
    repo_path = Path(repo_root)
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def write_eval_provenance_files(
    *,
    eval_root: Path,
    model_key: str,
    run_dir_name: str,
    temperature: float,
    repo_commit: str,
    dataset_version: str,
    artifact_packaging_pipeline_passed: bool,
    local_reload_validated: bool,
    quality_gates_passed: bool,
    eval_run_dir: Path | None = None,
) -> Path:
    if eval_run_dir is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        eval_run_dir = Path(eval_root) / timestamp
        if eval_run_dir.exists():
            raise PromotionError(f"Evaluation provenance directory already exists: {eval_run_dir}")
        eval_run_dir.mkdir(parents=True, exist_ok=False)
    else:
        eval_run_dir = Path(eval_run_dir)
        if not eval_run_dir.is_dir() or eval_run_dir.parent.resolve() != Path(eval_root).resolve():
            raise PromotionError(
                "Evaluation provenance updates must target an existing direct child of "
                f"'{Path(eval_root)}'."
            )
        timestamp = eval_run_dir.name

    promotion_summary = {
        "timestamp": timestamp,
        "dataset_version": dataset_version,
        "promotion_summary": {
            model_key: {
                "artifact_packaging_ready": bool(
                    artifact_packaging_pipeline_passed
                    and local_reload_validated
                ),
                "quality_gates_passed": quality_gates_passed,
                "ready_for_promotion": False,
                "gates": {
                    "artifact_packaging_pipeline_passed": (
                        artifact_packaging_pipeline_passed
                    ),
                    "local_reload_validated": local_reload_validated,
                    "quality_gates_passed": quality_gates_passed,
                },
                "temperature": float(temperature),
                "git_hash": repo_commit,
                "run_dir": run_dir_name,
            }
        },
    }
    write_json(eval_run_dir / "promotion_summary.json", promotion_summary)
    write_json(
        eval_run_dir / f"eval_results_{model_key}_calibrated.json",
        {"temperature": float(temperature)},
    )
    return eval_run_dir


def validate_local_reload(
    *,
    active_run_dir: Path,
    repo_root: Path,
    expected_model_version: str,
) -> None:
    del repo_root
    from web_app.config import Settings
    from web_app.services.model_service import ModelService

    settings = Settings(
        database_url="sqlite+aiosqlite://",
        app_env="development",
        model_path="unused",
        model_registry_path=str(Path(active_run_dir)),
        api_secret_key="promotion-local-reload",
    )
    service = ModelService(settings)
    if service.model_version != expected_model_version:
        raise PromotionError(
            "Local reload validation failed: "
            f"expected '{expected_model_version}', got '{service.model_version}'."
        )


def run_packager(
    *,
    model_key: str,
    run_dir_name: str,
    notes: str | None,
    calibration_eval_run_dir: Path,
) -> Path:
    return package_serving_artifact(
        model_key=model_key,
        run_dir_name=run_dir_name,
        discover_latest=False,
        overwrite=True,
        strict=True,
        notes=notes,
        calibration_eval_run_dir=calibration_eval_run_dir,
    )


def restore_archived_run(*, archived_run_dir: Path, active_run_dir: Path) -> Path:
    archived_dir = Path(archived_run_dir)
    active_dir = Path(active_run_dir)

    if not archived_dir.exists() or not archived_dir.is_dir():
        raise PromotionError(f"Archived run directory does not exist: {archived_dir}")
    if active_dir.exists():
        raise PromotionError(
            f"Cannot restore archived run because active path already exists: {active_dir}"
        )

    active_dir.parent.mkdir(parents=True, exist_ok=True)
    restored_path = Path(shutil.move(str(archived_dir), str(active_dir)))
    return restored_path


def _validate_architecture(architecture: Any) -> str:
    if not isinstance(architecture, str) or not architecture.strip():
        raise PromotionError(f"Unsupported or missing architecture: {architecture!r}")
    normalized = architecture.strip()
    if normalized not in SUPPORTED_ARCHITECTURES:
        raise PromotionError(f"Unsupported or missing architecture: {architecture!r}")
    return normalized


def validate_native_promotion_metadata(config_metadata: Mapping[str, Any]) -> None:
    """Fail closed unless metadata describes the maintained native model."""

    expected = {
        "model_key": "distilbert",
        "model_id": "distilbert-base-uncased",
        "architecture": "distilbert_sequence_classification",
        "architecture_family": "huggingface_sequence_classifier",
        "head_type": "hf_sequence_classification_head",
        "model_class": "DistilBertForSequenceClassification",
    }
    for field, expected_value in expected.items():
        if config_metadata.get(field) != expected_value:
            raise PromotionError(
                "Native DistilBERT promotion requires "
                f"{field}={expected_value!r}; got {config_metadata.get(field)!r}."
            )
    revision = config_metadata.get("model_revision")
    if (
        not isinstance(revision, str)
        or not revision.strip()
        or revision.strip().lower() == "unresolved"
    ):
        raise PromotionError(
            "Native DistilBERT promotion requires a pinned model_revision."
        )


def _normalize_legacy_custom_transformer_state_dict(
    state_dict: Mapping[str, Any],
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in state_dict.items():
        mapped_key = key
        if key.startswith("encoder."):
            mapped_key = "distilbert." + key[len("encoder.") :]
        elif key == "classifier_dense.weight":
            mapped_key = "pre_classifier.weight"
        elif key == "classifier_dense.bias":
            mapped_key = "pre_classifier.bias"
        elif key == "output.weight":
            mapped_key = "classifier.weight"
        elif key == "output.bias":
            mapped_key = "classifier.bias"
        elif key in {"layer_norm.weight", "layer_norm.bias"}:
            continue
        normalized[mapped_key] = value
    return normalized


def normalize_state_dict_for_packager(
    state_dict: Mapping[str, Any],
    *,
    architecture: str | None,
) -> dict[str, Any]:
    architecture = _validate_architecture(architecture)
    if architecture == "distilbert_sequence_classification":
        required_prefixes = ("distilbert.", "pre_classifier.", "classifier.")
        if not all(
            any(key.startswith(prefix) for key in state_dict)
            for prefix in required_prefixes
        ):
            raise PromotionError(
                "Native DistilBERT checkpoint must preserve distilbert.*, "
                "pre_classifier.*, and classifier.* keys."
            )
        if any(
            key.startswith(("encoder.", "classifier_dense.", "layer_norm.", "output."))
            for key in state_dict
        ):
            raise PromotionError(
                "Native DistilBERT checkpoint contains custom-model keys."
            )
        return dict(state_dict)
    if architecture == "legacy_transformer":
        return _normalize_legacy_custom_transformer_state_dict(state_dict)
    raise PromotionError(
        "Generic transformer architecture cannot be promoted or normalized; "
        "use the explicitly named legacy_transformer path."
    )


def _load_architecture_from_run_metadata(
    run_dir: Path,
    *,
    config_metadata: Mapping[str, Any] | None = None,
) -> str:
    candidates: list[Mapping[str, Any]] = []
    if config_metadata is not None:
        candidates.append(config_metadata)
    for filename in ("config_metadata.json", "config_used.json"):
        metadata_path = Path(run_dir) / filename
        if metadata_path.exists():
            payload = load_json(metadata_path)
            if isinstance(payload, dict):
                candidates.append(payload)

    for payload in candidates:
        if "architecture" in payload:
            return _validate_architecture(payload.get("architecture"))
    raise PromotionError(
        f"Unsupported or missing architecture metadata in training run: {Path(run_dir)}"
    )


def extract_state_dict_checkpoint(
    source_path: Path,
    target_path: Path,
    *,
    normalize_for_packager: bool = False,
    architecture: str | None = None,
) -> None:
    source = Path(source_path)
    target = Path(target_path)

    checkpoint = torch.load(source, map_location="cpu", weights_only=True)
    if not isinstance(checkpoint, dict) or "model_state_dict" not in checkpoint:
        raise PromotionError(
            f"Checkpoint at '{source}' does not contain a model_state_dict payload."
        )

    state_dict = checkpoint["model_state_dict"]
    if not isinstance(state_dict, dict):
        raise PromotionError(
            f"Checkpoint at '{source}' has a non-dict model_state_dict payload."
        )

    if normalize_for_packager:
        resolved_architecture = (
            _load_architecture_from_run_metadata(
                source.parent.parent if source.parent.name == "checkpoint" else source.parent
            )
            if architecture is None
            else architecture
        )
        state_dict = normalize_state_dict_for_packager(
            state_dict,
            architecture=resolved_architecture,
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    torch.save(state_dict, target)


def build_config_used(
    *,
    config_metadata: dict[str, Any],
    model_version: str,
) -> dict[str, Any]:
    validate_native_promotion_metadata(config_metadata)
    preprocessing_version = validate_supported_model_input_version(
        config_metadata.get("preprocessing_version"), context="final training run"
    )
    if config_metadata.get("model_input_hash_policy") != MODEL_INPUT_HASH_POLICY:
        raise PromotionError(
            "Final training metadata is missing the shared model-input hash policy."
        )
    try:
        contract_hash = require_contract_hash(config_metadata)
    except ValueError as exc:
        raise PromotionError(str(exc)) from exc
    config_used = {
        "model_key": config_metadata.get("model_key", "distilbert"),
        "model_id": config_metadata.get("model_id", "distilbert-base-uncased"),
        "model_revision": config_metadata.get("model_revision"),
        "tokenizer_id": config_metadata.get(
            "tokenizer_id", config_metadata.get("model_id")
        ),
        "tokenizer_revision": config_metadata.get(
            "tokenizer_revision", config_metadata.get("model_revision")
        ),
        "architecture": config_metadata.get("architecture"),
        "architecture_family": config_metadata.get("architecture_family"),
        "head_type": config_metadata.get("head_type"),
        "model_class": config_metadata.get("model_class"),
        "dataset_version": config_metadata.get("dataset_version"),
        "preprocessing_version": preprocessing_version,
        "model_input_hash_policy": config_metadata.get("model_input_hash_policy"),
        "max_seq_len": int(config_metadata.get("max_seq_len", 128)),
        "seed": config_metadata.get("seed"),
        "model_version": model_version,
        "label_names": list(DEFAULT_LABEL_NAMES),
        "run_contract_sha256": contract_hash,
    }
    if "run_contract" in config_metadata:
        config_used["run_contract"] = config_metadata["run_contract"]
    return config_used


def build_eval_report(
    *,
    summary_metrics: dict[str, Any],
    per_class_metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "accuracy": float(summary_metrics["test_accuracy"]),
        "macro avg": {
            "precision": float(summary_metrics.get("test_macro_precision", 0.0)),
            "recall": float(summary_metrics.get("test_macro_recall", 0.0)),
            "f1-score": float(summary_metrics["test_macro_f1"]),
            "support": float(summary_metrics.get("test_support", 0.0)),
        },
        "weighted avg": {
            "precision": float(summary_metrics.get("test_weighted_precision", 0.0)),
            "recall": float(summary_metrics.get("test_weighted_recall", 0.0)),
            "f1-score": float(summary_metrics["test_weighted_f1"]),
            "support": float(summary_metrics.get("test_support", 0.0)),
        },
    }

    for row in per_class_metrics:
        label_name = str(row["label_name"])
        report[label_name] = {
            "precision": float(row["precision"]),
            "recall": float(row["recall"]),
            "f1-score": float(row["f1"]),
            "support": float(row["support"]),
        }

    return report


def promote_final_training_run(
    *,
    source_dir: Path,
    active_run_dir: Path,
    archive_root: Path,
    repo_root: Path,
    checkpoint_filename: str = DEFAULT_CHECKPOINT_FILENAME,
    archive_suffix: str = "pre_20260420",
    notes: str | None = None,
    dry_run: bool = False,
) -> PromotionResult:
    source_paths = validate_final_training_source(source_dir, checkpoint_filename)
    config_metadata = load_json(source_paths["config_metadata.json"])
    architecture = _load_architecture_from_run_metadata(
        Path(source_dir),
        config_metadata=config_metadata,
    )
    config_metadata = {**config_metadata, "architecture": architecture}
    validate_native_promotion_metadata(config_metadata)
    summary_metrics = load_json(source_paths["summary_metrics.json"])
    per_class_metrics = load_json(source_paths["per_class_metrics.json"])
    calibration_payload = load_json(source_paths["calibration.json"])

    if not isinstance(per_class_metrics, list):
        raise PromotionError("Per-class metrics payload must be a list.")

    label_names = validate_label_names(
        [str(row["label_name"]) for row in per_class_metrics if isinstance(row, dict)]
    )
    calibration_temperature = extract_calibration_temperature(calibration_payload)
    active_dir = Path(active_run_dir)
    model_key = str(config_metadata.get("model_key", "distilbert"))
    model_version = active_dir.name
    config_used = build_config_used(config_metadata=config_metadata, model_version=model_version)
    eval_report = build_eval_report(
        summary_metrics=summary_metrics,
        per_class_metrics=per_class_metrics,
    )
    repo_commit = resolve_repo_commit(Path(repo_root))
    checkpoint_sha256 = sha256_file(source_paths["checkpoint"])

    if dry_run:
        print("DRY RUN: no filesystem changes will be made.")
        print(f"- validate source: {Path(source_dir)}")
        print(f"- archive active run: {Path(active_run_dir)} -> {Path(archive_root)}")
        print(f"- recreate active run directory: {Path(active_run_dir)}")
        print(f"- write checkpoint/config/eval/git_hash into: {Path(active_run_dir)}")
        print(
            "- write eval provenance under: "
            f"{Path(repo_root) / 'ml_model' / 'model_registry' / 'eval'}"
        )
        print(f"- run packager for run: {active_dir.name}")
        print(f"- write provenance/model card in: {Path(active_run_dir)}")
        print(f"- expected checkpoint sha256: {checkpoint_sha256}")
        return PromotionResult(
            active_run_dir=active_dir,
            archived_run_dir=None,
            eval_run_dir=None,
            dry_run=True,
        )

    archived_dir: Path | None = None
    eval_run_dir: Path | None = None
    try:
        archived_dir = archive_existing_run(
            active_run_dir=active_dir,
            archive_root=archive_root,
            archive_suffix=archive_suffix,
        )
        fresh_active_dir = create_fresh_active_run_dir(active_dir)

        extract_state_dict_checkpoint(
            source_paths["checkpoint"],
            fresh_active_dir / f"best_{model_key}_ckpt.pt",
            normalize_for_packager=True,
            architecture=architecture,
        )
        write_json(fresh_active_dir / "config_used.json", config_used)
        write_json(fresh_active_dir / "eval_report.json", eval_report)
        write_text(fresh_active_dir / "git_hash.txt", f"{repo_commit}\n")

        eval_run_dir = write_eval_provenance_files(
            eval_root=Path(repo_root) / "ml_model" / "model_registry" / "eval",
            model_key=model_key,
            run_dir_name=fresh_active_dir.name,
            temperature=calibration_temperature,
            repo_commit=repo_commit,
            dataset_version=str(config_used.get("dataset_version", "")),
            artifact_packaging_pipeline_passed=False,
            local_reload_validated=False,
            quality_gates_passed=False,
        )

        packaged_run_dir = run_packager(
            model_key=model_key,
            run_dir_name=fresh_active_dir.name,
            notes=notes,
            calibration_eval_run_dir=eval_run_dir,
        )

        validation_gates = {
            "source_validation_passed": True,
            "artifact_packaging_pipeline_passed": True,
            "local_reload_validated": False,
            "quality_gates_passed": False,
        }
        validate_local_reload(
            active_run_dir=packaged_run_dir,
            repo_root=repo_root,
            expected_model_version=fresh_active_dir.name,
        )
        validation_gates["local_reload_validated"] = True

        write_eval_provenance_files(
            eval_root=Path(repo_root) / "ml_model" / "model_registry" / "eval",
            model_key=model_key,
            run_dir_name=fresh_active_dir.name,
            temperature=calibration_temperature,
            repo_commit=repo_commit,
            dataset_version=str(config_used.get("dataset_version", "")),
            artifact_packaging_pipeline_passed=True,
            local_reload_validated=True,
            quality_gates_passed=False,
            eval_run_dir=eval_run_dir,
        )

        provenance = build_provenance_payload(
            model_name="distilbert-injection-detector",
            promoted_version=fresh_active_dir.name,
            checkpoint_sha256=checkpoint_sha256,
            archived_path=str(archived_dir),
            repo_commit=repo_commit,
            calibration_temperature=calibration_temperature,
            validation_gates=validation_gates,
            source_checkpoint_path=str(source_paths["checkpoint"]),
            dataset_version=str(config_used.get("dataset_version", "")),
            label_names=label_names,
        )
        write_json(packaged_run_dir / "provenance.json", provenance)

        model_card = build_model_card(
            model_version=fresh_active_dir.name,
            archived_version=archived_dir.name,
            summary_metrics=summary_metrics,
            label_names=label_names,
        )
        write_text(packaged_run_dir / "MODEL_CARD.md", model_card)

        return PromotionResult(
            active_run_dir=packaged_run_dir,
            archived_run_dir=archived_dir,
            eval_run_dir=eval_run_dir,
            dry_run=False,
        )
    except Exception as exc:
        if eval_run_dir is not None and eval_run_dir.exists():
            shutil.rmtree(eval_run_dir)
        if archived_dir is not None and archived_dir.exists():
            broken_active = Path(active_run_dir)
            if broken_active.exists():
                shutil.rmtree(broken_active)
            try:
                restore_archived_run(
                    archived_run_dir=archived_dir,
                    active_run_dir=broken_active,
                )
            except Exception as restore_exc:  # pragma: no cover - defensive branch
                raise PromotionError(
                    "Promotion failed and rollback restore also failed."
                ) from restore_exc
        if isinstance(exc, PromotionError):
            raise
        raise PromotionError(str(exc)) from exc


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Promote a final-training DistilBERT run into staged serving artifacts.",
    )
    parser.add_argument(
        "--source-run-dir",
        required=True,
        type=Path,
        help="Path to final-training source run directory (seed_2026).",
    )
    parser.add_argument(
        "--active-run-dir",
        required=True,
        type=Path,
        help="Path to active staged run directory to replace after archive-and-recreate.",
    )
    parser.add_argument(
        "--archive-root",
        required=True,
        type=Path,
        help="Root directory where archived staged runs are moved.",
    )
    parser.add_argument(
        "--checkpoint-filename",
        default=DEFAULT_CHECKPOINT_FILENAME,
        help="Checkpoint filename inside source-run-dir/checkpoint/.",
    )
    parser.add_argument(
        "--archive-suffix",
        default="pre_20260420",
        help="Deterministic suffix appended to archived run directory name.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions only without writing, moving, or packaging.",
    )
    parser.add_argument(
        "--notes",
        default=None,
        help="Optional operator notes passed to the packager manifest.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> PromotionResult:
    args = parse_args(argv)
    result = promote_final_training_run(
        source_dir=args.source_run_dir,
        active_run_dir=args.active_run_dir,
        archive_root=args.archive_root,
        repo_root=Path.cwd().resolve(),
        checkpoint_filename=args.checkpoint_filename,
        archive_suffix=args.archive_suffix,
        notes=args.notes,
        dry_run=args.dry_run,
    )
    print(f"Promotion complete. dry_run={result.dry_run} active_run={result.active_run_dir}")
    return result


if __name__ == "__main__":
    main()
