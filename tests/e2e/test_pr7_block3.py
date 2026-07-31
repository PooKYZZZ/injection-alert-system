from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.e2e import pr7_block3_lifecycle_harness as harness


@pytest.mark.skipif(
    os.environ.get("PR7_RUN_BLOCK3_E2E") != "1",
    reason="set PR7_RUN_BLOCK3_E2E=1 to run the disposable Block 3 lifecycle",
)
def test_attack_to_critical_waf_block_lifecycle() -> None:
    harness.run_block3_lifecycle()


@pytest.mark.skipif(
    os.environ.get("PR7_RUN_BLOCK3_EXPIRY_E2E") != "1",
    reason="set PR7_RUN_BLOCK3_EXPIRY_E2E=1 to run expiry during backend outage",
)
def test_dynamic_rule_expires_while_backend_remains_unavailable() -> None:
    harness.run_block3_lifecycle()


def test_correlated_audit_rejects_tokens_split_across_transactions(monkeypatch):
    lines = [
        '{"transaction":{"id":"external","uri":"?evidence-123"}}',
        '{"transaction":{"id":"probe","tags":["pr7","revision-4",'
        '"recommendation-17"]}}',
    ]

    monkeypatch.setattr(harness, "_audit_tail", lambda *_: lines)

    with pytest.raises(AssertionError, match="no single ModSecurity transaction"):
        harness._require_correlated_pr7_audit(
            "project",
            Path("override.yml"),
            evidence_id="evidence-123",
            revision=4,
            recommendation_id=17,
            timeout_seconds=0,
        )


def test_cleanup_failure_is_reported(monkeypatch, tmp_path):
    def fail_run(*args, **kwargs):
        raise RuntimeError("down failed")

    monkeypatch.setattr(harness, "_run", fail_run)
    monkeypatch.setattr(
        harness.subprocess,
        "run",
        lambda *args, **kwargs: type("Result", (), {"stdout": "leftover"})(),
    )

    errors = harness._cleanup("project", tmp_path / "override.yml")

    assert any("disable failed" in error for error in errors)
    assert any("compose down failed" in error for error in errors)
    assert any("leftover containers" in error for error in errors)


def test_cleanup_reports_unsafe_final_state(monkeypatch, tmp_path):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[-1] == "status":
            return '{"disabled":false,"metadata":{"selected_kind":"authoritative"}}'
        return ""

    monkeypatch.setattr(harness, "_run", fake_run)
    monkeypatch.setattr(
        harness.subprocess,
        "run",
        lambda *args, **kwargs: type("Result", (), {"stdout": ""})(),
    )
    errors = harness._cleanup("project", tmp_path / "override.yml")
    assert any("unsafe final WAF state" in error for error in errors)
    assert any(command[-1] == "status" for command in calls)
