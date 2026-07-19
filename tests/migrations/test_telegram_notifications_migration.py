from pathlib import Path


MIGRATION = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260720_000022_enable_telegram_notifications.py"
)


def test_telegram_migration_is_additive_and_channel_safe() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "20260720_000022"' in source
    assert 'down_revision = "20260715_000021"' in source
    assert "claim_notification_outbox_batch_v62" in source
    assert "channel IN ('email', 'telegram')" in source
    assert "channel <> 'telegram' OR kind = 'threat_detected'" in source
    assert "o.channel IN ('email', 'telegram')" in source
    assert "SECURITY INVOKER" in source
    assert "SET search_path = ''" in source


def test_telegram_migration_downgrade_refuses_data_loss() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert "cannot downgrade while Telegram notification rows exist" in source
    assert "DROP FUNCTION IF EXISTS public.claim_notification_outbox_batch_v62" in source
