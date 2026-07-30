from pathlib import Path


def test_pr7_audit_uses_a_named_volume_for_container_writability():
    compose = (Path(__file__).parents[2] / "docker-compose.yml").read_text()
    assert "- pr7-audit:/var/log/modsecurity" in compose
    assert "pr7-audit:" in compose
    assert "./logs/modsecurity/pr7:/var/log/modsecurity" not in compose
