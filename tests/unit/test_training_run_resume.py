from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

PINNED_REVISION = "a" * 40


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
        "seed_list": [42],
        "loss_keys": ["weighted_ce"],
        "max_seq_len": 128,
        "batch_size": 64,
        "eval_batch_size": 128,
        "epochs": 4,
        "learning_rate": 0.00003,
        "gradient_accumulation_steps": 2,
        "dataset_file_manifest_sha256": "f" * 64,
    }
    payload.update(overrides)
    if "architecture" in overrides:
        payload["model_contracts"] = {
            "distilbert": {
                **payload["model_contracts"]["distilbert"],
                "architecture": overrides["architecture"],
            }
        }
    return build_training_run_contract(**payload)


def _write_bootstrap(
    run_dir: Path, contract: dict, *, contract_hash: str | None = None
):
    from ml_model.training.run_contract import contract_sha256

    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_bootstrap.json").write_text(
        json.dumps(
            {
                "run_contract": contract,
                "run_contract_sha256": contract_hash or contract_sha256(contract),
                "model_keys": contract["model_keys"],
                "dataset_version": contract["dataset_version"],
                "preprocessing_version": contract["preprocessing_version"],
                "seed_list": contract["seed_list"],
            }
        ),
        encoding="utf-8",
    )
    checkpoint = run_dir / "distilbert" / "weighted_ce" / "seed_0042" / "checkpoint"
    checkpoint.mkdir(parents=True)
    torch.save(
        {
            "model_state_dict": {"distilbert.weight": torch.tensor([1.0])},
            "model_key": "distilbert",
            "seed": 42,
            "loss_key": "weighted_ce",
            "architecture": contract["model_contracts"]["distilbert"][
                "architecture"
            ],
            "preprocessing_version": contract["preprocessing_version"],
            "run_contract_sha256": contract_hash or contract_sha256(contract),
        },
        checkpoint / "last.pt",
    )


def test_resume_discovery_rejects_historical_runs_without_contract(tmp_path: Path):
    from ml_model.training.train import find_latest_resumable_run_dir

    legacy = tmp_path / "run_legacy"
    (legacy / "checkpoint").mkdir(parents=True)
    torch.save({}, legacy / "checkpoint" / "last_legacy.pt")

    assert find_latest_resumable_run_dir(tmp_path, "run", "a" * 64) is None


def test_rng_checkpoint_payload_is_safe_load_compatible(tmp_path: Path):
    from ml_model.training.confirmatory_runner import (
        FinalConfirmatoryRunner,
        load_checkpoint_payload,
    )

    checkpoint = tmp_path / "rng.pt"
    torch.save(
        {
            "model_state_dict": {"weight": torch.tensor([1.0])},
            "rng_state": FinalConfirmatoryRunner.capture_rng_state(),
        },
        checkpoint,
    )

    payload = load_checkpoint_payload(checkpoint, context="rng-test")
    FinalConfirmatoryRunner.restore_rng_state(payload["rng_state"])


def test_resume_discovery_requires_exact_contract_hash_and_identity(tmp_path: Path):
    from ml_model.training.run_contract import contract_sha256
    from ml_model.training.train import find_latest_resumable_run_dir

    contract = _contract()
    matching = tmp_path / "run_matching"
    _write_bootstrap(matching, contract)
    mismatched = tmp_path / "run_mismatched"
    _write_bootstrap(mismatched, _contract(learning_rate=0.00002))

    assert (
        find_latest_resumable_run_dir(tmp_path, "run", contract_sha256(contract))
        == matching
    )


def test_resume_discovery_accepts_matching_incomplete_checkpoint(tmp_path: Path):
    from ml_model.training.run_contract import contract_sha256
    from ml_model.training.train import find_latest_resumable_run_dir

    contract = _contract()
    run_dir = tmp_path / "run_matching"
    _write_bootstrap(run_dir, contract)

    assert (
        find_latest_resumable_run_dir(tmp_path, "run", contract_sha256(contract))
        == run_dir
    )


def test_explicit_resume_checkpoint_rejects_incompatible_contract(tmp_path: Path):
    from ml_model.training.run_contract import contract_sha256
    from ml_model.training.train import validate_resume_checkpoint_contract

    checkpoint = tmp_path / "run" / "model" / "checkpoint" / "last.pt"
    checkpoint.parent.mkdir(parents=True)
    contract = _contract(seed_list=[42], architecture="transformer")
    _write_bootstrap(checkpoint.parents[2], contract)

    with pytest.raises(ValueError, match="contract mismatch"):
        validate_resume_checkpoint_contract(
            checkpoint,
            contract_sha256(_contract(seed_list=[42])),
            expected_model_key="distilbert",
            expected_seed=42,
            expected_loss_key="weighted_ce",
            expected_architecture="distilbert_sequence_classification",
            expected_preprocessing_version="http-preprocessor-v1",
        )


