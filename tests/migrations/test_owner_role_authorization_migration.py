from pathlib import Path

MIGRATION = Path(
    "migrations/versions/20260905_000029_owner_role_authorization.py"
)


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_migration_adds_owner_to_storage_and_reuses_one_management_policy() -> None:
    source = migration_source()

    assert 'revision = "20260905_000029"' in source
    assert 'down_revision = "20260803_000028"' in source
    assert "role IN ('OWNER', 'ADMIN', 'ANALYST', 'VIEWER')" in source
    assert "CREATE FUNCTION public.auth_actor_can_manage_account" in source
    assert "v_actor_role NOT IN ('OWNER', 'ADMIN')" in source
    assert (
        "v_actor_role = 'ADMIN' AND upper(coalesce(p_requested_role, '')) = 'OWNER'"
        in source
    )
    assert "v_actor_role = 'ADMIN' AND v_target_role = 'OWNER'" in source

    for signature in (
        "admin_create_auth_account",
        "admin_create_auth_account_protected_v61",
        "admin_resend_password_setup",
        "admin_resend_password_setup_protected_v61",
        "admin_request_managed_email_change",
        "admin_request_managed_email_change_protected_v61",
        "admin_set_account_enabled",
        "admin_set_account_enabled_v61",
        "admin_change_account_role",
        "admin_reset_mfa",
        "consume_backup_code_for_recovery",
        "begin_email_recovery_challenge",
        "begin_mfa_challenge_v61",
        "mfa_enrollment_challenge_available_v61",
        "begin_email_recovery_challenge_protected_v61",
        "begin_recovery_totp_enrollment_v61",
        "begin_recent_totp_challenge_v61",
    ):
        assert signature in source


def test_migration_keeps_owner_mfa_eligible_and_blocks_unsafe_downgrade() -> None:
    source = migration_source()
    downgrade = source.split("def downgrade()", 1)[1]

    assert "role IN ('OWNER', 'ADMIN', 'ANALYST')" in source
    assert "a.role IN ('OWNER', 'ADMIN')" in source
    assert "Owner accounts must be reassigned before downgrading" in downgrade
    assert "DROP FUNCTION IF EXISTS {_HELPER_SIGNATURE}" in downgrade


def test_migration_skips_postgresql_only_auth_rewrites_on_sqlite() -> None:
    source = migration_source()

    assert 'return op.get_bind().dialect.name == "postgresql"' in source
    assert source.count("if not _is_postgresql():\n        return") == 2
