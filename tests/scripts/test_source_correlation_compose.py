from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[2]
BASE_TEST_OVERRIDE = "docker-compose.test.yml"
DEMO_TEST_OVERRIDE = "docker-compose.demo-target.test.yml"
SOURCE_TEST_OVERRIDE = "docker-compose.source-correlation-test.override.yml"
HOSTED_LAUNCHER = ROOT / "scripts" / "start_hosted_target.ps1"
TARGET_CLOUDFLARE_OVERLAY = "docker-compose.target-cloudflare.yml"
APP_CLOUDFLARE_OVERLAY = "docker-compose.app-cloudflare.yml"


def _run_hosted_launcher(env_file: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["COMPOSE_DISABLE_ENV_FILE"] = "1"
    return subprocess.run(
        [
            "pwsh",
            "-NoProfile",
            "-File",
            str(HOSTED_LAUNCHER),
            "-EnvFile",
            str(env_file),
            "-ValidateOnly",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def _compose_config(*files: str, profile: str | list[str] | None = None) -> dict:
    result = _compose_config_result(*files, profile=profile)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            result.args,
            output=result.stdout,
            stderr=result.stderr,
        )
    return json.loads(result.stdout)


def _compose_config_result(
    *files: str,
    profile: str | list[str] | None = None,
    hosted_peer: str | None = "172.30.20.2/32",
    token_file: str = "C:/Users/REDACTED/CyberTrace-Secrets/cloudflared-target.token",
) -> subprocess.CompletedProcess[str]:
    command = ["docker", "compose"]
    rendered_files = [*files, BASE_TEST_OVERRIDE]
    if "docker-compose.demo-target.yml" in files:
        rendered_files.append(DEMO_TEST_OVERRIDE)
    if "docker-compose.source-correlation-test.yml" in files:
        rendered_files.append(SOURCE_TEST_OVERRIDE)
    for file in rendered_files:
        command.extend(["-f", file])
    if profile is not None:
        profiles = [profile] if isinstance(profile, str) else profile
        for selected_profile in profiles:
            command.extend(["--profile", selected_profile])
    command.extend(["config", "--format", "json"])
    env = os.environ.copy()
    env.update(
        {
            "COMPOSE_DISABLE_ENV_FILE": "1",
            "WAF_INGEST_API_KEY": "compose-test-waf-key-not-a-runtime-secret",
            "WAF_AUDIT_EVIDENCE_KEY": "compose-test-audit-evidence-key",
            "SOURCE_TEST_API_SECRET_KEY": "compose-test-internal-key",
            "SOURCE_TEST_WAF_INGEST_API_KEY": "compose-test-waf-key",
            "CLOUDFLARED_TARGET_TOKEN_FILE": token_file,
        }
    )
    if hosted_peer is None:
        env.pop("HOSTED_WAF_TRUSTED_PEER", None)
    else:
        env["HOSTED_WAF_TRUSTED_PEER"] = hosted_peer
    env["WAF_SOURCE_VERIFICATION_MODE"] = "unverified"
    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def _base_config_without_profile() -> dict:
    return _compose_config("docker-compose.yml")


def test_default_compose_excludes_opt_in_technical_waf_pair() -> None:
    config = _base_config_without_profile()
    assert set(config["services"]) == {"backend", "frontend"}
    assert all("env_file" not in service for service in config["services"].values())
    assert config["services"]["backend"]["environment"]["ENFORCEMENT_MODE"] == "off"
    assert "ENFORCEMENT_CHECK_API_KEY" in config["services"]["backend"]["environment"]
    assert "ENFORCEMENT_CHECK_URL" not in config["services"]["frontend"]["environment"]
    assert (
        "ENFORCEMENT_CHECK_API_KEY"
        not in config["services"]["frontend"]["environment"]
    )


def test_demo_portal_receives_internal_shadow_check_wiring() -> None:
    config = _compose_config(
        "docker-compose.yml", "docker-compose.demo-target.yml", profile="demo-target"
    )
    portal = config["services"]["demo-portal"]
    assert portal["environment"]["ENFORCEMENT_CHECK_URL"] == (
        "http://backend:8000/api/internal/enforcement/check"
    )
    assert portal["environment"]["ENFORCEMENT_MODE"] == "off"
    assert portal["environment"]["DATABASE_URL"] == "file:./dev.db"
    assert "ENFORCEMENT_CHECK_API_KEY" in portal["environment"]
    assert "ENFORCEMENT_CHECK_TIMEOUT_MS" in portal["environment"]
    assert "ports" not in portal
    assert "injection-alert-system-portal-pre-waf" in portal["build"]["context"]
    assert any(
        "injection-alert-system-portal-pre-waf" in mount["source"]
        and mount["target"] == "/app/prisma"
        for mount in portal["volumes"]
    )


def test_local_collection_overlay_captures_benign_events_without_changing_default():
    default_config = _compose_config(
        "docker-compose.yml", "docker-compose.demo-target.yml", profile="demo-target"
    )
    collection_config = _compose_config(
        "docker-compose.yml",
        "docker-compose.demo-target.yml",
        "docker-compose.demo-target.collection.yml",
        profile="demo-target",
    )

    assert (
        default_config["services"]["demo-target-modsecurity"]["environment"][
            "MODSEC_AUDIT_ENGINE"
        ]
        == "RelevantOnly"
    )
    assert (
        collection_config["services"]["demo-target-modsecurity"]["environment"][
            "MODSEC_AUDIT_ENGINE"
        ]
        == "On"
    )
    bridge = collection_config["services"]["demo-target-bridge"]
    assert bridge["environment"]["WAF_INGEST_TIMEOUT_SECONDS"] == "30"
    assert bridge["environment"]["WAF_INGEST_MAX_RETRIES"] == "20"
    assert bridge["environment"]["WAF_INGEST_RETRY_DELAY_SECONDS"] == "2"
    assert "--timeout \"$$WAF_INGEST_TIMEOUT_SECONDS\"" in bridge["command"][2]


def test_technical_profile_contains_the_existing_8088_pair() -> None:
    config = _compose_config("docker-compose.yml", profile="technical-waf")

    assert set(config["services"]) == {"backend", "frontend", "modsecurity", "bridge"}
    assert config["services"]["modsecurity"]["ports"] == [
        {
            "mode": "ingress",
            "target": 8080,
            "published": "8088",
            "protocol": "tcp",
        }
    ]
    assert "B" not in config["services"]["modsecurity"]["environment"][
        "MODSEC_AUDIT_LOG_PARTS"
    ]
    assert sum(
        port.get("published") == "8088"
        for service in config["services"].values()
        for port in service.get("ports", [])
    ) == 1


def test_hosted_demo_profile_excludes_technical_pair_and_is_loopback_only() -> None:
    config = _compose_config(
        "docker-compose.yml",
        "docker-compose.demo-target.yml",
        "docker-compose.hosted-target.yml",
        profile="demo-target",
    )

    assert set(config["services"]) == {
        "backend",
        "frontend",
        "demo-portal",
        "demo-target-modsecurity",
        "demo-target-bridge",
    }
    ports = config["services"]["demo-target-modsecurity"]["ports"]
    assert ports == [
        {
            "mode": "ingress",
            "host_ip": "127.0.0.1",
            "target": 8080,
            "published": "8089",
            "protocol": "tcp",
        }
    ]
    rendered = json.dumps(config)
    assert '"published": "8088"' not in rendered
    assert "B" not in config["services"]["demo-target-modsecurity"]["environment"][
        "MODSEC_AUDIT_LOG_PARTS"
    ]
    assert config["services"]["demo-target-modsecurity"]["environment"][
        "REAL_IP_RECURSIVE"
    ] == "off"
    assert config["services"]["demo-target-modsecurity"]["environment"][
        "REAL_IP_HEADER"
    ] == "CF-Connecting-IP"
    assert config["services"]["demo-target-modsecurity"]["environment"][
        "SET_REAL_IP_FROM"
    ] == "172.30.20.2/32"
    assert config["services"]["backend"]["environment"][
        "WAF_SOURCE_VERIFICATION_MODE"
    ] == "unverified"


def test_hosted_compose_fails_clearly_without_trusted_peer() -> None:
    result = _compose_config_result(
        "docker-compose.yml",
        "docker-compose.demo-target.yml",
        "docker-compose.hosted-target.yml",
        profile="demo-target",
        hosted_peer=None,
    )

    assert result.returncode != 0
    assert "HOSTED_WAF_TRUSTED_PEER" in result.stderr


def test_hosted_launcher_loads_persistent_env_and_validates_it(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.hosted"
    env_file.write_text(
        "HOSTED_WAF_TRUSTED_PEER=172.30.20.2/32\n"
        "WAF_SOURCE_VERIFICATION_MODE=unverified\n",
        encoding="utf-8",
    )

    result = _run_hosted_launcher(env_file)

    assert result.returncode == 0, result.stderr or result.stdout


def test_hosted_launcher_rejects_missing_trusted_peer(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.hosted"
    env_file.write_text(
        "WAF_SOURCE_VERIFICATION_MODE=unverified\n",
        encoding="utf-8",
    )

    result = _run_hosted_launcher(env_file)

    assert result.returncode != 0
    assert "HOSTED_WAF_TRUSTED_PEER" in result.stderr


def test_hosted_launcher_rejects_broad_or_verified_configuration(
    tmp_path: Path,
) -> None:
    broad_peer = tmp_path / ".env.broad"
    broad_peer.write_text(
        "HOSTED_WAF_TRUSTED_PEER=0.0.0.0/0\n"
        "WAF_SOURCE_VERIFICATION_MODE=unverified\n",
        encoding="utf-8",
    )
    verified_mode = tmp_path / ".env.verified"
    verified_mode.write_text(
        "HOSTED_WAF_TRUSTED_PEER=172.30.20.2/32\n"
        "WAF_SOURCE_VERIFICATION_MODE=cloudflare_tunnel\n",
        encoding="utf-8",
    )

    broad_result = _run_hosted_launcher(broad_peer)
    verified_result = _run_hosted_launcher(verified_mode)

    assert broad_result.returncode != 0
    assert "narrow" in broad_result.stderr.lower()
    assert verified_result.returncode != 0
    assert "unverified" in verified_result.stderr.lower()


def test_target_cloudflare_overlay_isolated_and_secret_safe(tmp_path: Path) -> None:
    token_path = tmp_path / "cloudflared-target.token"
    token_path.write_text("token-must-not-render\n", encoding="utf-8")
    result = _compose_config_result(
        "docker-compose.yml",
        "docker-compose.demo-target.yml",
        TARGET_CLOUDFLARE_OVERLAY,
        profile=["demo-target", "target-cloudflare"],
        token_file=str(token_path),
    )

    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    rendered = json.dumps(config)
    assert "token-must-not-render" not in rendered
    assert "--token-file" in " ".join(
        config["services"]["cloudflared"]["command"]
    )
    assert "ports" not in config["services"]["demo-target-modsecurity"]
    assert config["services"]["cloudflared"]["networks"]["target_waf_ingress"][
        "ipv4_address"
    ] == "172.30.20.2"
    assert config["networks"]["target_waf_ingress"]["internal"] is True
    shared = {
        name
        for name, service in config["services"].items()
        if "target_waf_ingress" in service.get("networks", {})
    }
    assert shared == {
        "cloudflared",
        "demo-target-modsecurity",
    }
    egress_users = {
        name
        for name, service in config["services"].items()
        if "target_cloudflare_egress" in service.get("networks", {})
    }
    assert egress_users == {"cloudflared"}
    assert config["services"]["demo-target-modsecurity"]["networks"][
        "target_waf_ingress"
    ]["ipv4_address"] == "172.30.20.3"
    assert set(config["services"]["demo-target-modsecurity"]["networks"]) == {
        "target_application",
        "target_waf_ingress",
    }
    assert set(config["services"]["demo-portal"]["networks"]) == {
        "target_application",
    }
    assert config["services"]["demo-target-modsecurity"]["environment"][
        "SET_REAL_IP_FROM"
    ] == "172.30.20.2/32"


def test_app_cloudflare_overlay_adds_least_privilege_frontend_network(
    tmp_path: Path,
) -> None:
    token_path = tmp_path / "cloudflared-target.token"
    token_path.write_text("token-must-not-render\n", encoding="utf-8")
    result = _compose_config_result(
        "docker-compose.yml",
        "docker-compose.demo-target.yml",
        TARGET_CLOUDFLARE_OVERLAY,
        APP_CLOUDFLARE_OVERLAY,
        profile=["demo-target", "target-cloudflare"],
        token_file=str(token_path),
    )

    assert result.returncode == 0, result.stderr
    config = json.loads(result.stdout)
    rendered = json.dumps(config)
    assert "token-must-not-render" not in rendered
    assert config["networks"]["app_cloudflare_ingress"]["internal"] is True
    assert set(config["services"]["frontend"]["networks"]) == {
        "default",
        "app_cloudflare_ingress",
    }
    assert set(config["services"]["cloudflared"]["networks"]) == {
        "target_cloudflare_egress",
        "target_waf_ingress",
        "app_cloudflare_ingress",
    }
    assert "app_cloudflare_ingress" not in config["services"]["backend"][
        "networks"
    ]
    assert "app_cloudflare_ingress" not in config["services"][
        "demo-target-modsecurity"
    ]["networks"]
    assert config["services"]["backend"]["environment"][
        "WAF_SOURCE_VERIFICATION_MODE"
    ] == "unverified"
    assert config["services"]["backend"]["environment"][
        "CLOUDFLARE_TARGET_ISOLATION_ENABLED"
    ] == "true"
    assert config["services"]["backend"]["environment"][
        "CLOUDFLARE_TARGET_VERIFIED_PROOF"
    ] == "false"
    assert config["services"]["demo-target-bridge"]["environment"][
        "WAF_SOURCE_PROVENANCE_MODE"
    ] == "direct_remote_addr"
    healthcheck = config["services"]["cloudflared"]["healthcheck"]
    assert healthcheck["test"] == [
        "CMD",
        "cloudflared",
        "tunnel",
        "--metrics",
        "127.0.0.1:20241",
        "ready",
    ]
    assert "CMD-SHELL" not in healthcheck["test"]
    assert config["services"]["demo-target-modsecurity"]["environment"][
        "SET_REAL_IP_FROM"
    ] == "172.30.20.2/32"


def test_target_cloudflare_overlay_rejects_broad_real_ip_trust() -> None:
    template = (
        ROOT / "config" / "modsecurity" / "target-cloudflare-realip.conf.template"
    ).read_text(encoding="utf-8")
    assert "172.30.20.2/32" in template
    assert "0.0.0.0/0" not in template
    assert "10.0.0.0/8" not in template
    assert "172.16.0.0/12" not in template
    assert "192.168.0.0/16" not in template


def test_controlled_topology_has_narrow_trust_and_no_host_browser_path() -> None:
    config = _compose_config(
        "docker-compose.yml",
        "docker-compose.source-correlation-test.yml",
        profile="source-correlation-test",
    )

    assert set(config["services"]) == {
        "backend",
        "source-test-trusted-proxy",
        "source-test-untrusted-client",
        "source-test-client-a",
        "source-test-client-b",
        "source-test-modsecurity",
        "source-test-bridge",
    }
    waf = config["services"]["source-test-modsecurity"]
    assert set(waf["networks"]) == {
        "source_test_trusted",
        "source_test_untrusted",
        "source_test_backend",
    }
    assert waf["environment"]["SET_REAL_IP_FROM"] == "172.30.10.2/32"
    assert waf["environment"]["REAL_IP_HEADER"] == "CF-Connecting-IP"
    assert waf["environment"]["REAL_IP_RECURSIVE"] == "off"
    assert "B" not in waf["environment"]["MODSEC_AUDIT_LOG_PARTS"]
    rendered_waf = json.dumps(waf)
    assert "source-correlation-proxy-backend.conf.template" in rendered_waf
    assert "source-correlation-realip.conf.template" in rendered_waf
    assert "0.0.0.0/0" not in json.dumps(config)
    assert config["services"]["backend"]["environment"][
        "WAF_SOURCE_VERIFICATION_MODE"
    ] == "unverified"
    assert config["services"]["backend"]["environment"]["DATABASE_URL"] == (
        "sqlite+aiosqlite:////tmp/source-correlation-test.db"
    )
    assert "alembic" not in " ".join(config["services"]["backend"]["command"])
    assert not any(
        service.get("ports") for service in config["services"].values()
    )
    assert all("env_file" not in service for service in config["services"].values())
