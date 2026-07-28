from __future__ import annotations

from waf_runtime.logging import JsonEventLogger


def test_logger_redacts_secrets_and_payloads(capsys):
    logger = JsonEventLogger("canary-token")
    logger.emit(
        "waf_snapshot_rejected",
        reason="bad",
        authorization="Bearer canary-token",
        body="attack payload",
    )
    output = capsys.readouterr().out
    assert "canary-token" not in output
    assert "attack payload" not in output
    assert "waf_snapshot_rejected" in output
