from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ml_model.evaluation.golden_controls import load_golden_controls
from ml_model.retraining.experiment_contract import (
    EXPECTED_LABELS,
    EXPECTED_MODEL_REVISION,
    EXPECTED_PREPROCESSING_VERSION,
    AcceptanceTolerances,
    load_experiment_config,
)


@pytest.mark.parametrize(
    "field",
    [
        "normal_false_positive_tolerance",
        "attack_escape_tolerance",
        "macro_f1_drop_tolerance",
        "normal_recall_minimum",
        "supported_attack_recall_drop_tolerance",
    ],
)
def test_acceptance_tolerances_are_locked(field: str):
    changed = replace(AcceptanceTolerances(), **{field: 0.5})

    with pytest.raises(ValueError, match="locked"):
        changed.validate()


def test_checked_in_experiment_contract_is_immutable_and_portable():
    root = Path(__file__).resolve().parents[2]
    config = load_experiment_config(root / "ml_model/configs/retraining_20_day_v1.toml")

    assert config.preprocessing_version == EXPECTED_PREPROCESSING_VERSION
    assert config.model_revision == EXPECTED_MODEL_REVISION
    assert config.label_names == EXPECTED_LABELS
    assert config.daily_seed == 2026
    assert config.confirmation_seeds == (42, 1337, 2026)
    assert config.max_epochs == 4
    assert config.golden_version == "golden-v2"
    assert config.golden_manifest_file.name == "golden_manifest.json"
    assert config.daily_batch_dir.name == "records_search_v1"
    controls = load_golden_controls(config.golden_manifest_file)
    assert controls.golden_version == "golden-v2"
    assert controls.manifest["target_route"] == "/records/search"
    assert controls.manifest["target_case_count"] == 28
    assert config.action_for("Normal", "CRITICAL") == "ALLOWED"
    assert config.action_for("SQL Injection", "HIGH") == "BLOCKED"
    assert config.output_dir.is_relative_to(root)


def test_contract_rejects_v2_preprocessing(tmp_path: Path):
    path = tmp_path / "bad.toml"
    path.write_text(
        """
[experiment]
name = "controlled-retraining-20-day"
version = "retraining-20-day-v1"
[data]
historical_dataset_version = "v3_907k_cleaned"
preprocessing_version = "model-input-v2-redacted"
[model]
model_family = "native_distilbert"
model_id = "distilbert-base-uncased"
model_revision = "12040accade4e8a0f71eabdb258fecc2e7e948be"
daily_seed = 2026
confirmation_seeds = [42, 1337, 2026]
max_epochs = 4
[golden]
version = "golden-v1"
manifest_file = "golden_manifest.json"
[labels]
names = ["Code Injection", "Normal", "Other Attacks", "SQL Injection"]
[policy.thresholds]
low = 0.50
high = 0.80
critical = 0.90
[policy.actions]
normal = "ALLOWED"
low = "ALLOWED"
medium = "THROTTLED"
high = "BLOCKED"
critical = "BLOCKED"
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="http-preprocessor-v1"):
        load_experiment_config(path, project_root=tmp_path)


def test_runtime_preflight_reports_missing_inputs(tmp_path: Path):
    root = Path(__file__).resolve().parents[2]
    config = load_experiment_config(root / "ml_model/configs/retraining_20_day_v1.toml")

    with pytest.raises(FileNotFoundError, match="Experiment preflight failed"):
        config.validate_runtime_inputs(
            historical_data_dir=tmp_path / "historical",
            daily_batch_dir=tmp_path / "daily",
        )
