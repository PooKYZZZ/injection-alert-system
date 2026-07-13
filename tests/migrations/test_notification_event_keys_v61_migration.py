from __future__ import annotations

from pathlib import Path


MIGRATION = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260711_000018_notification_event_keys_v61.py"
)


def test_account_status_notifications_use_event_uuid_keys() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "20260711_000018"' in source
    assert 'down_revision = "20260711_000017"' in source
    assert "RETURNING id INTO v_event" in source
    assert "v_event_name || '/' || v_event::text" in source
    assert "event_id, kind, channel" in source
    assert "SECURITY INVOKER" in source
    assert "SET search_path = ''" in source
