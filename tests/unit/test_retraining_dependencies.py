from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from ml_model.retraining.content_digest import compute_content_digest
from web_app.presentation.dependencies import retraining as retraining_dependencies
from web_app.presentation.dependencies.retraining import (
    _active_model_identity,
    _content_digest,
    _source_dataset_version_for_mode,
)


def test_retraining_identity_uses_model_bytes_not_version_strings(tmp_path: Path):
    artifact = tmp_path / "model"
    artifact.mkdir()
    (artifact / "weights.bin").write_bytes(b"version-independent bytes")
    service = SimpleNamespace(
        model_version="active-v1",
        model_input_version="model-input-v2-redacted",
        artifact_path=artifact,
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(model_service=service)))

    version, preprocessing, digest = _active_model_identity(request)

    assert version == "active-v1"
    assert preprocessing == "model-input-v2-redacted"
    assert digest == compute_content_digest(artifact)

    (artifact / "weights.bin").write_bytes(b"different bytes")
    assert _content_digest(artifact) != digest


def test_retraining_identity_fails_closed_without_a_loaded_artifact():
    service = SimpleNamespace(
        model_version="active-v1",
        model_input_version="model-input-v2-redacted",
        artifact_path=None,
    )
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(model_service=service)))

    with pytest.raises(HTTPException) as raised:
        _active_model_identity(request)

    assert getattr(raised.value, "status_code", None) == 503


def test_stable_content_identity_is_cached_by_immutable_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    artifact = tmp_path / "model"
    artifact.mkdir()
    (artifact / "weights.bin").write_bytes(b"stable bytes")
    calls = 0
    original_digest = retraining_dependencies.compute_artifact_digest

    def counted_digest(path):
        nonlocal calls
        calls += 1
        return original_digest(path)

    retraining_dependencies._cached_content_digest.cache_clear()
    monkeypatch.setattr(
        retraining_dependencies, "compute_artifact_digest", counted_digest
    )

    first = retraining_dependencies._cached_content_digest(
        str(artifact), "model:active-v1"
    )
    second = retraining_dependencies._cached_content_digest(
        str(artifact), "model:active-v1"
    )

    assert first == second
    assert calls == 1


def test_retraining_source_dataset_is_selected_by_worker_mode():
    assert _source_dataset_version_for_mode("smoke") == "v3_907k_cleaned"
    assert (
        _source_dataset_version_for_mode("native")
        == "v3_907k_cleaned_model_input_v2"
    )
