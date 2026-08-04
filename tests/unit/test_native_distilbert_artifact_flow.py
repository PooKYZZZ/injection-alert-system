from __future__ import annotations

import json
from pathlib import Path

import torch
from transformers import AutoModelForSequenceClassification, DistilBertConfig

from ml_model.export.package_serving_artifact import (
    CalibrationProvenance,
    build_manifest,
)
from ml_model.export.promote_final_training_run import extract_state_dict_checkpoint


REVISION = "12040accade4e8a0f71eabdb258fecc2e7e948be"


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
    config_used_path.write_text(
        json.dumps(
            {
                "model_key": "distilbert",
                "model_id": "distilbert-base-uncased",
                "model_revision": REVISION,
                "tokenizer_id": "distilbert-base-uncased",
                "tokenizer_revision": REVISION,
                "run_contract_sha256": "a" * 64,
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
        label_names=["Code Injection", "Normal", "Other Attacks", "SQL Injection"],
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
