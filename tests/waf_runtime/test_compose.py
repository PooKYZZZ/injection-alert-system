from pathlib import Path


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
