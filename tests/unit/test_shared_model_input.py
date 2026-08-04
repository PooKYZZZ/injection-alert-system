from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from inspect import getsource

import pytest

from ml_model.preprocessing.dataset_io import resolve_data_dir, validate_dataset_preprocessing
from ml_model.preprocessing.model_input import (
    LEGACY_MODEL_INPUT_VERSION,
    MODEL_INPUT_BUILDER,
    MODEL_INPUT_HASH_POLICY,
    MODEL_INPUT_TEXT_COLUMN,
    MODEL_INPUT_VERSION,
    build_model_input_text,
    prepare_legacy_model_input,
    prepare_model_input,
)


def test_shared_builder_redacts_query_and_body_without_removing_attack_indicators():
    text = build_model_input_text(
        "POST",
        "/search?q=1%27%20UNION%20SELECT%20username%20FROM%20users&token=TOPSECRET",
        body='{"username":"admin\' OR \'1\'=\'1","password":"BODYSECRET"}',
    )

    assert "topsecret" not in text
    assert "bodysecret" not in text
    assert "union select" in text
    assert "or '1'='1" in text


def test_sensitive_values_keep_only_safe_attack_indicators():
    text = build_model_input_text(
        "POST",
        "/login?password=' OR 1=1--&token=TOPSECRET",
        body='{"password":";cat /etc/passwd","token":"BODYSECRET"}',
    )

    assert "topsecret" not in text
    assert "bodysecret" not in text
    assert "[indicator:sql]" in text
    assert "[indicator:command]" in text
    assert "' or 1=1" not in text
    assert ";cat /etc/passwd" not in text


def test_legacy_model_input_preserves_inference_text_but_declares_legacy_contract():
    raw = "POST /login?password=TOPSECRET HTTP/1.1\r\n\r\npassword=TOPSECRET"

    model_input, model_input_hash, version = prepare_legacy_model_input(raw)

    assert "topsecret" in model_input
    assert model_input_hash == sha256(model_input.encode("utf-8")).hexdigest()
    assert version == LEGACY_MODEL_INPUT_VERSION


def test_runtime_prepare_uses_shared_hash_and_version():
    raw = "GET /search?q=1%27&api_key=TOPSECRET HTTP/1.1\r\n\r\n"
    model_input, model_input_hash, version = prepare_model_input(raw)

    assert model_input == build_model_input_text("GET", "/search?q=1%27&api_key=TOPSECRET")
    assert model_input_hash == sha256(model_input.encode("utf-8")).hexdigest()
    assert version == MODEL_INPUT_VERSION


def test_dataset_metadata_validation_fails_closed_on_old_contract(tmp_path: Path):
    metadata_path = tmp_path / "metadata_preprocessing.json"
    metadata_path.write_text(
        '{"dataset_version":"v3_907k_cleaned",'
        '"preprocessing_version":"http-preprocessor-v1",'
        '"text_column":"combined_payload",'
        '"model_input_hash_policy":"sha256(model_input_text)"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Dataset version mismatch|incompatible"):
        validate_dataset_preprocessing(
            tmp_path,
            expected_dataset_version="v3_907k_cleaned_model_input_v2",
        )


def test_dataset_metadata_validation_accepts_shared_contract(tmp_path: Path):
    metadata_path = tmp_path / "metadata_preprocessing.json"
    metadata_path.write_text(
        "{"
        f'"dataset_version":"v3_907k_cleaned_model_input_v2",'
        f'"preprocessing_version":"{MODEL_INPUT_VERSION}",'
        f'"text_column":"{MODEL_INPUT_TEXT_COLUMN}",'
        f'"shared_builder_name":"{MODEL_INPUT_BUILDER}",'
        f'"model_input_hash_policy":"{MODEL_INPUT_HASH_POLICY}"'
        "}",
        encoding="utf-8",
    )

    metadata = validate_dataset_preprocessing(
        tmp_path,
        expected_dataset_version="v3_907k_cleaned_model_input_v2",
    )
    assert metadata["preprocessing_version"] == MODEL_INPUT_VERSION


def test_dataset_cleaner_builds_shared_text_before_identity_operations():
    source = Path("data/clean_907k.py").read_text(encoding="utf-8")
    assert "from ml_model.preprocessing.model_input" in source
    assert source.index("df[MODEL_INPUT_TEXT_COLUMN]") < source.index("drop_duplicates")
    assert "web_app" not in getsource(build_model_input_text)


def test_missing_dataset_fails_before_training_work(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Could not locate dataset directory"):
        resolve_data_dir("v3_907k_cleaned_model_input_v2", project_root=tmp_path)
