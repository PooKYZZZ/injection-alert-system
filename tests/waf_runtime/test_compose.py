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
