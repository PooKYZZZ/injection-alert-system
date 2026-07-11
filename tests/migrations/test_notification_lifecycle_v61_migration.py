from __future__ import annotations

from pathlib import Path


MIGRATION = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260711_000016_notification_lifecycle_v61.py"
)


def test_notification_lifecycle_migration_is_additive_and_deadline_bound() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "20260711_000016"' in source
    assert 'down_revision = "20260711_000015"' in source
    assert '"deliver_before"' in source
    assert '"terminalized_at"' in source
    assert "cancelled" in source
    assert "expired" in source
    assert "legacy_notification" in source
    assert "email_recovery_completed" in source
    assert "claim_notification_outbox_batch_v61" in source
    assert "deliver_before > clock_timestamp()" in source
    assert "NEW.payload_safe_json := '{}'::jsonb" in source


def test_notification_lifecycle_functions_are_security_invoker_and_search_path_bound() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert source.count("SECURITY INVOKER") >= 7
    assert source.count("SET search_path = ''") >= 7
    assert "channel = 'email'" in source
    assert "kind <> 'legacy_notification'" in source
