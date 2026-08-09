from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import torch
from transformers import (
    AutoModelForSequenceClassification,
    BertTokenizerFast,
    DistilBertConfig,
)

import ml_model.export.package_serving_artifact as package_module
from ml_model.export.package_serving_artifact import (
    CalibrationProvenance,
    PackagingError,
    bind_summary_metrics_to_packaged_artifact,
    build_manifest,
    ensure_required_run_files,
    stage_training_summary_for_packaging,
)
from ml_model.export.promote_final_training_run import extract_state_dict_checkpoint
from ml_model.retraining.run_baseline import _load_verified_summary_metrics
from ml_model.training.run_contract import build_training_run_contract, contract_sha256

REVISION = "12040accade4e8a0f71eabdb258fecc2e7e948be"
LABEL_NAMES = ["Code Injection", "Normal", "Other Attacks", "SQL Injection"]


def test_packaging_requires_summary_metrics_provenance_file(tmp_path: Path):
    for name in ("config_used.json", "eval_report.json", "git_hash.txt"):
        (tmp_path / name).write_text("{}\n", encoding="utf-8")

    with pytest.raises(PackagingError, match="summary_metrics.json"):
        ensure_required_run_files(tmp_path)


def test_candidate_summary_is_staged_and_bound_to_final_artifact(tmp_path: Path):
    source_summary_path = tmp_path / "training" / "summary_metrics.json"
    original_summary = {
        "test_accuracy": 0.99,
        "test_macro_f1": 0.98,
        "test_weighted_f1": 0.991,
        "normal_false_positive_rate": 0.001,
        "attack_escape_rate": 0.002,
        "custom_metric": {"preserve": True},
    }
    source_summary_path.parent.mkdir(parents=True)
    source_summary_path.write_text(
        json.dumps(original_summary, indent=2) + "\n", encoding="utf-8"
    )

    candidate_run = tmp_path / "candidate"
    staged = stage_training_summary_for_packaging(
        source_summary_path=source_summary_path,
        candidate_run=candidate_run,
    )
    assert staged == original_summary
    assert json.loads(
        (candidate_run / "summary_metrics.json").read_text(encoding="utf-8")
    ) == original_summary

    checkpoint_path = candidate_run / "model.safetensors"
    checkpoint_path.write_bytes(b"packaged-checkpoint")
    manifest_path = candidate_run / "serving_manifest.json"
    manifest = {
        "checkpoint_file": checkpoint_path.name,
        "checkpoint_sha256": package_module.sha256_file(checkpoint_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    summary_path = bind_summary_metrics_to_packaged_artifact(
        packaged_run=candidate_run,
        source_summary_path=source_summary_path,
        summary_metrics=staged,
    )
    final_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert final_summary["custom_metric"] == original_summary["custom_metric"]
    assert final_summary["checkpoint_sha256"] == package_module.sha256_file(
        checkpoint_path
    )
    assert final_summary["artifact_manifest_sha256"] == package_module.sha256_file(
        manifest_path
    )
    assert final_summary["source_summary_sha256"] == package_module.sha256_file(
        source_summary_path
    )
    verified = _load_verified_summary_metrics(
        candidate_run, manifest_path, manifest
    )
    assert verified["test_macro_f1"] == original_summary["test_macro_f1"]


def test_training_summary_staging_fails_for_missing_source(tmp_path: Path):
    with pytest.raises(PackagingError, match="Training summary is missing"):
        stage_training_summary_for_packaging(
            source_summary_path=tmp_path / "missing-summary.json",
            candidate_run=tmp_path / "candidate",
        )


def test_training_summary_staging_fails_for_malformed_source(tmp_path: Path):
    source_summary_path = tmp_path / "summary_metrics.json"
    source_summary_path.write_text("not-json", encoding="utf-8")

    with pytest.raises(PackagingError, match="Training summary is malformed"):
        stage_training_summary_for_packaging(
            source_summary_path=source_summary_path,
            candidate_run=tmp_path / "candidate",
        )


def make_training_contract() -> dict:
    return build_training_run_contract(
        dataset_version="v3_907k_cleaned",
        preprocessing_version="http-preprocessor-v1",
        model_keys=["distilbert"],
        model_contracts={
            "distilbert": {
                "model_id": "distilbert-base-uncased",
                "model_revision": REVISION,
                "architecture": "distilbert_sequence_classification",
            }
        },
        seed_list=[42],
        loss_keys=["weighted_ce"],
        max_seq_len=128,
        batch_size=4,
        eval_batch_size=8,
        epochs=1,
        learning_rate=3e-5,
        gradient_accumulation_steps=1,
        dataset_file_manifest_sha256="f" * 64,
        label_names=LABEL_NAMES,
        class_mapping={label: index for index, label in enumerate(LABEL_NAMES)},
        loss_contracts={"weighted_ce": {"focal_gamma": 2.0}},
        weight_decay=0.01,
        warmup_ratio=0.04,
        sample_limits={"train": 64, "validation": 32, "test": 32},
        precision="full",
        training_implementation_version="training-implementation.v2",
    )


def test_native_distilbert_checkpoint_round_trips_through_packaging_contract(
    tmp_path: Path,
):
    config = DistilBertConfig(
        vocab_size=101,
        max_position_embeddings=16,
        n_layers=1,
        n_heads=2,
        dim=16,
        hidden_dim=32,
        num_labels=4,
    )
    source_model = AutoModelForSequenceClassification.from_config(config)
    source_model.save_pretrained(tmp_path / "source_model")
    reloaded_model = AutoModelForSequenceClassification.from_pretrained(
        tmp_path / "source_model", local_files_only=True
    )

    source_checkpoint = tmp_path / "source_checkpoint.pt"
    torch.save({"model_state_dict": source_model.state_dict()}, source_checkpoint)
    packaged_checkpoint = tmp_path / "packaged_checkpoint.pt"
    extract_state_dict_checkpoint(
        source_checkpoint,
        packaged_checkpoint,
        normalize_for_packager=True,
        architecture="distilbert_sequence_classification",
    )
    state = torch.load(packaged_checkpoint, map_location="cpu", weights_only=True)
    reloaded_model.load_state_dict(state, strict=True)

    config_used_path = tmp_path / "config_used.json"
    contract = make_training_contract()
    config_used_path.write_text(
        json.dumps(
            {
                "model_key": "distilbert",
                "model_id": "distilbert-base-uncased",
                "model_revision": REVISION,
                "tokenizer_id": "distilbert-base-uncased",
                "tokenizer_revision": REVISION,
                "run_contract": contract,
                "run_contract_sha256": contract_sha256(contract),
                "dataset_version": "v3_907k_cleaned",
                "preprocessing_version": "http-preprocessor-v1",
                "model_input_hash_policy": "sha256(model_input_text)",
                "architecture": "distilbert_sequence_classification",
                "architecture_family": "huggingface_sequence_classifier",
                "head_type": "hf_sequence_classification_head",
                "model_class": "DistilBertForSequenceClassification",
            }
        ),
        encoding="utf-8",
    )
    manifest = build_manifest(
        run_dir=tmp_path,
        model_key="distilbert",
        model_version="native_test",
        base_model="distilbert-base-uncased",
        checkpoint_path=packaged_checkpoint,
        config_used_path=config_used_path,
        calibration=CalibrationProvenance(
            eval_run_dir=tmp_path,
            promotion_summary_path=tmp_path / "promotion.json",
            result_path=tmp_path / "calibration.json",
            temperature=1.0,
        ),
        label_names=LABEL_NAMES,
        max_seq_len=128,
        notes=None,
        local_reload_verified=True,
        actual_model=reloaded_model,
    )

    assert type(reloaded_model).__name__ == "DistilBertForSequenceClassification"
    assert manifest["architecture"] == "distilbert_sequence_classification"
    assert manifest["model_class"] == "DistilBertForSequenceClassification"
    assert manifest["model_revision"] == REVISION
    assert all(
        not key.startswith(("classifier_dense.", "layer_norm.", "output."))
        for key in state
    )


@pytest.mark.parametrize("model_key", ["minilm", "bert-base"])
def test_native_packaging_rejects_historical_custom_model_keys(model_key: str):
    with pytest.raises(PackagingError, match="only model_key='distilbert'"):
        package_module.package_serving_artifact(model_key=model_key)


def test_packaging_cli_only_advertises_distilbert(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        sys, "argv", ["package_serving_artifact", "--model-key", "minilm"]
    )
    with pytest.raises(SystemExit):
        package_module.parse_args()


def test_offline_packaging_runs_real_function_and_strict_reload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    config = DistilBertConfig(
        vocab_size=32,
        max_position_embeddings=32,
        n_layers=1,
        n_heads=2,
        dim=16,
        hidden_dim=32,
        num_labels=4,
    )
    fixture_model_dir = tmp_path / "hf_fixture_model"
    fixture_model = AutoModelForSequenceClassification.from_config(config)
    fixture_model.save_pretrained(fixture_model_dir)

    vocab_path = tmp_path / "vocab.txt"
    vocab_path.write_text(
        "[PAD]\n[UNK]\n[CLS]\n[SEP]\n[MASK]\nselect\nfrom\nusers\nwhere\n1\n=\n--\n",
        encoding="utf-8",
    )
    fixture_tokenizer_dir = tmp_path / "hf_fixture_tokenizer"
    BertTokenizerFast(vocab_file=str(vocab_path)).save_pretrained(fixture_tokenizer_dir)

    original_config = package_module.AutoConfig
    original_model = package_module.AutoModelForSequenceClassification
    original_tokenizer = package_module.AutoTokenizer

    class OfflineConfig:
        @staticmethod
        def from_pretrained(name, **kwargs):
            if name == "distilbert-base-uncased":
                name = fixture_model_dir
                kwargs = {"local_files_only": True}
            return original_config.from_pretrained(name, **kwargs)

    class OfflineModel:
        @staticmethod
        def from_pretrained(name, **kwargs):
            if name == "distilbert-base-uncased":
                name = fixture_model_dir
                kwargs.pop("revision", None)
                kwargs["local_files_only"] = True
            return original_model.from_pretrained(name, **kwargs)

    class OfflineTokenizer:
        @staticmethod
        def from_pretrained(name, **kwargs):
            if name == "distilbert-base-uncased":
                name = fixture_tokenizer_dir
                kwargs.pop("revision", None)
                kwargs["local_files_only"] = True
            return original_tokenizer.from_pretrained(name, **kwargs)

    monkeypatch.setattr(package_module, "AutoConfig", OfflineConfig)
    monkeypatch.setattr(
        package_module, "AutoModelForSequenceClassification", OfflineModel
    )
    monkeypatch.setattr(package_module, "AutoTokenizer", OfflineTokenizer)

    repo_root = tmp_path / "repo"
    run_dir = (
        repo_root
        / "ml_model"
        / "model_registry"
        / "staging"
        / "distilbert_native_fixture"
    )
    eval_run_dir = repo_root / "ml_model" / "model_registry" / "eval" / "eval_fixture"
    run_dir.mkdir(parents=True)
    eval_run_dir.mkdir(parents=True)
    monkeypatch.setattr(
        package_module,
        "find_repo_root",
        lambda _start: (_ for _ in ()).throw(
            AssertionError("explicit repo_root must bypass cwd discovery")
        ),
    )

    contract = make_training_contract()
    contract_hash = contract_sha256(contract)
    (run_dir / "config_used.json").write_text(
        json.dumps(
            {
                "model_key": "distilbert",
                "model_id": "distilbert-base-uncased",
                "model_revision": REVISION,
                "tokenizer_id": "distilbert-base-uncased",
                "tokenizer_revision": REVISION,
                "run_contract": contract,
                "run_contract_sha256": contract_hash,
                "dataset_version": "v3_907k_cleaned",
                "preprocessing_version": "http-preprocessor-v1",
                "model_input_hash_policy": "sha256(model_input_text)",
                "architecture": "distilbert_sequence_classification",
                "architecture_family": "huggingface_sequence_classifier",
                "head_type": "hf_sequence_classification_head",
                "model_class": "DistilBertForSequenceClassification",
                "label_names": LABEL_NAMES,
                "max_seq_len": 16,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "eval_report.json").write_text(json.dumps({}), encoding="utf-8")
    (run_dir / "summary_metrics.json").write_text(
        json.dumps({"accuracy": 1.0, "macro avg": {}, "weighted avg": {}}),
        encoding="utf-8",
    )
    (run_dir / "git_hash.txt").write_text("fixture\n", encoding="utf-8")
    torch.save(
        fixture_model.state_dict(),
        run_dir / "best_distilbert_ckpt.pt",
    )
    (eval_run_dir / "promotion_summary.json").write_text(
        json.dumps(
            {
                "promotion_summary": {
                    "distilbert": {
                        "run_dir": run_dir.name,
                        "temperature": 1.0,
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (eval_run_dir / "eval_results_distilbert_calibrated.json").write_text(
        json.dumps({"temperature": 1.0}), encoding="utf-8"
    )

    result = package_module.package_serving_artifact(
        model_key="distilbert",
        run_dir_name=run_dir.name,
        strict=True,
        repo_root=repo_root,
    )

    manifest = json.loads(
        (result / "serving_manifest.json").read_text(encoding="utf-8")
    )
    assert result == run_dir.resolve()
    assert manifest["run_contract_sha256"] == contract_hash
    assert manifest["local_reload_verified"] is True
    assert any(path.name == "model.safetensors" for path in result.iterdir())
