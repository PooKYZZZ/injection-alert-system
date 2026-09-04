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


def test_ci_uses_node24_action_runtime_releases() -> None:
    source = "\n".join(
        workflow.read_text(encoding="utf-8")
        for workflow in WORKFLOWS
    )

    assert (
        "actions/setup-python@5fda3b95a4ea91299a34e894583c3862153e4b97"
        " # v7.0.0"
    ) in source
    assert (
        "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020"
        " # v7.0.0"
    ) in source


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


def test_frontend_pr_dependency_review_avoids_registry_audit_outage_failures() -> None:
    source = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    frontend_job = source.split("  frontend:", 1)[1].split(
        "  frontend-dependency-review:", 1
    )[0]
    review_job = source.split("  frontend-dependency-review:", 1)[1].split(
        "  auth-e2e:", 1
    )[0]

    assert "npm audit" not in frontend_job
    assert "if: github.event_name == 'pull_request'" in review_job
    assert (
        "actions/dependency-review-action@a1d282b36b6f3519aa1f3fc636f609c47dddb294"
        in review_job
    )
    assert "fail-on-severity: high" in review_job
    assert "fail-on-scopes: runtime, development" in review_job
    assert "license-check: false" in review_job
    assert "vulnerability-check: true" in review_job
    assert "warn-only: true" not in review_job