def test_explicit_resume_requires_one_model_and_one_seed():
    from ml_model.training.train import validate_explicit_resume_scope

    with pytest.raises(ValueError, match="exactly one model and one seed"):
        validate_explicit_resume_scope(
            checkpoint=Path("checkpoint.pt"),
            model_keys=["distilbert"],
            seeds=[42, 1337, 2026],
        )

    with pytest.raises(ValueError, match="exactly one model and one seed"):
        validate_explicit_resume_scope(
            checkpoint=Path("checkpoint.pt"),
            model_keys=["distilbert", "minilm_l6"],
            seeds=[42],
        )


def test_matching_explicit_resume_checkpoint_is_accepted(tmp_path: Path):
    from ml_model.training.run_contract import contract_sha256
    from ml_model.training.train import validate_resume_checkpoint_contract

    contract = _contract(seed_list=[42])
    checkpoint = tmp_path / "run" / "distilbert" / "weighted_ce" / "seed_0042" / "checkpoint" / "last.pt"
    _write_bootstrap(checkpoint.parents[4], contract)

    validate_resume_checkpoint_contract(
        checkpoint,
        contract_sha256(contract),
        expected_model_key="distilbert",
        expected_seed=42,
        expected_loss_key="weighted_ce",
        expected_architecture="distilbert_sequence_classification",
        expected_preprocessing_version="http-preprocessor-v1",
    )


def test_native_root_model_contract_metadata_is_self_describing():
    from ml_model.training.train import build_model_contract_metadata

    metadata = build_model_contract_metadata(
        {
            "distilbert": {
                "model_id": "distilbert-base-uncased",
                "model_revision": "verified-revision",
                "architecture": "distilbert_sequence_classification",
            }
        }
    )["distilbert"]

    assert metadata == {
        "model_id": "distilbert-base-uncased",
        "model_revision": "verified-revision",
        "architecture": "distilbert_sequence_classification",
        "architecture_family": "huggingface_sequence_classifier",
        "head_type": "hf_sequence_classification_head",
        "model_class": "DistilBertForSequenceClassification",
    }


def test_tokenizer_loader_passes_pinned_revision(monkeypatch):
    from ml_model.training import confirmatory_runner

    calls: list[dict[str, object]] = []

    def fake_from_pretrained(model_id: str, **kwargs):
        calls.append({"model_id": model_id, **kwargs})
        return object()

    monkeypatch.setattr(
        confirmatory_runner,
        "AutoTokenizer",
        SimpleNamespace(from_pretrained=fake_from_pretrained),
    )

    confirmatory_runner.load_tokenizer_for_config(
        {"model_id": "distilbert-base-uncased", "model_revision": PINNED_REVISION}
    )

    assert calls == [
        {
            "model_id": "distilbert-base-uncased",
            "use_fast": True,
            "revision": PINNED_REVISION,
        }
    ]


@pytest.mark.parametrize("revision", [None, "unresolved"])
def test_tokenizer_loader_rejects_missing_or_unresolved_revision(
    monkeypatch, revision
):
    from ml_model.training import confirmatory_runner

    calls: list[dict[str, object]] = []

    def fake_from_pretrained(model_id: str, **kwargs):
        calls.append({"model_id": model_id, **kwargs})
        return object()

    monkeypatch.setattr(
        confirmatory_runner,
        "AutoTokenizer",
        SimpleNamespace(from_pretrained=fake_from_pretrained),
    )

    with pytest.raises(ValueError, match="pinned model_revision"):
        confirmatory_runner.load_tokenizer_for_config(
            {"model_id": "distilbert-base-uncased", "model_revision": revision}
        )

    assert calls == []


def _runner(tmp_path: Path, *, seeds: list[int] | None = None):
    from ml_model.training.confirmatory_runner import FinalConfirmatoryRunner
    from ml_model.training.run_contract import contract_sha256

    contract = _contract()
    runner = object.__new__(FinalConfirmatoryRunner)
    runner.ctx = SimpleNamespace(
        run_contract=contract,
        run_contract_sha256=contract_sha256(contract),
        dataset_version=contract["dataset_version"],
        preprocessing_version=contract["preprocessing_version"],
        benchmark_seeds=seeds or [42],
        fixed_loss_key="weighted_ce",
        model_registry={
            "distilbert": {
                "model_key": "distilbert",
                "model_id": "distilbert-base-uncased",
                "architecture": "distilbert_sequence_classification",
                "num_train_epochs": 4,
                "max_seq_len": 128,
            }
        },
    )
    return runner


