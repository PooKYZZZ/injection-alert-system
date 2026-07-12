from pathlib import Path


WORKFLOW = Path(".github/workflows/ci.yml")


def test_ci_requires_the_managed_chromium_authentication_project() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")

    assert "  auth-e2e:" in source
    assert "node-version: '24'" in source
    assert "python-version: '3.14'" in source
    assert "npx playwright install --with-deps chromium" in source
    assert "npm run test:e2e:auth" in source
    assert "continue-on-error" not in source


def test_ci_retains_safe_failure_evidence_and_always_cleans_resources() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    job = source.split("  auth-e2e:", 1)[1].split("  secret-scan:", 1)[0]

    assert "actions/upload-artifact@v4" in job
    assert "if: failure()" in job
    assert "frontend/playwright-report/auth" in job
    assert "frontend/test-results/auth" in job
    assert "if: always()" in job
    assert "cybertrace.auth-e2e=true" in job
    assert "secrets." not in job


def test_postgres_ci_provisions_the_supabase_runtime_role_before_migrations() -> None:
    source = WORKFLOW.read_text(encoding="utf-8")
    job = source.split("  postgres:", 1)[1].split("  frontend:", 1)[0]

    role_setup = "python scripts/prepare_ci_postgres_roles.py"
    assert role_setup in job
    assert job.index(role_setup) < job.index("python -m alembic upgrade head")
