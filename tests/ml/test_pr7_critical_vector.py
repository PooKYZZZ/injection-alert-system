from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.e2e.pr7_block3_artifacts import verify_model_lock
from web_app.application.http_preprocessor import preprocess_http_request
from web_app.config import Settings
from web_app.services.model_service import ModelService

RUN_REAL_MODEL = os.environ.get("PR7_RUN_REAL_MODEL") == "1"
RUN_DIR = Path(__file__).resolve().parents[2] / (
    "ml_model/model_registry/staging/"
    "distilbert_v3_907k_cleaned_20260312_133755"
)
VECTOR = "GET /records/search?id=1%20OR%201=1-- HTTP/1.1\nHost: localhost"


@pytest.mark.skipif(
    not RUN_REAL_MODEL,
    reason="set PR7_RUN_REAL_MODEL=1 to run the pinned real-model vector",
)
def test_pinned_pr7_vector_is_sql_injection_critical() -> None:
    lock = verify_model_lock(RUN_DIR)
    manifest = json.loads(
        (RUN_DIR / "serving_manifest.json").read_text(encoding="utf-8")
    )
    settings = Settings(
        env_file=False,
        database_url="sqlite+aiosqlite:///test.db",
        model_path=str(RUN_DIR),
        model_registry_path=str(RUN_DIR),
        app_env="testing",
    )

    result = ModelService(settings).predict(preprocess_http_request(VECTOR))

    assert manifest["model_version"] == lock["model"]["model_version"]
    assert manifest["temperature"] == pytest.approx(0.596868)
    assert result["model_version"] == lock["model"]["model_version"]
    assert result["prediction"] == "SQL Injection"
    assert result["confidence_tier"] == "CRITICAL"
    assert result["confidence"] >= settings.confidence_critical_threshold
