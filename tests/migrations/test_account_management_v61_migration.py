from pathlib import Path


MIGRATION = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260710_000010_account_management_v61.py"
)


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_migration_adds_pending_email_and_explicit_account_rpcs() -> None:
    source = migration_source()

    for field in ("pending_email", "pending_email_requested_at"):
        assert field in source
    for function in (
        "admin_create_auth_account",
        "consume_password_setup_token",
        "admin_change_account_role",
        "admin_set_account_enabled",
        "admin_request_managed_email_change",
        "activate_verified_managed_email",
    ):
        assert f"create function public.{function}" in source
        assert f"drop function if exists public.{function}" in source

    assert "security invoker" in source
    assert "set search_path = ''" in source
    assert "from public" in source
    assert "from anon" in source
    assert "from authenticated" in source
    assert "to service_role" in source


def test_setup_and_email_verification_are_single_use_and_session_invalidating() -> None:
    source = migration_source()

    assert "purpose = 'password_setup'" in source
    assert "purpose = 'email_verification'" in source
    assert "status = 'pending'" in source
    assert "used_at is null" in source
    assert "authz_version = authz_version + 1" in source
    assert "email_verified_at" in source
    assert "mfa_required" in source
    assert "role <> 'viewer'" in source


def test_downgrade_removes_only_unrepresentable_ephemeral_email_tokens() -> None:
    source = migration_source()
    downgrade = source.split("def downgrade()", 1)[1]

    assert "delete from public.auth_reset_tokens" in downgrade
    assert "purpose = 'email_verification'" in downgrade
    assert "delete from public.auth_accounts" not in downgrade
    assert "delete from public.security_events" not in downgrade
