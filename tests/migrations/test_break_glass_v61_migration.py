from pathlib import Path

MIGRATION = Path(
    "migrations/versions/20260712_000020_restricted_break_glass_v61.py"
)


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_migration_creates_one_nologin_role_and_narrow_definer_function() -> None:
    source = migration_source()

    assert 'revision = "20260712_000020"' in source
    assert 'down_revision = "20260711_000019"' in source
    assert "CREATE ROLE cybertrace_break_glass NOLOGIN NOINHERIT NOBYPASSRLS" in source
    assert "operator_reset_admin_mfa_restricted_v61" in source
    assert "SECURITY DEFINER" in source
    assert "SET search_path = ''" in source
    assert "GRANT EXECUTE ON FUNCTION" in source
    assert "TO cybertrace_break_glass" in source


def test_migration_removes_runtime_access_and_records_safe_audit_context() -> None:
    source = migration_source()

    assert "REVOKE EXECUTE ON FUNCTION" in source
    assert '_revoke_from_role_if_present(LEGACY_SIGNATURE, "service_role")' in source
    assert "operator_identity" in source
    assert "database_session_user" in source
    assert "performed_at" in source
    assert "result" in source
    assert "auth.operator_admin_recovery" in source
    assert "p_reason" in source
    assert "p_target_account_id" in source
