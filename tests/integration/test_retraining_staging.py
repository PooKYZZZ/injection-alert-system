import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from ml_model.preprocessing.model_input import MODEL_INPUT_HASH_POLICY
from web_app.infrastructure.retraining_staging_adapter import (
    LocalStagingAdapter,
    compute_artifact_digest,
)

LABELS = ["Code Injection", "Normal", "Other Attacks", "SQL Injection"]
RUN_ID = "retrain-20260811T120000Z-000000000001"


def _write_artifact(root: Path, version: str) -> Path:
    artifact = root / version
    artifact.mkdir(parents=True)
    config_used = b'{"preprocessing_version":"model-input-v2-redacted"}\n'
    checkpoint = b"controlled integration checkpoint"
    (artifact / "config_used.json").write_bytes(config_used)
    (artifact / "best_distilbert_ckpt.pt").write_bytes(checkpoint)
    (artifact / "config.json").write_text("{}\n", encoding="utf-8")
    (artifact / "tokenizer_config.json").write_text("{}\n", encoding="utf-8")
    (artifact / "tokenizer.json").write_text("{}\n", encoding="utf-8")
    (artifact / "model.safetensors").write_bytes(b"controlled integration weights")
    (artifact / "serving_manifest.json").write_text(
        json.dumps(
            {
                "model_version": version,
                "run_dir_name": version,
                "model_key": "distilbert",
                "preprocessing_version": "model-input-v2-redacted",
                "model_input_hash_policy": MODEL_INPUT_HASH_POLICY,
                "architecture": "distilbert_sequence_classification",
                "model_class": "DistilBertForSequenceClassification",
                "model_revision": "controlled-integration-fixture",
                "label_names": LABELS,
                "num_labels": len(LABELS),
                "local_reload_verified": True,
                "checkpoint_file": "best_distilbert_ckpt.pt",
                "checkpoint_sha256": hashlib.sha256(checkpoint).hexdigest(),
                "config_used_file": "config_used.json",
                "config_used_sha256": hashlib.sha256(config_used).hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    return artifact


def test_controlled_local_reload_and_rollback_updates_loaded_model_version(tmp_path):
    staging_root = tmp_path / "model_registry" / "staging"
    archive_root = tmp_path / "model_registry" / "archive"
    run_root = tmp_path / "runs"
    candidate_root = run_root / RUN_ID / "candidate_model"
    candidate_root.parent.mkdir(parents=True)
    candidate = _write_artifact(tmp_path / "candidate", "candidate-v1")
    active = _write_artifact(staging_root, "active-v1")
    candidate_root.mkdir()
    for source in candidate.iterdir():
        (candidate_root / source.name).write_bytes(source.read_bytes())

    app_state = SimpleNamespace(model_version="active-v1")

    def validate_load(path: Path, expected_version: str):
        return expected_version

    def reload_model(path: Path, expected_version: str):
        app_state.model_version = expected_version
        return expected_version

    adapter = LocalStagingAdapter(
        staging_root=staging_root,
        archive_root=archive_root,
        load_validator=validate_load,
        reload_callback=reload_model,
    )
    candidate_digest = compute_artifact_digest(candidate_root)
    plan = adapter.prepare_deployment(
        artifact_root=run_root,
        run_id=RUN_ID,
        candidate_model_version="candidate-v1",
        candidate_model_digest=candidate_digest,
        active_model_version="active-v1",
        active_model_digest="d" * 64,
        expected_preprocessing_version="model-input-v2-redacted",
    )

    deployed = adapter.deploy(plan)
    assert deployed.status == "DEPLOYED"
    assert app_state.model_version == "candidate-v1"
    assert not active.exists()

    rolled_back = adapter.rollback(
        deployed,
        requested_previous_version="active-v1",
    )
    assert rolled_back.status == "ROLLED_BACK"
    assert app_state.model_version == "active-v1"
    assert (staging_root / "active-v1").is_dir()
