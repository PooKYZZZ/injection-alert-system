import re
from pathlib import Path

WORKFLOWS = tuple(Path(".github/workflows").glob("*.yml"))
FULL_SHA_ACTION = re.compile(r"uses:\s+[^\s@]+@[0-9a-f]{40}(?:\s+#.+)?$")


def test_all_external_actions_are_pinned_to_full_commit_shas() -> None:
    action_lines = [
        line.strip()
        for workflow in WORKFLOWS
        for line in workflow.read_text(encoding="utf-8").splitlines()
        if "uses:" in line
    ]

    assert action_lines
    assert all(FULL_SHA_ACTION.search(line) for line in action_lines)


def test_ci_jobs_have_bounded_timeouts() -> None:
    source = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    for job_name in (
        "backend",
        "postgres",
        "frontend",
        "auth-e2e",
        "secret-scan",
        "pr7-waf-runtime",
        "container-smoke",
    ):
        match = re.search(
            rf"(?ms)^  {re.escape(job_name)}:.*?(?=^  [a-z][\w-]*:|\Z)",
            source,
        )
        assert match is not None
        assert "timeout-minutes:" in match.group()


def test_ci_validates_and_smokes_the_local_compose_stack() -> None:
    source = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    job = source.split("  container-smoke:", 1)[1]

    assert "docker compose config --quiet" in job
    assert "docker-compose.local.yml" in job
    assert "up -d --build --wait" in job
    assert "docker compose" in job and "exec -T backend" in job
    assert "exec -T frontend" in job
    assert "down --volumes" in job


def test_pr7_off_mode_waits_for_nginx_readiness_before_probing() -> None:
    source = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    job = source.split("  pr7-waf-runtime:", 1)[1].split(
        "  container-smoke:", 1
    )[0]

    assert "PR7_WAF_MODE=off" in job
    assert "http://127.0.0.1:8081/__pr7/ready" in job
    assert "status_code == 204" in job


def test_ci_lints_only_the_remediated_backend_boundaries() -> None:
    source = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    backend_job = source.split("  backend:", 1)[1].split("  postgres:", 1)[0]

    assert "Lint the remediated backend boundaries" in backend_job
    assert "web_app/application/retraining_control_use_case.py" in backend_job
    assert "ruff check ." not in backend_job
