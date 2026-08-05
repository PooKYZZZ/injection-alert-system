from __future__ import annotations

from pathlib import Path

import pytest


def _contract(**overrides):
    from ml_model.training.run_contract import build_training_run_contract

    payload = {
        "dataset_version": "v3_907k_cleaned",
        "preprocessing_version": "http-preprocessor-v1",
        "model_keys": ["distilbert"],
        "model_contracts": {
            "distilbert": {
                "model_id": "distilbert-base-uncased",
                "model_revision": "verified-revision",
                "architecture": "distilbert_sequence_classification",
            }
        },
        "seed_list": [42, 1337, 2026],
        "loss_keys": ["weighted_ce"],
        "max_seq_len": 128,
        "batch_size": 64,
        "eval_batch_size": 128,
        "epochs": 4,
        "learning_rate": 0.00003,
        "gradient_accumulation_steps": 2,
        "dataset_file_manifest_sha256": "f" * 64,
        "label_names": [
            "Code Injection",
            "Normal",
            "Other Attacks",
            "SQL Injection",
        ],
        "class_mapping": {
            "Code Injection": 0,
            "Normal": 1,
            "Other Attacks": 2,
            "SQL Injection": 3,
        },
        "loss_contracts": {"weighted_ce": {"focal_gamma": None}},
        "weight_decay": 0.01,
        "warmup_ratio": 0.04,
        "sample_limits": {
            "train": 64,
            "validation": 32,
            "test": 32,
        },
        "precision": "full",
        "training_implementation_version": "training-implementation.v1",
    }
    payload.update(overrides)
    return build_training_run_contract(**payload)


def test_identical_contracts_have_identical_hashes():
    from ml_model.training.run_contract import contract_sha256

    assert contract_sha256(_contract()) == contract_sha256(_contract())


def test_dictionary_order_does_not_change_hash():
    from ml_model.training.run_contract import contract_sha256

    first = _contract()
    second = dict(reversed(list(first.items())))
    assert contract_sha256(first) == contract_sha256(second)


@pytest.mark.parametrize(
    "change",
    [
        {
            "model_contracts": {
                "distilbert": {
                    "model_id": "distilbert-base-uncased",
                    "model_revision": "verified-revision",
                    "architecture": "transformer",
                }
            }
        },
        {"seed_list": [42]},
        {"learning_rate": 0.00002},
        {"epochs": 5},
        {"dataset_file_manifest_sha256": "e" * 64},
        {"label_names": ["Normal", "Code Injection", "Other Attacks", "SQL Injection"]},
        {"class_mapping": {"Code Injection": 1, "Normal": 0, "Other Attacks": 2, "SQL Injection": 3}},
        {"loss_contracts": {"weighted_ce": {"focal_gamma": 2.0}}},
        {"weight_decay": 0.02},
        {"warmup_ratio": 0.08},
        {"sample_limits": {"train": 65, "validation": 32, "test": 32}},
        {"precision": "fp16"},
        {"training_implementation_version": "training-implementation.v2"},
    ],
)
def test_reproducibility_changes_change_the_hash(change):
    from ml_model.training.run_contract import contract_sha256

    assert contract_sha256(_contract()) != contract_sha256(_contract(**change))


def test_model_revision_changes_the_hash():
    from ml_model.training.run_contract import contract_sha256

    changed = _contract(
        model_contracts={
            "distilbert": {
                "model_id": "distilbert-base-uncased",
                "model_revision": "different-revision",
                "architecture": "distilbert_sequence_classification",
            }
        }
    )

    assert contract_sha256(_contract()) != contract_sha256(changed)


def test_contract_contains_no_machine_specific_paths():
    from ml_model.training.run_contract import canonical_json

    contract = _contract()
    serialized = canonical_json(contract)

    assert str(Path("C:/Users/example/.cache/model")) not in serialized
    assert "\\" not in serialized
    assert "/tmp/" not in serialized


def test_contract_builder_does_not_upgrade_legacy_metadata():
    from ml_model.training.run_contract import require_contract_hash

    with pytest.raises(ValueError, match="contract"):
        require_contract_hash(
            {"architecture": "transformer", "model_key": "distilbert"}
        )


def test_persisted_contract_requires_current_schema_version_and_full_payload():
    from ml_model.training.run_contract import contract_sha256, require_contract_hash

    legacy_contract = _contract()
    legacy_contract["contract_version"] = "training-run-contract.v1"
    payload = {
        "run_contract": legacy_contract,
        "run_contract_sha256": contract_sha256(legacy_contract),
    }

    with pytest.raises(ValueError, match="contract_version"):
        require_contract_hash(payload)


def test_persisted_contract_rejects_incomplete_current_schema():
    from ml_model.training.run_contract import contract_sha256, require_contract_hash

    incomplete_contract = {
        "contract_version": "training-run-contract.v2",
        "model_key": "distilbert",
    }

    with pytest.raises(ValueError, match="missing required fields"):
        require_contract_hash(
            {
                "run_contract": incomplete_contract,
                "run_contract_sha256": contract_sha256(incomplete_contract),
            }
        )


def test_multi_model_contract_records_each_models_training_settings():
    from ml_model.training.run_contract import build_training_run_contract

    contract = build_training_run_contract(
        dataset_version="v3_907k_cleaned",
        preprocessing_version="http-preprocessor-v1",
        model_keys=["distilbert", "minilm_l6"],
        model_contracts={
            "distilbert": {
                "model_id": "distilbert-base-uncased",
                "model_revision": "distilbert-revision",
                "architecture": "distilbert_sequence_classification",
            },
            "minilm_l6": {
                "model_id": "nreimers/MiniLM-L6-H384-uncased",
                "model_revision": "minilm-revision",
                "architecture": "transformer",
            },
        },
        training_settings_by_model={
            "distilbert": {
                "learning_rate": 3e-5,
                "per_device_train_batch_size": 64,
                "eval_batch_size": 128,
                "gradient_accumulation_steps": 2,
                "weight_decay": 0.01,
                "warmup_ratio": 0.04,
                "max_seq_len": 128,
                "num_train_epochs": 4,
                "focal_gamma": 2.0,
            },
            "minilm_l6": {
                "learning_rate": 2e-5,
                "per_device_train_batch_size": 128,
                "eval_batch_size": 256,
                "gradient_accumulation_steps": 1,
                "weight_decay": 0.01,
                "warmup_ratio": 0.03,
                "max_seq_len": 128,
                "num_train_epochs": 4,
                "head_hidden_dim": 256,
            },
        },
        seed_list=[42],
        loss_keys=["weighted_ce"],
        max_seq_len=128,
        batch_size=64,
        eval_batch_size=128,
        epochs=4,
        learning_rate=3e-5,
        gradient_accumulation_steps=2,
        dataset_file_manifest_sha256="f" * 64,
        label_names=["Code Injection", "Normal", "Other Attacks", "SQL Injection"],
        class_mapping={
            "Code Injection": 0,
            "Normal": 1,
            "Other Attacks": 2,
            "SQL Injection": 3,
        },
        loss_contracts={"weighted_ce": {"focal_gamma": 2.0}},
        weight_decay=0.01,
        warmup_ratio=0.04,
        sample_limits={"train": None, "validation": None, "test": None},
        precision="full",
        training_implementation_version="training-implementation.v2",
    )

    assert contract["training_settings_by_model"]["distilbert"]["learning_rate"] == 3e-5
    assert contract["training_settings_by_model"]["minilm_l6"]["learning_rate"] == 2e-5
