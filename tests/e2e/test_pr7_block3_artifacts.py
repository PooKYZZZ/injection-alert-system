from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.pr7_block3_artifacts import (
    load_artifact_lock,
    require_pinned_compose_images,
    require_portal_commit,
    require_real_model_health,
    verify_model_lock,
)


def test_block3bc_lock_is_loaded_and_has_current_portal_commit() -> None:
    root = Path(__file__).parents[2]
    lock = load_artifact_lock(root / "docs/project-ops/pr7-block3bc-artifact-lock.json")
    assert lock["portal"]["commit"] == "139039cff70fd92977bd23097b6a9e430daba301"
    assert lock["portal"]["repository"] == "PooKYZZZ/injection-alert-system"


def test_model_lock_rejects_missing_artifact(tmp_path: Path) -> None:
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "model": {
                    "files": [{"path": "missing.bin", "sha256": "0" * 64}]
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="missing"):
        verify_model_lock(tmp_path, lock_path)


def test_portal_commit_rejects_dirty_checkout(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "tests.e2e.pr7_block3_artifacts.subprocess.run",
        lambda command, **kwargs: type(
            "Result", (), {"stdout": "expected\n" if command[-1] == "HEAD" else " M file"}
        )(),
    )
    with pytest.raises(AssertionError, match="not clean"):
        require_portal_commit(tmp_path, "expected")


def test_pinned_compose_check_accepts_all_overlay_inputs(tmp_path: Path) -> None:
    lock_path = tmp_path / "lock.json"
    lock_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "containers": {"waf": "waf@sha256:test"},
            }
        ),
        encoding="utf-8",
    )
    compose_a = tmp_path / "a.yml"
    compose_b = tmp_path / "b.yml"
    compose_a.write_text("services: {}\n", encoding="utf-8")
    compose_b.write_text("image: waf@sha256:test\n", encoding="utf-8")
    require_pinned_compose_images((compose_a, compose_b), lock_path)


def test_real_model_health_rejects_degraded_or_mock_payloads() -> None:
    with pytest.raises(AssertionError, match="healthy"):
        require_real_model_health({"status": "degraded"}, "locked")
    with pytest.raises(AssertionError, match="mock"):
        require_real_model_health(
            {
                "status": "healthy",
                "loaded": True,
                "model_version": "locked",
                "mock": True,
            },
            "locked",
        )
