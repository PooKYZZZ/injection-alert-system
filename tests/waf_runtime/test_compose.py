from pathlib import Path
import json
import os
import shutil
import subprocess

import pytest


ROOT = Path(__file__).parents[2]


def test_backend_runtime_code_is_not_excluded_from_the_image():
    dockerignore = {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text().splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert "ml_model/retraining/" not in dockerignore
    assert "ml_model/results/" in dockerignore


def test_backend_compose_exposes_the_opt_in_training_dependency_build_arg():
    compose = (ROOT / "docker-compose.yml").read_text()

    assert "INSTALL_TRAINING_REQUIREMENTS: ${INSTALL_TRAINING_REQUIREMENTS:-false}" in compose


def test_backend_compose_guards_migrations_before_startup():
    compose = (ROOT / "docker-compose.yml").read_text()

    assert "python -m scripts.safe_local_migrate" in compose
    assert "alembic upgrade head && uvicorn" not in compose


def test_hosted_compose_starts_without_local_migration_guard():
    config = _merged_compose(
        "docker-compose.yml",
        "docker-compose.demo-target.yml",
        "docker-compose.hosted-target.yml",
    )

    command = config["services"]["backend"]["command"]
    assert command == [
        "sh",
        "-c",
        "uvicorn --factory web_app.presentation.app:create_app --host 0.0.0.0 --port 8000",
    ]
    assert "safe_local_migrate" not in " ".join(command)


def test_cloudflare_target_compose_starts_without_local_migration_guard():
    config = _merged_compose(
        "docker-compose.yml",
        "docker-compose.demo-target.yml",
        "docker-compose.target-cloudflare.yml",
    )

    command = config["services"]["backend"]["command"]
    assert command == [
        "sh",
        "-c",
        "uvicorn --factory web_app.presentation.app:create_app --host 0.0.0.0 --port 8000",
    ]
    assert "safe_local_migrate" not in " ".join(command)


def test_cloudflare_target_compose_mounts_approved_datasets_read_only():
    config = _merged_compose(
        "docker-compose.yml",
        "docker-compose.demo-target.yml",
        "docker-compose.target-cloudflare.yml",
    )

    mounts = config["services"]["backend"]["volumes"]
    expected_datasets = (
        "v3_907k_cleaned",
        "v3_907k_cleaned_model_input_v2",
    )
    for dataset in expected_datasets:
        expected_source = str((ROOT / "data" / "processed" / dataset).resolve())
        assert any(
            mount.get("type") == "bind"
            and mount.get("source") == expected_source
            and mount.get("target") == f"/app/data/processed/{dataset}"
            and mount.get("read_only") is True
            for mount in mounts
        )


def test_local_compose_uses_an_explicit_postgres_database():
    config = _merged_compose("docker-compose.yml", "docker-compose.local.yml")

    services = config["services"]
    assert "postgres" in services
    assert services["backend"]["environment"]["DATABASE_URL"] == (
        "postgresql+asyncpg://cybertrace:review-local-postgres-password@postgres:5432/"
        "cybertrace"
    )
    assert services["backend"]["depends_on"]["postgres"]["condition"] == (
        "service_healthy"
    )
    assert services["postgres"].get("ports", []) == []


def test_full_local_stack_launcher_uses_the_local_database_overlay():
    script = (ROOT / "scripts" / "rebuild_full_local_stack.ps1").read_text()

    assert '"-f", "docker-compose.local.yml"' in script


def test_application_services_wait_for_backend_readiness():
    config = _merged_compose("docker-compose.yml")

    services = config["services"]
    assert services["frontend"]["depends_on"]["backend"]["condition"] == (
        "service_healthy"
    )
    assert services["pr7-waf"]["depends_on"]["backend"]["condition"] == (
        "service_healthy"
    )


def test_frontend_has_a_runtime_readiness_check():
    config = _merged_compose("docker-compose.yml")

    healthcheck = config["services"]["frontend"]["healthcheck"]
    assert healthcheck["test"][0] == "CMD"
    assert "http://127.0.0.1:3000/login" in " ".join(healthcheck["test"])


def test_frontend_image_uses_standalone_non_root_runtime():
    next_config = (ROOT / "frontend" / "next.config.ts").read_text(encoding="utf-8")
    dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")

    assert "output: 'standalone'" in next_config
    assert dockerfile.count("FROM node:24-alpine") >= 3
    assert (
        "COPY --from=builder --chown=node:node /app/.next/standalone ./" in dockerfile
    )
    assert "USER node" in dockerfile
    assert 'CMD ["node", "server.js"]' in dockerfile


def test_backend_image_runs_non_root_with_owned_runtime_directories():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "useradd --no-log-init" in dockerfile
    assert "runtime" in dockerfile
    assert "ml_model/results/dashboard_retraining" in dockerfile
    assert "ml_model/model_registry/staging" in dockerfile
    assert "ml_model/model_registry/archive" in dockerfile
    assert "USER cybertrace" in dockerfile
    assert "DATABASE_URL=sqlite+aiosqlite:///./runtime/injection_alerts.db" in env_example


def test_default_sqlite_runtime_directory_exists_in_a_clean_checkout():
    runtime_dir = ROOT / "runtime"

    assert runtime_dir.is_dir()
    assert (runtime_dir / ".gitkeep").is_file()


def _merged_compose(*files: str) -> dict:
    if shutil.which("docker") is None:
        pytest.skip("Docker is required for merged Compose contract tests")
    environment = os.environ.copy()
    environment.update(
        {
            "PR7_BLOCK3B_POSTGRES_PASSWORD": "reviewdbpassword",
            "LOCAL_POSTGRES_PASSWORD": "review-local-postgres-password",
            "WAF_INGEST_API_KEY": "review-ingest",
            "WAF_AUDIT_EVIDENCE_KEY": "review-audit",
            "WAF_STATE_SYNC_API_KEY": "review-sync",
            "ENFORCEMENT_CHECK_API_KEY": "review-enforcement",
            "ENFORCEMENT_TURNSTILE_SITE_KEY": "1x00000000000000000000AA",
            "ENFORCEMENT_TURNSTILE_SECRET_KEY": "1x0000000000000000000000000000000AA",
            "ENFORCEMENT_TURNSTILE_EXPECTED_HOSTNAME": "localhost",
            "CLOUDFLARE_TARGET_VERIFIED_PROOF": "true",
            "APP_ENV": "staging",
            "HOSTED_WAF_TRUSTED_PEER": "172.30.20.2/32",
            "CLOUDFLARED_TARGET_TOKEN_FILE": str(
                ROOT / "docs/project-ops/PR7_Sections_3B_3C_Implementation_Design.md"
            ),
        }
    )
    command = ["docker", "compose"]
    for compose_file in files:
        command.extend(["-f", str(ROOT / compose_file)])
    command.extend(
        [
            "--profile",
            "demo-target",
            "--profile",
            "target-cloudflare",
            "--profile",
            "pr7-block3",
            "--profile",
            "pr7-local-waf",
            "config",
            "--format",
            "json",
        ]
    )
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise AssertionError(
            "docker compose config failed\n"
            f"command: {command!r}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    return json.loads(result.stdout)


def test_pr7_audit_uses_a_named_volume_for_container_writability():
    compose = (Path(__file__).parents[2] / "docker-compose.yml").read_text()
    assert "- pr7-audit:/var/log/modsecurity" in compose
    assert "pr7-audit:" in compose
    assert "./logs/modsecurity/pr7:/var/log/modsecurity" not in compose


def test_block3_evidence_logging_is_opt_in_and_path_only():
    root = Path(__file__).parents[2]
    dockerfile = (root / "Dockerfile.pr7-waf").read_text()
    compose = (root / "docker-compose.pr7-block3.yml").read_text()
    template = (root / "config/modsecurity/pr7-evidence-log.conf.template").read_text()

    assert "pr7-evidence-log.conf.template" not in dockerfile
    evidence_mount = (
        "./config/modsecurity/pr7-evidence-log.conf.template:"
        "/etc/nginx/templates/conf.d/pr7-evidence-log.conf.template:ro"
    )
    assert evidence_mount in compose
    assert '"uri":"$uri"' in template
    assert "$request_uri" not in template
    assert "if=$pr7_evidence_loggable" in template


def test_block3_bridge_replays_existing_audit_lines_after_restart():
    compose = (Path(__file__).parents[2] / "docker-compose.pr7-block3.yml").read_text()
    assert "--follow --from-start" in compose


def test_block3b_preserves_exact_cloudflared_peer_and_hides_origins():
    root = Path(__file__).parents[2]
    compose = (root / "docker-compose.pr7-block3b.yml").read_text()

    assert "SET_REAL_IP_FROM: 172.30.20.2/32" in compose
    assert "ports: !override []" in compose
    assert "PR7_PORTAL_SENTINEL_PATH: /pr7-evidence/portal.jsonl" in compose
    assert "ENFORCEMENT_CHECK_API_KEY:" in compose
    assert "ENFORCEMENT_TURNSTILE_SITE_KEY:" in compose
    assert "ENFORCEMENT_SOURCE_TRUST_MODE: cloudflare_verified" in compose
    assert "WAF_SOURCE_VERIFICATION_MODE: cloudflare_tunnel" in compose
    assert "CLOUDFLARE_TARGET_VERIFIED_PROOF:" in compose
    assert compose.count("ENFORCEMENT_MODE: enforce") == 2
    assert "target_waf_ingress" in compose
    assert "target_application" in compose
    assert "cloudflared_target_token" not in compose


def test_block3c_is_local_and_preserves_persistent_runtime_state():
    root = Path(__file__).parents[2]
    compose = (root / "docker-compose.pr7-block3c.yml").read_text()

    assert "cloudflared" not in compose
    assert "pr7-block3c-state:/pr7-state" in compose
    assert '127.0.0.1::8080' in compose
    assert "PR7_PORTAL_SENTINEL_PATH: /pr7-evidence/portal.jsonl" in compose
    assert "ENFORCEMENT_CHECK_API_KEY:" in compose
    assert "ENFORCEMENT_TURNSTILE_SITE_KEY: 1x00000000000000000000AA" in compose
    assert "ENFORCEMENT_ALLOW_UNVERIFIED_SOURCE_FOR_TESTS: \"true\"" in compose


def test_block3b_merged_model_has_active_enforcement_and_no_origin_ports():
    config = _merged_compose(
        "docker-compose.yml",
        "docker-compose.test.yml",
        "docker-compose.demo-target.yml",
        "docker-compose.target-cloudflare.yml",
        "docker-compose.pr7-block3b.yml",
    )
    services = config["services"]
    assert services["demo-portal"]["environment"]["ENFORCEMENT_MODE"] == "enforce"
    assert services["backend"]["environment"]["ENFORCEMENT_MODE"] == "enforce"
    assert services["backend"]["environment"]["WAF_SOURCE_VERIFICATION_MODE"] == "cloudflare_tunnel"
    assert services["demo-target-modsecurity"]["environment"]["SET_REAL_IP_FROM"] == "172.30.20.2/32"
    assert services["demo-portal"].get("ports", []) == []
    assert services["demo-target-modsecurity"].get("ports", []) == []
    assert "target_waf_ingress" in services["cloudflared"]["networks"]
    assert "target_waf_ingress" in services["demo-target-modsecurity"]["networks"]


def test_block3c_merged_model_is_local_and_explicitly_test_only():
    config = _merged_compose(
        "docker-compose.yml",
        "docker-compose.test.yml",
        "docker-compose.pr7-block3.yml",
        "docker-compose.pr7-block3c.yml",
    )
    services = config["services"]
    assert "cloudflared" not in services
    assert services["demo-portal"]["environment"]["ENFORCEMENT_MODE"] == "enforce"
    assert services["demo-portal"]["environment"]["ENFORCEMENT_ALLOW_UNVERIFIED_SOURCE_FOR_TESTS"] == "true"
    assert services["backend"]["environment"]["NOTIFICATION_WORKER_ENABLED"] == "false"
    assert any(
        mount["source"] == "pr7-block3c-state" and mount["target"] == "/pr7-state"
        for mount in services["pr7-block3-waf"]["volumes"]
    )


def test_demo_target_modsecurity_disables_the_image_healthcheck():
    config = _merged_compose(
        "docker-compose.yml",
        "docker-compose.demo-target.yml",
    )

    assert config["services"]["demo-target-modsecurity"]["healthcheck"] == {
        "disable": True
    }
