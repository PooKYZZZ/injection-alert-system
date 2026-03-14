from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from web_app.config import Settings
from web_app.presentation import app as app_module


def _make_settings(model_registry_path: Path, app_env: str) -> Settings:
    return Settings(
        database_url="sqlite+aiosqlite://",
        app_env=app_env,
        model_path="unused",
        model_registry_path=str(model_registry_path),
        api_secret_key="test-secret",
    )


async def _fake_init_db() -> None:
    return None


def test_startup_fails_fast_when_artifact_missing_in_production(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    missing_path = tmp_path / "missing-run"

    monkeypatch.setattr(
        app_module,
        "get_settings",
        lambda: _make_settings(missing_path, "production"),
    )
    monkeypatch.setattr(app_module, "init_db", _fake_init_db)

    with pytest.raises(RuntimeError, match="MODEL_REGISTRY_PATH"):
        with TestClient(app_module.create_app()):
            pass


def test_startup_uses_mock_service_when_artifact_missing_in_testing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    missing_path = tmp_path / "missing-run"
    mock_service = object()

    class FakeModelService:
        def __init__(self, settings):
            raise AssertionError("real loader should not run for missing test artifact")

        @classmethod
        def create_mock(cls):
            return mock_service

    monkeypatch.setattr(
        app_module,
        "get_settings",
        lambda: _make_settings(missing_path, "testing"),
    )
    monkeypatch.setattr(app_module, "init_db", _fake_init_db)
    monkeypatch.setattr(app_module, "ModelService", FakeModelService)

    app = app_module.create_app()
    with TestClient(app):
        assert app.state.model_service is mock_service
        assert app.state.model is mock_service


def test_startup_stores_real_model_service_on_app_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    run_dir = tmp_path / "distilbert_v3_907k_cleaned_20260312_133755"
    run_dir.mkdir()
    (run_dir / "best_distilbert_ckpt.pt").write_bytes(b"checkpoint")

    class FakeModelService:
        def __init__(self, settings):
            self.settings = settings
            self.model_version = "distilbert_v3_907k_cleaned_20260312_133755"

        @classmethod
        def create_mock(cls):
            raise AssertionError("mock loader should not run for explicit artifact path")

    monkeypatch.setattr(
        app_module,
        "get_settings",
        lambda: _make_settings(run_dir, "production"),
    )
    monkeypatch.setattr(app_module, "init_db", _fake_init_db)
    monkeypatch.setattr(app_module, "ModelService", FakeModelService)

    app = app_module.create_app()
    with TestClient(app):
        assert isinstance(app.state.model_service, FakeModelService)
        assert app.state.model is app.state.model_service
