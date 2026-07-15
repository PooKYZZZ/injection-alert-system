from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).parents[2]


def _compose_config(*files: str, profile: str) -> dict:
    command = ["docker", "compose"]
    for file in files:
        command.extend(["-f", file])
    command.extend(["--profile", profile, "config", "--format", "json"])
    env = os.environ.copy()
    env.update(
        {
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
    result = subprocess.run(
        ["docker", "compose", "-f", "docker-compose.yml", "config", "--format", "json"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_default_compose_excludes_opt_in_technical_waf_pair() -> None:
    config = _base_config_without_profile()
    assert set(config["services"]) == {"backend", "frontend"}


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
    assert "0.0.0.0/0" not in json.dumps(config)
    assert config["services"]["backend"]["environment"][
        "WAF_SOURCE_VERIFICATION_MODE"
    ] == "controlled_private_network"
    assert config["services"]["backend"]["environment"]["DATABASE_URL"] == (
        "sqlite+aiosqlite:////tmp/source-correlation-test.db"
    )
    assert "alembic" not in " ".join(config["services"]["backend"]["command"])
    assert not any(
        service.get("ports") for service in config["services"].values()
    )
