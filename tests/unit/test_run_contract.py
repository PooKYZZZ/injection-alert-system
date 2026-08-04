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
    }
    payload.update(overrides)
    return build_training_run_contract(**payload)


def test_identical_contracts_have_identical_hashes():
    from ml_model.training.run_contract import contract_sha256

    assert contract_sha256(_contract()) == contract_sha256(_contract())


def test_dictionary_order_does_not_change_hash():
    from ml_model.training.run_contract import contract_sha256

    first = _contract()
    second = {
        "gradient_accumulation_steps": first["gradient_accumulation_steps"],
        "learning_rate": first["learning_rate"],
        "epochs": first["epochs"],
        "eval_batch_size": first["eval_batch_size"],
        "batch_size": first["batch_size"],
        "max_seq_len": first["max_seq_len"],
        "loss_keys": first["loss_keys"],
        "seed_list": first["seed_list"],
        "model_contracts": first["model_contracts"],
        "model_keys": first["model_keys"],
        "preprocessing_version": first["preprocessing_version"],
        "dataset_version": first["dataset_version"],
        "contract_version": first["contract_version"],
        "model_id": first["model_id"],
        "model_revision": first["model_revision"],
        "architecture": first["architecture"],
    }
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
