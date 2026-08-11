from pathlib import Path
import json

import pytest

from web_app.config import Settings
from web_app.services.model_service import ModelService
from ml_model.retraining.content_digest import compute_content_digest


def _make_settings(model_registry_path: Path, app_env: str) -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite://",
        app_env=app_env,
        model_path="unused",
        model_registry_path=str(model_registry_path),
        api_secret_key="test-secret",
    )


def _make_run_dir(base_dir: Path, name: str) -> Path:
    run_dir = base_dir / name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "best_distilbert_ckpt.pt").write_bytes(b"checkpoint")
    (run_dir / "config_used.json").write_text(
        '{"preprocessing_version":"model-input-v2-redacted"}',
        encoding="utf-8",
    )
    return run_dir


def _make_packaged_dir(base_dir: Path, name: str = "distillbert") -> Path:
    package_dir = base_dir / name
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "serving_manifest.json").write_text(
        '{"model_version":"distilbert_v3_907k_cleaned_20260312_133755",'
        '"preprocessing_version":"model-input-v2-redacted"}',
        encoding="utf-8",
    )
    (package_dir / "config.json").write_text("{}", encoding="utf-8")
    (package_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    return package_dir


def test_confidence_tier_boundaries_are_locked():
    assert ModelService._confidence_tier_for(0.49) == "LOW"
    assert ModelService._confidence_tier_for(0.50) == "MEDIUM"
    assert ModelService._confidence_tier_for(0.799999) == "MEDIUM"
    assert ModelService._confidence_tier_for(0.80) == "MEDIUM"
    assert ModelService._confidence_tier_for(0.800001) == "HIGH"


def test_confidence_tier_boundaries_extend_to_critical():
    assert ModelService._confidence_tier_for(0.899999) == "HIGH"
    assert ModelService._confidence_tier_for(0.8999999999999999) == "HIGH"
    assert ModelService._confidence_tier_for(0.90) == "CRITICAL"
    assert ModelService._confidence_tier_for(1.0) == "CRITICAL"


def test_confidence_thresholds_include_critical_band():
    service = ModelService.create_mock()

    assert service.confidence_thresholds == {
        "low": 0.50,
        "high": 0.80,
        "critical": 0.90,
    }


def test_production_requires_explicit_run_directory(tmp_path: Path):
    staging_dir = tmp_path / "staging"
    _make_run_dir(staging_dir, "distilbert_v3_907k_cleaned_20260312_133755")

    settings = _make_settings(tmp_path, "production")

    with pytest.raises(RuntimeError, match="explicit model run directory"):
        ModelService(settings)


def test_development_broad_path_resolves_latest_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    staging_dir = tmp_path / "staging"
    _make_run_dir(staging_dir, "distilbert_v3_907k_cleaned_20260312_133755")
    latest_run = _make_run_dir(staging_dir, "distilbert_v3_907k_cleaned_20260312_140000")

    monkeypatch.setattr(
        ModelService,
        "_load_run_artifacts",
        lambda self, run_dir: (object(), object(), 0.596868),
    )

    service = ModelService(_make_settings(tmp_path, "development"))

    assert service.model_version == latest_run.name
    assert service.model_input_version == "model-input-v2-redacted"
    assert latest_run.name in caplog.text


def test_active_model_pointer_pins_restart_to_verified_content(tmp_path, monkeypatch):
    staging_dir = tmp_path / "staging"
    active_run = _make_run_dir(staging_dir, "distilbert_active_v1")
    (staging_dir / "active_model.json").write_text(
        json.dumps(
            {
                "artifact_version": "staging-pointer.v1",
                "model_version": active_run.name,
                "artifact_digest": compute_content_digest(active_run),
                "directory": active_run.name,
                "preprocessing_version": "model-input-v2-redacted",
            }
        ),
        encoding="utf-8",
    )
    replacement = _make_run_dir(staging_dir, "distilbert_zzzz")

    monkeypatch.setattr(
        ModelService,
        "_load_run_artifacts",
        lambda self, run_dir: (object(), object(), 0.596868),
    )

    service = ModelService(_make_settings(tmp_path, "development"))

    assert service.artifact_path == active_run.resolve()
    assert service.artifact_path != replacement.resolve()


def test_active_model_pointer_fails_closed_when_bytes_change(tmp_path, monkeypatch):
    staging_dir = tmp_path / "staging"
    active_run = _make_run_dir(staging_dir, "distilbert_active_v1")
    digest = compute_content_digest(active_run)
    (staging_dir / "active_model.json").write_text(
        json.dumps(
            {
                "artifact_version": "staging-pointer.v1",
                "model_version": active_run.name,
                "artifact_digest": digest,
                "directory": active_run.name,
                "preprocessing_version": "model-input-v2-redacted",
            }
        ),
        encoding="utf-8",
    )
    (active_run / "best_distilbert_ckpt.pt").write_bytes(b"changed")

    monkeypatch.setattr(
        ModelService,
        "_load_run_artifacts",
        lambda self, run_dir: (object(), object(), 0.596868),
    )

    with pytest.raises(RuntimeError, match="pointer digest"):
        ModelService(_make_settings(tmp_path, "development"))


def test_explicit_run_directory_does_not_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    staging_dir = tmp_path / "staging"
    pinned_run = _make_run_dir(staging_dir, "distilbert_v3_907k_cleaned_20260312_133755")
    _make_run_dir(staging_dir, "distilbert_v3_907k_cleaned_20260312_140000")

    monkeypatch.setattr(
        ModelService,
        "_load_run_artifacts",
        lambda self, run_dir: (object(), object(), 0.596868),
    )

    service = ModelService(_make_settings(pinned_run, "production"))

    assert service.model_version == pinned_run.name


def test_packaged_artifact_directory_is_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    packaged_dir = _make_packaged_dir(tmp_path)

    monkeypatch.setattr(
        ModelService,
        "_load_run_artifacts",
        lambda self, run_dir: (object(), object(), 0.596868),
    )

    service = ModelService(_make_settings(packaged_dir, "production"))

    assert service.model_version == "distilbert_v3_907k_cleaned_20260312_133755"


def test_known_legacy_model_uses_explicit_v1_compatibility_rule(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    run_dir = _make_run_dir(tmp_path, "distilbert_v3_907k_cleaned_20260312_133755")
    (run_dir / "config_used.json").write_text(
        '{"dataset_version":"v3_907k_cleaned"}',
        encoding="utf-8",
    )

    monkeypatch.setattr(
        ModelService,
        "_load_run_artifacts",
        lambda self, path: (object(), object(), 0.596868),
    )
    service = ModelService(_make_settings(run_dir, "production"))

    assert service.model_input_version == "http-preprocessor-v1"


def test_unknown_metadata_less_model_is_rejected(tmp_path: Path):
    run_dir = _make_run_dir(tmp_path, "distilbert_unknown")
    (run_dir / "config_used.json").write_text(
        '{"model_version":"unknown"}',
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="missing preprocessing_version"):
        ModelService(_make_settings(run_dir, "production"))
