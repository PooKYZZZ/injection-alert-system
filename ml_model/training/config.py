"""TOML-backed configuration for the script-first training workflow."""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping

from ml_model.preprocessing.model_input import LEGACY_MODEL_INPUT_VERSION
from ml_model.training.paths import (
    resolve_configured_path,
    resolve_project_root,
)

DEFAULT_DATASET_VERSION = "v3_907k_cleaned"
DEFAULT_MODELS = ("distilbert",)
DEFAULT_SEEDS = (42, 1337, 2026)
DEFAULT_MODEL_REVISION = "12040accade4e8a0f71eabdb258fecc2e7e948be"


@dataclass(frozen=True)
class TrainingConfig:
    dataset_version: str = DEFAULT_DATASET_VERSION
    preprocessing_version: str = LEGACY_MODEL_INPUT_VERSION
    model_revision: str = DEFAULT_MODEL_REVISION
    data_dir: Path | None = None
    output_dir: Path | None = None
    models: tuple[str, ...] = DEFAULT_MODELS
    seeds: tuple[int, ...] = DEFAULT_SEEDS
    device: str = "auto"
    precision: str = "auto"
    batch_size: int | None = None
    eval_batch_size: int | None = None
    epochs: int = 4
    learning_rate: float | None = None
    num_workers: int = 0
    checkpoint_interval_epochs: int = 1
    resume: bool = True
    resume_checkpoint: Path | None = None
    max_train_samples: int | None = None
    max_validation_samples: int | None = None
    max_test_samples: int | None = None
    max_seq_len: int | None = None
    gradient_accumulation_steps: int | None = None
    prepare_only: bool = False

    @property
    def model_keys(self) -> tuple[str, ...]:
        """Compatibility name used by the existing runner boundary."""

        return self.models

    @classmethod
    def smoke(cls) -> "TrainingConfig":
        return cls(
            models=("distilbert",),
            seeds=(42,),
            device="cpu",
            precision="full",
            batch_size=2,
            eval_batch_size=4,
            epochs=1,
            num_workers=0,
            checkpoint_interval_epochs=1,
            resume=False,
            max_train_samples=64,
            max_validation_samples=32,
            max_test_samples=32,
            prepare_only=False,
        )

    def validate(self) -> "TrainingConfig":
        if not self.dataset_version.strip():
            raise ValueError("dataset_version must not be empty")
        if not self.preprocessing_version.strip():
            raise ValueError("preprocessing_version must not be empty")
        if not self.model_revision.strip() or self.model_revision == "unresolved":
            raise ValueError("model_revision must be a pinned revision")
        if not self.models:
            raise ValueError("models must contain at least one model key")
        if not self.seeds:
            raise ValueError("seeds must contain at least one seed")
        if any(int(seed) < 0 for seed in self.seeds):
            raise ValueError("seeds must be non-negative")
        if self.device not in {"auto", "cpu", "cuda", "mps"}:
            raise ValueError("device must be auto, cpu, cuda, or mps")
        if self.precision not in {"auto", "full", "fp16", "bf16"}:
            raise ValueError("precision must be auto, full, fp16, or bf16")
        for name, value in (
            ("batch_size", self.batch_size),
            ("eval_batch_size", self.eval_batch_size),
            ("epochs", self.epochs),
            ("num_workers", self.num_workers),
            ("checkpoint_interval_epochs", self.checkpoint_interval_epochs),
            ("max_train_samples", self.max_train_samples),
            ("max_validation_samples", self.max_validation_samples),
            ("max_test_samples", self.max_test_samples),
            ("max_seq_len", self.max_seq_len),
            ("gradient_accumulation_steps", self.gradient_accumulation_steps),
        ):
            if value is not None and int(value) < (0 if name == "num_workers" else 1):
                raise ValueError(
                    f"{name} must be non-negative when provided"
                    if name == "num_workers"
                    else f"{name} must be positive when provided"
                )
        if self.learning_rate is not None and self.learning_rate <= 0:
            raise ValueError("learning_rate must be positive when provided")
        return self

    def resolve_paths(self, project_root: Path | str | None = None) -> "TrainingConfig":
        root = resolve_project_root(project_root)
        return replace(
            self,
            data_dir=(
                resolve_configured_path(self.data_dir, project_root=root)
                if self.data_dir is not None
                else None
            ),
            output_dir=(
                resolve_configured_path(self.output_dir, project_root=root)
                if self.output_dir is not None
                else None
            ),
            resume_checkpoint=resolve_configured_path(
                self.resume_checkpoint, project_root=root
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["models"] = list(self.models)
        payload["seeds"] = list(self.seeds)
        for key in ("data_dir", "output_dir", "resume_checkpoint"):
            if payload[key] is not None:
                payload[key] = str(payload[key])
        return payload


def _tuple_value(
    mapping: Mapping[str, Any], key: str, default: tuple[Any, ...]
) -> tuple[Any, ...]:
    value = mapping.get(key, default)
    if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
        raise ValueError(f"{key} must be a list")
    return tuple(value)


def _from_mapping(mapping: Mapping[str, Any]) -> TrainingConfig:
    return TrainingConfig(
        dataset_version=str(mapping.get("dataset_version", DEFAULT_DATASET_VERSION)),
        preprocessing_version=str(
            mapping.get("preprocessing_version", LEGACY_MODEL_INPUT_VERSION)
        ),
        model_revision=str(mapping.get("model_revision", DEFAULT_MODEL_REVISION)),
        data_dir=Path(mapping["data_dir"]) if mapping.get("data_dir") else None,
        output_dir=Path(mapping["output_dir"]) if mapping.get("output_dir") else None,
        models=tuple(
            str(item) for item in _tuple_value(mapping, "models", DEFAULT_MODELS)
        ),
        seeds=tuple(
            int(item) for item in _tuple_value(mapping, "seeds", DEFAULT_SEEDS)
        ),
        device=str(mapping.get("device", "auto")),
        precision=str(mapping.get("precision", "auto")),
        batch_size=mapping.get("batch_size"),
        eval_batch_size=mapping.get("eval_batch_size"),
        epochs=int(mapping.get("epochs", 4)),
        learning_rate=mapping.get("learning_rate"),
        num_workers=int(mapping.get("num_workers", 0)),
        checkpoint_interval_epochs=int(mapping.get("checkpoint_interval_epochs", 1)),
        resume=bool(mapping.get("resume", True)),
        resume_checkpoint=(
            Path(mapping["resume_checkpoint"])
            if mapping.get("resume_checkpoint")
            else None
        ),
        max_train_samples=mapping.get("max_train_samples"),
        max_validation_samples=mapping.get("max_validation_samples"),
        max_test_samples=mapping.get("max_test_samples"),
        max_seq_len=mapping.get("max_seq_len"),
        gradient_accumulation_steps=mapping.get("gradient_accumulation_steps"),
        prepare_only=bool(mapping.get("prepare_only", False)),
    ).validate()


def load_training_config(
    path: Path | str, *, project_root: Path | str | None = None
) -> TrainingConfig:
    config_path = Path(path).expanduser().resolve()
    with config_path.open("rb") as handle:
        document = tomllib.load(handle)
    mapping = document.get("training", document)
    if not isinstance(mapping, dict):
        raise ValueError("Training configuration must contain a [training] table")
    config = _from_mapping(mapping)
    root = resolve_project_root(project_root)
    return config.resolve_paths(root)
