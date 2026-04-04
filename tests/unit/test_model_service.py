from pathlib import Path

import pytest

from web_app.config import Settings
from web_app.services.model_service import ModelService


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
    return run_dir


def _make_packaged_dir(base_dir: Path, name: str = "distillbert") -> Path:
    package_dir = base_dir / name
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "serving_manifest.json").write_text(
        '{"model_version":"distilbert_v3_907k_cleaned_20260312_133755"}',
        encoding="utf-8",
    )
    (package_dir / "config.json").write_text("{}", encoding="utf-8")
    (package_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
    return package_dir


def test_confidence_tier_boundaries_are_locked():
    assert ModelService._confidence_tier_for(0.49) == "LOW"
    assert ModelService._confidence_tier_for(0.50) == "MEDIUM"
    assert ModelService._confidence_tier_for(0.799999) == "MEDIUM"
    assert ModelService._confidence_tier_for(0.80) == "HIGH"


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
    assert latest_run.name in caplog.text


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
