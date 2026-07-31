from __future__ import annotations

import json

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


def test_total_reconcile_duration_is_preserved_in_safe_event_fields(capsys) -> None:
    JsonEventLogger().emit("waf_candidate_selected", mode="enforce", total_ms=12.345)

    payload = json.loads(capsys.readouterr().out)
    assert payload["event"] == "waf_candidate_selected"
    assert payload["total_ms"] == 12.345
