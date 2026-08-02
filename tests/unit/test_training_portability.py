from __future__ import annotations

from pathlib import Path

import pytest
import torch


def test_project_root_resolution_uses_explicit_root(tmp_path: Path):
    from ml_model.training.paths import resolve_project_root

    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='fixture'\n", encoding="utf-8"
    )
    (tmp_path / "ml_model").mkdir()

    assert resolve_project_root(explicit=tmp_path) == tmp_path.resolve()


def test_training_config_loads_toml_and_resolves_relative_paths(tmp_path: Path):
    from ml_model.training.config import load_training_config

    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='fixture'\n", encoding="utf-8"
    )
    (tmp_path / "ml_model").mkdir()
    config_path = tmp_path / "laptop.toml"
    config_path.write_text(
        """
[training]
dataset_version = "fixture_dataset"
data_dir = "data/processed/fixture_dataset"
output_dir = "runs/smoke"
models = ["distilbert"]
seeds = [42]
device = "cpu"
precision = "full"
batch_size = 2
epochs = 1
learning_rate = 0.00003
num_workers = 0
checkpoint_interval_epochs = 1
resume = false
""",
        encoding="utf-8",
    )

    config = load_training_config(config_path, project_root=tmp_path)

    assert config.dataset_version == "fixture_dataset"
    assert config.data_dir == (tmp_path / "data/processed/fixture_dataset").resolve()
    assert config.output_dir == (tmp_path / "runs/smoke").resolve()
    assert config.models == ("distilbert",)
    assert config.seeds == (42,)
    assert config.batch_size == 2
    assert config.resume is False


def test_training_config_rejects_unsafe_values():
    from ml_model.training.config import TrainingConfig

    with pytest.raises(ValueError, match="batch_size"):
        TrainingConfig(batch_size=0).validate()

    with pytest.raises(ValueError, match="precision"):
        TrainingConfig(precision="tf32").validate()

    with pytest.raises(ValueError, match="checkpoint_interval_epochs"):
        TrainingConfig(checkpoint_interval_epochs=0).validate()


def test_explicit_unavailable_device_fails_and_auto_falls_back(monkeypatch):
    from ml_model.training.device import resolve_device

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: False)

    assert resolve_device("auto").type == "cpu"
    with pytest.raises(RuntimeError, match="CUDA.*unavailable"):
        resolve_device("cuda")


def test_laptop_smoke_config_is_cpu_safe():
    from ml_model.training.config import TrainingConfig

    config = TrainingConfig.smoke()

    assert config.device == "cpu"
    assert config.precision == "full"
    assert config.models == ("distilbert",)
    assert config.seeds == (42,)
    assert config.epochs == 1
    assert config.max_train_samples > 0
    assert config.max_validation_samples > 0
    assert config.max_test_samples > 0


def test_default_training_config_targets_distilbert_only():
    from ml_model.training.config import TrainingConfig

    config = TrainingConfig()

    assert config.models == ("distilbert",)


def test_fp16_precision_is_allowed_for_cuda(monkeypatch):
    from ml_model.training.device import resolve_precision

    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)

    assert resolve_precision("fp16", torch.device("cuda")) == "fp16"


def test_laptop_cuda_distilbert_preset_is_gpu_optimized():
    from ml_model.training.config import load_training_config

    config = load_training_config(
        Path("ml_model/configs/training/laptop_cuda_distilbert.toml")
    )

    assert config.models == ("distilbert",)
    assert config.device == "cuda"
    assert config.precision == "fp16"
    assert config.batch_size == 64
    assert config.eval_batch_size == 128
    assert config.epochs == 5
    assert config.gradient_accumulation_steps == 2
    assert config.max_seq_len == 128
    assert config.num_workers == 2


def test_default_training_output_dir_is_for_training_runs(tmp_path: Path):
    from ml_model.training.paths import default_training_output_dir

    output_dir = default_training_output_dir(project_root=tmp_path)

    assert output_dir == tmp_path / "ml_model" / "results" / "training_runs"


def test_resume_checkpoint_path_is_resolved_from_config(tmp_path: Path):
    from ml_model.training.config import TrainingConfig

    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='fixture'\n", encoding="utf-8"
    )
    (tmp_path / "ml_model").mkdir()
    checkpoint = tmp_path / "checkpoints" / "last.pt"
    config = TrainingConfig(resume_checkpoint=Path("checkpoints/last.pt"))
    resolved = config.resolve_paths(tmp_path)

    assert resolved.resume_checkpoint == checkpoint.resolve()


def test_missing_explicit_resume_checkpoint_fails_before_dataset_work(tmp_path: Path):
    from ml_model.training.config import TrainingConfig
    from ml_model.training.train import build_runner_context

    with pytest.raises(FileNotFoundError, match="resume checkpoint"):
        build_runner_context(
            TrainingConfig(
                resume_checkpoint=tmp_path / "missing.pt",
                models=("distilbert",),
                seeds=(42,),
            )
        )