def _write_completed_seed(
    runner,
    tmp_path: Path,
    seed_number: int = 42,
    checkpoint_overrides: dict | None = None,
    **overrides,
):
    paths = runner.build_seed_paths(
        tmp_path / "variant", "distilbert", "weighted_ce", seed_number
    )
    paths["seed_dir"].mkdir(parents=True, exist_ok=True)
    paths["ckpt_dir"].mkdir(parents=True, exist_ok=True)
    metadata = {
        "run_contract_sha256": runner.ctx.run_contract_sha256,
        "model_key": "distilbert",
        "model_id": "distilbert-base-uncased",
        "architecture": "distilbert_sequence_classification",
        "seed": seed_number,
        "loss_key": "weighted_ce",
        "dataset_version": runner.ctx.dataset_version,
        "preprocessing_version": runner.ctx.preprocessing_version,
        "model_class": "DistilBertForSequenceClassification",
    }
    metadata.update(overrides)
    for name in ("config_metadata.json", "summary_metrics.json"):
        payload = {
            **metadata,
            "best_epoch": 1,
            "val_macro_f1": 0.5,
            "test_macro_f1": 0.5,
        }
        paths["seed_dir"].joinpath(name).write_text(
            json.dumps(payload), encoding="utf-8"
        )
    paths["completed_marker"].write_text(json.dumps(metadata), encoding="utf-8")
    checkpoint_payload = {
        "epoch": 1,
        "model_state_dict": {"distilbert.weight": torch.tensor([1.0])},
        "model_key": "distilbert",
        "seed": seed_number,
        "loss_key": "weighted_ce",
        "architecture": "distilbert_sequence_classification",
        "model_class": "DistilBertForSequenceClassification",
        "preprocessing_version": runner.ctx.preprocessing_version,
        "run_contract_sha256": runner.ctx.run_contract_sha256,
    }
    checkpoint_payload.update(checkpoint_overrides or {})
    torch.save(checkpoint_payload, paths["best_ckpt"])
    return paths


def test_matching_completed_seed_is_skipped_safely(tmp_path: Path):
    runner = _runner(tmp_path)
    paths = _write_completed_seed(runner, tmp_path)

    valid, reason, summary = runner.validate_completed_seed_artifacts(paths)

    assert valid is True
    assert reason == "ok"
    assert summary["run_contract_sha256"] == runner.ctx.run_contract_sha256


def test_completed_seed_without_config_metadata_is_not_valid(tmp_path: Path):
    runner = _runner(tmp_path)
    paths = _write_completed_seed(runner, tmp_path)
    paths["config_metadata"].unlink()

    valid, reason, _ = runner.validate_completed_seed_artifacts(paths)

    assert valid is False
    assert reason == "config_metadata_missing"


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("architecture", "transformer", "architecture_mismatch"),
        ("model_id", "other/model", "model_id_mismatch"),
        ("seed", 1337, "seed_mismatch"),
        ("loss_key", "focal", "loss_key_mismatch"),
        ("run_contract_sha256", "b" * 64, "contract_mismatch"),
    ],
)
def test_mismatched_completed_seed_is_rerun(tmp_path: Path, field, value, reason):
    runner = _runner(tmp_path)
    paths = _write_completed_seed(runner, tmp_path, **{field: value})

    valid, actual_reason, _ = runner.validate_completed_seed_artifacts(paths)

    assert valid is False
    assert actual_reason == reason


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("model_key", "minilm_l6", "checkpoint_model_key_mismatch"),
        ("seed", 1337, "checkpoint_seed_mismatch"),
        ("architecture", "transformer", "checkpoint_architecture_mismatch"),
        ("run_contract_sha256", "b" * 64, "checkpoint_contract_mismatch"),
    ],
)
def test_checkpoint_identity_mismatch_invalidates_completed_seed(
    tmp_path: Path, field, value, reason
):
    runner = _runner(tmp_path)
    paths = _write_completed_seed(
        runner,
        tmp_path,
        checkpoint_overrides={field: value},
    )

    valid, actual_reason, _ = runner.validate_completed_seed_artifacts(paths)

    assert valid is False
    assert actual_reason == reason


@pytest.mark.parametrize(
    "payload",
    [
        b"truncated checkpoint",
        {"epoch": 1},
        {"model_state_dict": {"distilbert.weight": "not a tensor"}},
    ],
)
def test_corrupt_or_incomplete_best_checkpoint_invalidates_completed_seed(
    tmp_path: Path, payload
):
    runner = _runner(tmp_path)
    paths = _write_completed_seed(runner, tmp_path)
    if isinstance(payload, bytes):
        paths["best_ckpt"].write_bytes(payload)
    else:
        torch.save(payload, paths["best_ckpt"])

    valid, reason, _ = runner.validate_completed_seed_artifacts(paths)

    assert valid is False
    assert reason.startswith("checkpoint_")


def test_aggregation_rejects_mixed_contract_hashes(tmp_path: Path):
    runner = _runner(tmp_path, seeds=[42, 1337])
    variant_dir = tmp_path / "variant"
    _write_completed_seed(runner, tmp_path)
    _write_completed_seed(
        runner, tmp_path, seed_number=1337, run_contract_sha256="c" * 64
    )

    with pytest.raises(ValueError, match="contract"):
        runner.aggregate_variant_from_disk(
            runner.ctx.model_registry["distilbert"], "weighted_ce", variant_dir
        )
