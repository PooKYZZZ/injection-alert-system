from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from ml_model.project_paths import PROJECT_ROOT, project_path
from ml_model.retraining.content_digest import compute_content_digest
from ml_model.retraining.dashboard_pipeline import NativeDashboardPipeline
from web_app.infrastructure.retraining_process_runner import RetrainingProcessRunner
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
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(model_service=service))
    )

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
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(model_service=service))
    )

    with pytest.raises(HTTPException) as raised:
        _active_model_identity(request)

    assert getattr(raised.value, "status_code", None) == 503


def test_retraining_identity_recomputes_model_digest_after_artifact_changes(
    tmp_path: Path,
):
    artifact = tmp_path / "model"
    artifact.mkdir()
    weights = artifact / "weights.bin"
    weights.write_bytes(b"first model bytes")
    service = SimpleNamespace(
        model_version="active-v1",
        model_input_version="model-input-v2-redacted",
        artifact_path=artifact,
    )
    request = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(model_service=service))
    )

    first = _active_model_identity(request)
    weights.write_bytes(b"second model bytes")
    second = _active_model_identity(request)

    assert first[2] != second[2]


def test_retraining_source_dataset_is_selected_by_worker_mode():
    assert _source_dataset_version_for_mode("smoke") == "v3_907k_cleaned"
    assert (
        _source_dataset_version_for_mode("native")
        == "v3_907k_cleaned_model_input_v2"
    )


def test_project_paths_do_not_depend_on_the_process_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)

    assert PROJECT_ROOT == Path(__file__).resolve().parents[2]
    assert project_path("data/processed/v3_907k_cleaned") == (
        PROJECT_ROOT / "data" / "processed" / "v3_907k_cleaned"
    )
    assert RetrainingProcessRunner().project_root == PROJECT_ROOT
    assert NativeDashboardPipeline()._project_root == PROJECT_ROOT

    with pytest.raises(ValueError, match="repository-relative"):
        project_path("../outside")
