from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import (
    pr7_block3_evidence as evidence,
)
from scripts import (
    pr7_block3_preflight as preflight,
)
from scripts import (
    pr7_block3_stack as stack,
)
from scripts import (
    pr7_block3b_coordinator as coordinator,
)
from scripts import (
    pr7_block3b_source_agent as source_agent,
)
from scripts import (
    pr7_block3c_runner as runner,
)


def test_evidence_rejects_sensitive_fields_and_bounds_output(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        evidence.assert_safe_fields({"authorization": "redacted"})
    path = tmp_path / "evidence.json"
    evidence.write_json(path, {"evidence_id": "run-1", "status_code": 200})
    assert json.loads(path.read_text(encoding="utf-8"))["status_code"] == 200


def test_preflight_reports_missing_compose_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(preflight, "ROOT", Path("Z:/does-not-exist"))
    monkeypatch.setattr(preflight.shutil, "which", lambda _: None)
    result = preflight.run_preflight("3c", "run-1")
    assert result["overall"] == "FAIL"
    assert any(check["name"] == "compose_files" for check in result["checks"])


def test_source_agent_requires_explicit_live_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PR7_RUN_BLOCK3_LIVE", raising=False)
    with pytest.raises(RuntimeError, match="PR7_RUN_BLOCK3_LIVE"):
        source_agent.run_source_agent("https://example.test", "run-1", "home")


def test_source_agent_records_only_safe_response_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PR7_RUN_BLOCK3_LIVE", "1")

    class Response:
        status_code = 200
        headers = {"server": "cloudflare", "cf-ray": "ray"}
        content = b"private response body"

    class Client:
        def __init__(self, **_: object) -> None:
            pass

        def __enter__(self) -> "Client":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def get(self, *_: object, **__: object) -> Response:
            return Response()

    monkeypatch.setattr(source_agent.httpx, "Client", Client)
    result = source_agent.run_source_agent(
        "https://example.test/search",
        "run-1",
        "home",
    )
    assert len(result["results"]) == 6
    assert all("content" not in item["result"] for item in result["results"])


def _bundle(run_id: str, label: str) -> dict:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "source_label": label,
        "results": [
            {"scenario": "normal", "result": {"status_code": 200}},
            {"scenario": "static_crs", "result": {"status_code": 403}},
            {"scenario": "forged_headers", "result": {"status_code": 403}},
        ],
    }


def test_coordinator_requires_distinct_sources_and_passes_matrix(
    tmp_path: Path,
) -> None:
    first = tmp_path / "home.json"
    second = tmp_path / "mobile.json"
    evidence.write_json(first, _bundle("run-1", "home"))
    evidence.write_json(second, _bundle("run-1", "mobile"))
    result = coordinator.coordinate("run-1", [first, second])
    assert result["overall"] == "PASS"
    with pytest.raises(ValueError, match="distinct"):
        coordinator.coordinate("run-1", [first, first])


def test_stack_command_is_bounded_and_uses_unique_project_name() -> None:
    command = stack.compose_command("3c", "run-1", "start")
    assert command[:4] == ["docker", "compose", "--project-name", "pr7-run-1"]
    assert "--wait" in command
    with pytest.raises(ValueError):
        stack.compose_command("3c", "bad/run", "start")


def test_runner_captures_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    class Completed:
        returncode = 0
        stdout = "1 passed"
        stderr = ""

    monkeypatch.setattr(runner.subprocess, "run", lambda *args, **kwargs: Completed())
    result = runner.run_3c("run-1")
    assert result["status"] == "PASS"
    assert result["return_code"] == 0
