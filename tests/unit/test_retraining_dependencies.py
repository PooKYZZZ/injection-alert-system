from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from ml_model.retraining.content_digest import compute_content_digest
from web_app.presentation.dependencies.retraining import (
    _active_model_identity,
    _content_digest,
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
