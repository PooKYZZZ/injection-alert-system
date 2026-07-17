from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).parents[2]
BASE_TEST_OVERRIDE = "docker-compose.test.yml"
DEMO_TEST_OVERRIDE = "docker-compose.demo-target.test.yml"
SOURCE_TEST_OVERRIDE = "docker-compose.source-correlation-test.override.yml"


def _compose_config(*files: str, profile: str | None = None) -> dict:
    command = ["docker", "compose"]
    rendered_files = [*files, BASE_TEST_OVERRIDE]
    if "docker-compose.demo-target.yml" in files:
        rendered_files.append(DEMO_TEST_OVERRIDE)
    if "docker-compose.source-correlation-test.yml" in files:
        rendered_files.append(SOURCE_TEST_OVERRIDE)
    for file in rendered_files:
        command.extend(["-f", file])
    if profile is not None:
        command.extend(["--profile", profile])
    command.extend(["config", "--format", "json"])
    env = os.environ.copy()
    env.update(
        {
            "COMPOSE_DISABLE_ENV_FILE": "1",
            "HOSTED_WAF_TRUSTED_PEER": "172.30.20.2/32",
            "WAF_INGEST_API_KEY": "compose-test-waf-key-not-a-runtime-secret",
            "SOURCE_TEST_API_SECRET_KEY": "compose-test-internal-key",
            "SOURCE_TEST_WAF_INGEST_API_KEY": "compose-test-waf-key",
        }
    )
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def _base_config_without_profile() -> dict:
    return _compose_config("docker-compose.yml")


def test_default_compose_excludes_opt_in_technical_waf_pair() -> None:
    config = _base_config_without_profile()
    assert set(config["services"]) == {"backend", "frontend"}
    assert all("env_file" not in service for service in config["services"].values())


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
