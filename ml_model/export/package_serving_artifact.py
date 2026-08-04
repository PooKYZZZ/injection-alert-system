"""Package one exact staged model run into a reproducible local serving artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
import transformers
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from ml_model.preprocessing.model_input import (
    MODEL_INPUT_HASH_POLICY,
    validate_supported_model_input_version,
)

DEFAULT_LABEL_NAMES = ["Code Injection", "Normal", "Other Attacks", "SQL Injection"]
MODEL_IDS = {
    "minilm": "nreimers/MiniLM-L6-H384-uncased",
    "distilbert": "distilbert-base-uncased",
    "bert-base": "bert-base-uncased",
}
PACKAGING_TOOL = "ml_model/export/package_serving_artifact.py"
DEFAULT_SAMPLE_TEXT = "SELECT * FROM users WHERE 1=1 --"
DEVICE = torch.device("cpu")
REQUIRED_RUN_FILES = ("config_used.json", "eval_report.json", "git_hash.txt")
MANIFEST_NAME = "serving_manifest.json"
SUMMARY_METRIC_KEYS = {"accuracy", "macro avg", "weighted avg"}
PACKAGED_FILE_CONFLICTS = {
    "config.json",
    "generation_config.json",
    "model.safetensors",
    "pytorch_model.bin",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "vocab.txt",
    "merges.txt",
    "added_tokens.json",
    "spiece.model",
    "sentencepiece.bpe.model",
    MANIFEST_NAME,
}
REQUIRED_CONFIG_FILES = ("config.json", "tokenizer_config.json")
OPTIONAL_TOKENIZER_METADATA_FILES = ("special_tokens_map.json", "added_tokens.json")
TOKENIZER_FAMILY_FILES = (
    "tokenizer.json",
    "vocab.txt",
    "merges.txt",
    "spiece.model",
    "sentencepiece.bpe.model",
)


class PackagingError(RuntimeError):
    """Raised when packaging provenance or validation is unsafe."""


class CalibrationProvenance:
    """Exact-run calibration mapping resolved through evaluation metadata."""

    def __init__(
        self,
        *,
        eval_run_dir: Path,
        promotion_summary_path: Path,
        result_path: Path,
        temperature: float,
    ) -> None:
        self.eval_run_dir = eval_run_dir
        self.promotion_summary_path = promotion_summary_path
        self.result_path = result_path
        self.temperature = temperature


def find_repo_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "ml_model").exists() and (candidate / "web_app").exists():
            return candidate
    raise PackagingError("Could not locate repo root from current working directory")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing required file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def discover_latest_run(staging_dir: Path, model_key: str) -> Path:
    candidates = sorted(
        [
            path
            for path in staging_dir.iterdir()
            if path.is_dir() and path.name.startswith(model_key + "_")
        ],
        key=lambda path: path.name,
        reverse=True,
    )
    if not candidates:
        raise FileNotFoundError(f"No staged run found for {model_key} in {staging_dir}")
    return candidates[0]


def resolve_run_dir(
    staging_dir: Path,
    model_key: str,
    run_dir_name: str | None,
    *,
    discover_latest: bool,
    strict: bool,
) -> Path:
    if run_dir_name:
        run_dir = staging_dir / run_dir_name
        if not run_dir.exists() or not run_dir.is_dir():
            raise FileNotFoundError(f"Specified run directory does not exist: {run_dir}")
        if not run_dir.name.startswith(model_key + "_"):
            raise PackagingError(
                f"Run directory '{run_dir.name}' does not match model key '{model_key}'"
            )
        return run_dir.resolve()

    if strict and discover_latest:
        raise PackagingError(
            "Strict mode requires --run-dir-name; convenience latest-run discovery is disabled."
        )

    if discover_latest:
        return discover_latest_run(staging_dir, model_key).resolve()

    raise PackagingError(
        "Exact-run packaging requires --run-dir-name. "
        "Use --discover-latest explicitly only for convenience packaging."
    )


def ensure_required_run_files(run_dir: Path) -> None:
    missing = [name for name in REQUIRED_RUN_FILES if not (run_dir / name).exists()]
    if missing:
        raise PackagingError(
            f"Run directory '{run_dir}' is missing required provenance files: {missing}"
        )


def derive_model_version(run_dir: Path, config_used: dict[str, Any]) -> str:
    for key in ("model_version", "version", "artifact_version", "run_dir"):
        value = config_used.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return run_dir.name


def resolve_label_names(
    config_used: dict[str, Any],
    eval_report: dict[str, Any],
) -> list[str]:
    raw_config_labels = config_used.get("label_names")
    if isinstance(raw_config_labels, list) and all(
        isinstance(value, str) and value.strip() for value in raw_config_labels
    ):
        return [value.strip() for value in raw_config_labels]

    report_labels = [key for key in eval_report if key not in SUMMARY_METRIC_KEYS]
    if report_labels:
        return report_labels

    raise PackagingError(
        "Could not resolve label names from exact-run artifacts. "
        "Expected 'label_names' in config_used.json or class sections in eval_report.json."
    )


def validate_label_names(label_names: list[str]) -> list[str]:
    if label_names != DEFAULT_LABEL_NAMES:
        raise PackagingError(
            "Exact-run label configuration does not match serving expectations. "
            f"Expected {DEFAULT_LABEL_NAMES}, got {label_names}."
        )
    return label_names


def resolve_calibration_provenance(
    eval_dir: Path,
    *,
    model_key: str,
    run_dir_name: str,
    calibration_eval_run_dir: Path | None = None,
) -> CalibrationProvenance:
    if not eval_dir.exists():
        raise PackagingError(f"Evaluation directory does not exist: {eval_dir}")

    if calibration_eval_run_dir is not None:
        explicit_eval_run_dir = Path(calibration_eval_run_dir).resolve()
        if explicit_eval_run_dir.parent != eval_dir.resolve():
            raise PackagingError(
                "Explicit calibration evaluation directory must be a direct child of "
                f"'{eval_dir}'."
            )
        if not explicit_eval_run_dir.is_dir():
            raise PackagingError(
                f"Explicit calibration evaluation directory does not exist: {explicit_eval_run_dir}"
            )
        candidate_dirs = [explicit_eval_run_dir]
    else:
        candidate_dirs = sorted(
            [path for path in eval_dir.iterdir() if path.is_dir()],
            key=lambda path: path.name,
            reverse=True,
        )

    matches: list[CalibrationProvenance] = []
    for eval_run_dir in candidate_dirs:
        promotion_summary_path = eval_run_dir / "promotion_summary.json"
        if not promotion_summary_path.exists():
            continue

        summary_payload = load_json(promotion_summary_path)
        promotion_summary = summary_payload.get("promotion_summary")
        if not isinstance(promotion_summary, dict):
            continue

        model_summary = promotion_summary.get(model_key)
        if not isinstance(model_summary, dict):
            continue
        if model_summary.get("run_dir") != run_dir_name:
            continue

        result_path = eval_run_dir / f"eval_results_{model_key}_calibrated.json"
        if not result_path.exists():
            raise PackagingError(
                f"Promotion summary mapped run '{run_dir_name}' to '{eval_run_dir}', "
                f"but calibrated results file is missing: {result_path}"
            )

        result_payload = load_json(result_path)
        result_temperature_raw = result_payload.get("temperature")
        summary_temperature_raw = model_summary.get("temperature")
        if result_temperature_raw is None or summary_temperature_raw is None:
            raise PackagingError(
                "Calibration provenance is incomplete; temperature is missing from "
                f"'{result_path}' or '{promotion_summary_path}'."
            )

        result_temperature = float(result_temperature_raw)
        summary_temperature = float(summary_temperature_raw)
        if round(result_temperature, 6) != round(summary_temperature, 6):
            raise PackagingError(
                "Calibration temperature mismatch between promotion summary and eval results "
                f"for run '{run_dir_name}' in '{eval_run_dir}'."
            )

        matches.append(
            CalibrationProvenance(
                eval_run_dir=eval_run_dir.resolve(),
                promotion_summary_path=promotion_summary_path.resolve(),
                result_path=result_path.resolve(),
                temperature=result_temperature,
            )
        )

    if not matches:
        raise PackagingError(
            f"Could not determine exact-run calibration provenance for '{run_dir_name}' "
            f"and model '{model_key}'."
        )
    if len(matches) > 1:
        raise PackagingError(
            "Calibration provenance is ambiguous; multiple evaluation runs reference "
            f"'{run_dir_name}': {[str(match.eval_run_dir) for match in matches]}"
        )
    return matches[0]


def find_packaging_conflicts(run_dir: Path) -> list[str]:
    return sorted(name for name in PACKAGED_FILE_CONFLICTS if (run_dir / name).exists())


def ensure_overwrite_allowed(run_dir: Path, *, overwrite: bool) -> str:
    conflicts = find_packaging_conflicts(run_dir)
    if conflicts and not overwrite:
        raise PackagingError(
            "Packaging would overwrite existing serving files. "
            f"Re-run with --overwrite to replace them: {conflicts}"
        )
    return "overwrite" if conflicts else "fresh export"


def build_manifest(
    *,
    run_dir: Path,
    model_key: str,
    model_version: str,
    base_model: str,
    checkpoint_path: Path,
    config_used_path: Path,
    calibration: CalibrationProvenance,
    label_names: list[str],
    max_seq_len: int,
    notes: str | None,
    local_reload_verified: bool,
    actual_model: Any | None = None,
) -> dict[str, Any]:
    config_metadata = json.loads(config_used_path.read_text(encoding="utf-8"))
    preprocessing_version = validate_supported_model_input_version(
        config_metadata.get("preprocessing_version"), context="serving artifact"
    )
    if config_metadata.get("model_input_hash_policy") != MODEL_INPUT_HASH_POLICY:
        raise PackagingError("Serving artifact is missing the shared model-input hash policy.")
    expected_metadata = {
        "model_key": "distilbert",
        "model_id": "distilbert-base-uncased",
        "architecture": "distilbert_sequence_classification",
        "architecture_family": "huggingface_sequence_classifier",
        "head_type": "hf_sequence_classification_head",
        "model_class": "DistilBertForSequenceClassification",
    }
    for field, expected_value in expected_metadata.items():
        actual_value = model_key if field == "model_key" else (
            base_model if field == "model_id" else config_metadata.get(field)
        )
        if actual_value != expected_value:
            raise PackagingError(
                "Native DistilBERT serving manifest requires "
                f"{field}={expected_value!r}; got {actual_value!r}."
            )
    model_revision = config_metadata.get("model_revision")
    if not isinstance(model_revision, str) or not model_revision.strip():
        raise PackagingError("Native DistilBERT serving manifest requires model_revision.")
    if actual_model is not None:
        if type(actual_model).__name__ != expected_metadata["model_class"]:
            raise PackagingError(
                "Loaded model class does not match native DistilBERT serving metadata."
            )
        if int(getattr(actual_model.config, "num_labels", -1)) != len(label_names):
            raise PackagingError("Loaded model label count does not match serving labels.")
    return {
        "model_version": model_version,
        "model_key": model_key,
        "dataset_version": config_metadata.get("dataset_version"),
        "preprocessing_version": preprocessing_version,
        "model_input_hash_policy": config_metadata.get("model_input_hash_policy"),
        "architecture": config_metadata.get("architecture"),
        "architecture_family": config_metadata.get("architecture_family"),
        "head_type": config_metadata.get("head_type"),
        "model_class": config_metadata.get("model_class"),
        "model_revision": model_revision,
        "tokenizer_id": config_metadata.get("tokenizer_id", base_model),
        "tokenizer_revision": config_metadata.get("tokenizer_revision", model_revision),
        "run_contract_sha256": config_metadata.get("run_contract_sha256"),
        "base_model": base_model,
        "run_dir_name": run_dir.name,
        "run_dir_path": str(run_dir.resolve()),
        "checkpoint_file": checkpoint_path.name,
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "config_used_file": str(config_used_path.resolve()),
        "config_used_sha256": sha256_file(config_used_path),
        "temperature": round(float(calibration.temperature), 6),
        "temperature_source_file": str(calibration.result_path),
        "label_names": label_names,
        "num_labels": len(label_names),
        "max_seq_len": max_seq_len,
        "packaged_at_utc": utc_now_iso(),
        "packaging_tool": PACKAGING_TOOL,
        "torch_version": torch.__version__,
        "transformers_version": transformers.__version__,
        "local_reload_verified": local_reload_verified,
        "notes": notes or "",
        "source_notebooks": [
            "ml_model/notebooks/legacy/edited.ipynb",
            "ml_model/notebooks/legacy/evaluate.ipynb",
            "ml_model/notebooks/legacy/package_serving_artifact.ipynb",
        ],
        "promotion_summary_file": str(calibration.promotion_summary_path),
        "calibration_eval_run_dir": str(calibration.eval_run_dir),
    }


def write_manifest(run_dir: Path, manifest: dict[str, Any]) -> Path:
    manifest_path = run_dir / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def validate_packaged_artifact(
    *,
    run_dir: Path,
    label_names: list[str],
    max_seq_len: int,
    temperature: float,
    manifest_path: Path,
    temperature_source_file: Path,
    sample_text: str,
) -> None:
    for name in REQUIRED_CONFIG_FILES:
        if not (run_dir / name).exists():
            raise PackagingError(f"Packaged artifact missing required file: {run_dir / name}")

    if not any((run_dir / name).exists() for name in TOKENIZER_FAMILY_FILES):
        raise PackagingError(
            "Packaged tokenizer artifacts are incomplete; none of the tokenizer-family files "
            f"were found in '{run_dir}'."
        )

    optional_present = [name for name in OPTIONAL_TOKENIZER_METADATA_FILES if (run_dir / name).exists()]
    if optional_present:
        print(f"Optional tokenizer metadata present: {optional_present}")
    else:
        print("Optional tokenizer metadata files not emitted for this tokenizer family.")

    if not manifest_path.exists():
        raise PackagingError(f"Serving manifest was not written: {manifest_path}")

    reload_model = AutoModelForSequenceClassification.from_pretrained(
        run_dir,
        local_files_only=True,
    )
    reload_tokenizer = AutoTokenizer.from_pretrained(
        run_dir,
        local_files_only=True,
    )
    reload_model.to(DEVICE).eval()

    if int(reload_model.config.num_labels) != len(label_names):
        raise PackagingError(
            "Reloaded model num_labels does not match expected serving label count: "
            f"{reload_model.config.num_labels} != {len(label_names)}"
        )

    encoded = reload_tokenizer(
        sample_text,
        truncation=True,
        max_length=max_seq_len,
        return_tensors="pt",
        padding=True,
    )

    with torch.inference_mode():
        logits = reload_model(**encoded).logits.float()

    if logits.ndim != 2 or int(logits.shape[-1]) != len(label_names):
        raise PackagingError(
            "Dry-run inference returned unexpected logits shape: "
            f"{tuple(logits.shape)} for {len(label_names)} labels"
        )

    probs = torch.softmax(logits / float(temperature), dim=-1).squeeze().tolist()
    pred_idx = int(torch.argmax(torch.tensor(probs)).item())

    manifest_payload = load_json(manifest_path)
    if manifest_payload.get("run_dir_name") != run_dir.name:
        raise PackagingError("Serving manifest run_dir_name does not match selected run.")
    if manifest_payload.get("temperature_source_file") != str(temperature_source_file.resolve()):
        raise PackagingError(
            "Serving manifest temperature_source_file does not match exact calibration source."
        )

    print(f"Sample prediction : {label_names[pred_idx]}")
    print(f"Confidence        : {max(float(value) for value in probs):.6f}")
    print("Local-only reload succeeded.")


def package_serving_artifact(
    *,
    model_key: str = "distilbert",
    run_dir_name: str | None = None,
    discover_latest: bool = False,
    overwrite: bool = False,
    strict: bool = False,
    sample_text: str = DEFAULT_SAMPLE_TEXT,
    notes: str | None = None,
    calibration_eval_run_dir: Path | None = None,
) -> Path:
    if model_key not in MODEL_IDS:
        raise KeyError(f"Unknown model key: {model_key}")

    repo_root = find_repo_root(Path.cwd().resolve())
    model_registry = repo_root / "ml_model" / "model_registry"
    staging_dir = model_registry / "staging"
    eval_dir = model_registry / "eval"

    run_dir = resolve_run_dir(
        staging_dir,
        model_key,
        run_dir_name,
        discover_latest=discover_latest,
        strict=strict,
    )
    ensure_required_run_files(run_dir)

    config_used_path = run_dir / "config_used.json"
    eval_report_path = run_dir / "eval_report.json"
    checkpoint_path = run_dir / f"best_{model_key}_ckpt.pt"
    if not checkpoint_path.exists():
        raise FileNotFoundError(f"Missing checkpoint: {checkpoint_path}")

    packaging_mode = ensure_overwrite_allowed(run_dir, overwrite=overwrite)
    config_used = load_json(config_used_path)
    eval_report = load_json(eval_report_path)
    label_names = validate_label_names(resolve_label_names(config_used, eval_report))
    calibration = resolve_calibration_provenance(
        eval_dir,
        model_key=model_key,
        run_dir_name=run_dir.name,
        calibration_eval_run_dir=calibration_eval_run_dir,
    )

    model_id = config_used.get("model_id", MODEL_IDS[model_key])
    if not isinstance(model_id, str) or not model_id.strip():
        raise PackagingError("Exact-run config_used.json does not contain a valid model_id.")
    model_id = model_id.strip()
    model_revision = config_used.get("model_revision")
    if not isinstance(model_revision, str) or not model_revision.strip():
        raise PackagingError("Exact-run config_used.json does not contain a pinned model_revision.")
    tokenizer_id = config_used.get("tokenizer_id", model_id)
    tokenizer_revision = config_used.get("tokenizer_revision", model_revision)
    if tokenizer_id != model_id or tokenizer_revision != model_revision:
        raise PackagingError("Model and tokenizer revisions must match the exact run contract.")
    max_seq_len = int(config_used.get("max_seq_len", 128))
    model_version = derive_model_version(run_dir, config_used)

    print(f"Repo root             : {repo_root}")
    print(f"Model registry        : {model_registry}")
    print(f"Resolved run path     : {run_dir}")
    print(f"Packaging mode        : {packaging_mode}")
    print(f"Checkpoint            : {checkpoint_path.name}")
    print(f"Base model            : {model_id}")
    print(f"Model revision        : {model_revision}")
    print(f"Model version         : {model_version}")
    print(f"Max seq len           : {max_seq_len}")
    print(f"Calibration source    : {calibration.result_path}")
    print(f"Calibration temperature: {calibration.temperature:.6f}")

    model = AutoModelForSequenceClassification.from_pretrained(
        model_id,
        revision=model_revision,
        num_labels=len(label_names),
    )
    state = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if not isinstance(state, dict):
        raise TypeError(f"Expected state_dict, got {type(state)}")
    model.load_state_dict(state, strict=True)
    model.to(DEVICE).eval()
    tokenizer = AutoTokenizer.from_pretrained(
        tokenizer_id,
        revision=tokenizer_revision,
    )
    print("Checkpoint and tokenizer loaded successfully.")

    manifest = build_manifest(
        run_dir=run_dir,
        model_key=model_key,
        model_version=model_version,
        base_model=model_id,
        checkpoint_path=checkpoint_path,
        config_used_path=config_used_path,
        calibration=calibration,
        label_names=label_names,
        max_seq_len=max_seq_len,
        notes=notes,
        local_reload_verified=False,
        actual_model=model,
    )

    model.save_pretrained(run_dir)
    tokenizer.save_pretrained(run_dir)
    manifest_path = write_manifest(run_dir, manifest)

    validate_packaged_artifact(
        run_dir=run_dir,
        label_names=label_names,
        max_seq_len=max_seq_len,
        temperature=calibration.temperature,
        manifest_path=manifest_path,
        temperature_source_file=calibration.result_path,
        sample_text=sample_text,
    )

    manifest["local_reload_verified"] = True
    write_manifest(run_dir, manifest)

    print("Run directory contents:")
    for path in sorted(run_dir.iterdir(), key=lambda item: item.name):
        print(f"  - {path.name}")
    print("Serving manifest updated with verified local reload status.")
    return run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package one staged transformer checkpoint as a local serving artifact.",
    )
    parser.add_argument(
        "--model-key",
        choices=sorted(MODEL_IDS),
        default="distilbert",
        help="Model family to package.",
    )
    parser.add_argument(
        "--run-dir-name",
        default=None,
        help="Exact run directory name under ml_model/model_registry/staging/.",
    )
    parser.add_argument(
        "--discover-latest",
        action="store_true",
        help="Convenience-only mode: explicitly discover the latest run for the model key.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting previously packaged serving files in the target run directory.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Disallow convenience discovery and require exact-run packaging inputs.",
    )
    parser.add_argument(
        "--sample-text",
        default=DEFAULT_SAMPLE_TEXT,
        help="Sample text used to validate local-only reload after packaging.",
    )
    parser.add_argument(
        "--notes",
        default=None,
        help="Optional operator note to store in the serving manifest.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    package_serving_artifact(
        model_key=args.model_key,
        run_dir_name=args.run_dir_name,
        discover_latest=args.discover_latest,
        overwrite=args.overwrite,
        strict=args.strict,
        sample_text=args.sample_text,
        notes=args.notes,
    )


if __name__ == "__main__":
    main()
