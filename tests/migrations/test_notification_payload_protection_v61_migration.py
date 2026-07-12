from pathlib import Path

MIGRATION = Path(
    "migrations/versions/20260711_000019_notification_payload_protection_v61.py"
)


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_migration_adds_protected_atomic_producers_and_plaintext_guard() -> None:
    source = migration_source()

    assert 'revision = "20260711_000019"' in source
    assert 'down_revision = "20260711_000018"' in source
    for function_name in (
        "admin_create_auth_account_protected_v61",
        "admin_resend_password_setup_protected_v61",
        "admin_request_managed_email_change_protected_v61",
        "create_password_reset_token_protected_v61",
        "begin_email_recovery_challenge_protected_v61",
    ):
        assert function_name in source
    assert "notification payload protection is required" in source
    assert "jsonb_object_length" not in source
    assert "payload_safe_json - ARRAY" in source
    assert (
        "active plaintext notification payloads require reviewed remediation" in source
    )


def test_migration_preserves_terminal_scrubbing_and_safe_downgrade_gate() -> None:
    source = migration_source()

    assert "NEW.payload_safe_json := '{}'::jsonb" in source
    assert "status IN ('sent', 'cancelled', 'expired', 'permanent_failure')" in source
    assert "active encrypted notification payloads prevent downgrade" in source
    assert "def downgrade()" in source
