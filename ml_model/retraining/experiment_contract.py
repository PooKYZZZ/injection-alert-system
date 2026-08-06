"""Immutable configuration for the controlled 20-day retraining experiment."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from ml_model.training.paths import resolve_project_root

EXPERIMENT_NAME = "controlled-retraining-20-day"
EXPERIMENT_VERSION = "retraining-20-day-v1"
EXPECTED_LABELS = (
    "Code Injection",
    "Normal",
    "Other Attacks",
    "SQL Injection",
)
EXPECTED_PREPROCESSING_VERSION = "http-preprocessor-v1"
EXPECTED_MODEL_FAMILY = "native_distilbert"
EXPECTED_MODEL_ID = "distilbert-base-uncased"
EXPECTED_MODEL_REVISION = "12040accade4e8a0f71eabdb258fecc2e7e948be"
MODEL_REVISION_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def canonical_json_sha256(payload: Mapping[str, Any]) -> str:
    """Hash a JSON object without machine-specific formatting or paths."""

    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class AcceptanceTolerances:
    normal_false_positive_tolerance: float = 0.001
    attack_escape_tolerance: float = 0.001
    macro_f1_drop_tolerance: float = 0.002
    normal_recall_minimum: float = 0.995
    supported_attack_recall_drop_tolerance: float = 0.01

    def validate(self) -> "AcceptanceTolerances":
        numeric = {
            "normal_false_positive_tolerance": self.normal_false_positive_tolerance,
            "attack_escape_tolerance": self.attack_escape_tolerance,
            "macro_f1_drop_tolerance": self.macro_f1_drop_tolerance,
            "normal_recall_minimum": self.normal_recall_minimum,
            "supported_attack_recall_drop_tolerance": (
                self.supported_attack_recall_drop_tolerance
            ),
        }
        if any(float(value) < 0 for value in numeric.values()):
            raise ValueError("acceptance tolerances must be non-negative")
        if not 0.0 <= self.normal_recall_minimum <= 1.0:
            raise ValueError("normal_recall_minimum must be within 0..1")
        return self

    def to_dict(self) -> dict[str, float]:
        return {
            "normal_false_positive_tolerance": self.normal_false_positive_tolerance,
            "attack_escape_tolerance": self.attack_escape_tolerance,
            "macro_f1_drop_tolerance": self.macro_f1_drop_tolerance,
            "normal_recall_minimum": self.normal_recall_minimum,
            "supported_attack_recall_drop_tolerance": (
                self.supported_attack_recall_drop_tolerance
            ),
        }


@dataclass(frozen=True)
class ExperimentConfig:
    name: str
    version: str
    historical_dataset_version: str
    preprocessing_version: str
    model_family: str
    model_id: str
    model_revision: str
    daily_seed: int
    confirmation_seeds: tuple[int, ...]
    max_epochs: int
    golden_version: str
    golden_manifest_file: Path
    label_names: tuple[str, ...]
    confidence_thresholds: dict[str, float]
    response_actions: dict[str, str]
    output_dir: Path
    daily_batch_dir: Path
    training_config: Path | None
    acceptance: AcceptanceTolerances
    project_root: Path

    @property
    def golden_cases_file(self) -> Path:
        return self.golden_manifest_file.parent / "golden_cases.jsonl"

    @property
    def contract_hash(self) -> str:
        return canonical_json_sha256(self.to_dict(include_paths=False))

    def action_for(self, label: str, confidence_tier: str) -> str:
        if label == "Normal":
            return self.response_actions["normal"]
        key = confidence_tier.lower()
        if key not in self.response_actions:
            raise ValueError(f"Unknown confidence tier: {confidence_tier}")
        return self.response_actions[key]

    def resolve_path(self, value: Path | str) -> Path:
        path = Path(value).expanduser()
        return (
            path.resolve()
            if path.is_absolute()
            else (self.project_root / path).resolve()
        )

    def validate_runtime_inputs(
        self,
        *,
        historical_data_dir: Path | str,
        daily_batch_dir: Path | str,
        days: Iterable[int] | None = None,
    ) -> None:
        historical_root = Path(historical_data_dir).expanduser().resolve()
        daily_root = Path(daily_batch_dir).expanduser().resolve()
        required = [
            self.golden_manifest_file,
            self.golden_cases_file,
            historical_root / "train.parquet",
            historical_root / "validation.parquet",
            historical_root / "test.parquet",
            historical_root / "metadata_preprocessing.json",
            historical_root / "checksums.txt",
        ]
        if self.training_config is not None:
            required.append(self.training_config)
        requested_days = tuple(int(day) for day in (days or range(1, 21)))
        required.extend(
            daily_root / f"day_{day:02d}.jsonl" for day in requested_days
        )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError(
                "Experiment preflight failed. Missing:\n" + "\n".join(missing)
            )

    def to_dict(self, *, include_paths: bool = True) -> dict[str, Any]:
        def portable(path: Path | None) -> str | None:
            if path is None:
                return None
            if not include_paths:
                return path.name
            try:
                return str(path.relative_to(self.project_root))
            except ValueError:
                return str(path)

        return {
            "name": self.name,
            "version": self.version,
            "historical_dataset_version": self.historical_dataset_version,
            "preprocessing_version": self.preprocessing_version,
            "model_family": self.model_family,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "daily_seed": self.daily_seed,
            "confirmation_seeds": list(self.confirmation_seeds),
            "max_epochs": self.max_epochs,
            "golden_version": self.golden_version,
            "golden_manifest_file": portable(self.golden_manifest_file),
            "label_names": list(self.label_names),
            "confidence_thresholds": self.confidence_thresholds,
            "response_actions": self.response_actions,
            "output_dir": portable(self.output_dir),
            "daily_batch_dir": portable(self.daily_batch_dir),
            "training_config": portable(self.training_config),
            "acceptance": self.acceptance.to_dict(),
        }

    def validate(self) -> "ExperimentConfig":
        if (self.name, self.version) != (EXPERIMENT_NAME, EXPERIMENT_VERSION):
            raise ValueError("experiment name/version is not the locked v1 contract")
        if self.preprocessing_version != EXPECTED_PREPROCESSING_VERSION:
            raise ValueError("primary experiment must use http-preprocessor-v1")
        if (
            self.model_family != EXPECTED_MODEL_FAMILY
            or self.model_id != EXPECTED_MODEL_ID
        ):
            raise ValueError("primary experiment must use native DistilBERT")
        if not MODEL_REVISION_PATTERN.fullmatch(self.model_revision):
            raise ValueError("model_revision must be a pinned 40-character SHA")
        if self.model_revision != EXPECTED_MODEL_REVISION:
            raise ValueError(
                "model_revision differs from the locked native DistilBERT revision"
            )
        if self.daily_seed != 2026 or self.confirmation_seeds != (42, 1337, 2026):
            raise ValueError("daily and confirmation seeds are immutable")
        if not 1 <= self.max_epochs <= 4:
            raise ValueError("max_epochs must be between 1 and 4")
        if self.golden_version != "golden-v1":
            raise ValueError("golden version is immutable")
        if self.label_names != EXPECTED_LABELS:
            raise ValueError("label mapping/order differs from the serving contract")
        thresholds = self.confidence_thresholds
        if (
            not 0.0
            <= thresholds["low"]
            < thresholds["high"]
            < thresholds["critical"]
            <= 1.0
        ):
            raise ValueError("confidence thresholds are invalid")
        expected_actions = {
            "normal": "ALLOWED",
            "low": "ALLOWED",
            "medium": "THROTTLED",
            "high": "BLOCKED",
            "critical": "BLOCKED",
        }
        if self.response_actions != expected_actions:
            raise ValueError(
                "response-action mapping differs from the serving contract"
            )
        self.acceptance.validate()
        return self


def load_experiment_config(
    path: Path | str,
    *,
    project_root: Path | str | None = None,
) -> ExperimentConfig:
    config_path = Path(path).expanduser().resolve()
    document = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("experiment configuration must be a TOML object")
    root = (
        Path(project_root).expanduser().resolve()
        if project_root is not None
        else resolve_project_root()
    )
    data = document.get("data", {})
    model = document.get("model", {})
    golden = document.get("golden", {})
    policy = document.get("policy", {})
    labels = document.get("labels", {})
    acceptance = document.get("acceptance", {})
    runtime = document.get("runtime", {})
    if not all(
        isinstance(section, dict)
        for section in (data, model, golden, policy, labels, acceptance, runtime)
    ):
        raise ValueError("experiment configuration sections must be TOML tables")
    thresholds = policy.get("thresholds", {})
    actions = policy.get("actions", {})
    if not isinstance(thresholds, dict) or not isinstance(actions, dict):
        raise ValueError("policy.thresholds and policy.actions must be tables")

    def resolve_optional(value: object) -> Path | None:
        if value in (None, ""):
            return None
        candidate = Path(str(value)).expanduser()
        return (candidate if candidate.is_absolute() else root / candidate).resolve()

    manifest = resolve_optional(golden.get("manifest_file"))
    if manifest is None:
        raise ValueError("golden.manifest_file is required")
    config = ExperimentConfig(
        name=str(document.get("experiment", {}).get("name", "")),
        version=str(document.get("experiment", {}).get("version", "")),
        historical_dataset_version=str(data.get("historical_dataset_version", "")),
        preprocessing_version=str(data.get("preprocessing_version", "")),
        model_family=str(model.get("model_family", "")),
        model_id=str(model.get("model_id", "")),
        model_revision=str(model.get("model_revision", "")),
        daily_seed=int(model.get("daily_seed", -1)),
        confirmation_seeds=tuple(
            int(value) for value in model.get("confirmation_seeds", [])
        ),
        max_epochs=int(model.get("max_epochs", 0)),
        golden_version=str(golden.get("version", "")),
        golden_manifest_file=manifest,
        label_names=tuple(str(value) for value in labels.get("names", [])),
        confidence_thresholds={
            key: float(thresholds[key]) for key in ("low", "high", "critical")
        },
        response_actions={
            key: str(actions[key])
            for key in ("normal", "low", "medium", "high", "critical")
        },
        output_dir=resolve_optional(runtime.get("output_dir"))
        or (root / "ml_model" / "results" / EXPERIMENT_VERSION),
        daily_batch_dir=resolve_optional(runtime.get("daily_batch_dir"))
        or (root / "data" / "experiments" / EXPERIMENT_VERSION / "daily_batches"),
        training_config=resolve_optional(runtime.get("training_config")),
        acceptance=AcceptanceTolerances(
            normal_false_positive_tolerance=float(
                acceptance.get("normal_false_positive_tolerance", 0.001)
            ),
            attack_escape_tolerance=float(
                acceptance.get("attack_escape_tolerance", 0.001)
            ),
            macro_f1_drop_tolerance=float(
                acceptance.get("macro_f1_drop_tolerance", 0.002)
            ),
            normal_recall_minimum=float(acceptance.get("normal_recall_minimum", 0.995)),
            supported_attack_recall_drop_tolerance=float(
                acceptance.get("supported_attack_recall_drop_tolerance", 0.01)
            ),
        ),
        project_root=root,
    )
    return config.validate()
