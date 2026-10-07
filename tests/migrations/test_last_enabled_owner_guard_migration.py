from pathlib import Path

MIGRATION = Path(
    "migrations/versions/20261007_000032_guard_last_enabled_owner.py"
)


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_migration_serializes_and_guards_every_account_role_status_rpc() -> None:
    source = migration_source()

    assert 'revision = "20261007_000032"' in source
    assert 'down_revision = "20260930_000031"' in source
    assert "CREATE FUNCTION public.assert_last_enabled_owner" in source
    assert "LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path = ''" in source
    assert "current_setting('transaction_isolation') <> 'read committed'" in source
    assert "pg_catalog.pg_advisory_xact_lock(20261007, 32)" in source
    assert "role = 'OWNER' AND disabled_at IS NULL" in source
    assert "IF v_enabled_owner_count <= 1 THEN" in source
    assert "IF p_enabled IS NOT TRUE THEN" in source
    assert "RAISE EXCEPTION 'LAST_ENABLED_OWNER' USING ERRCODE = '23514'" in source
    assert "REVOKE EXECUTE ON FUNCTION {_GUARD_SIGNATURE} FROM PUBLIC" in source
    assert "GRANT EXECUTE ON FUNCTION {_GUARD_SIGNATURE} TO service_role" in source

    for signature in (
        "admin_change_account_role(uuid, uuid, text)",
        "admin_set_account_enabled(uuid, uuid, boolean)",
        "admin_set_account_enabled_v61(uuid, uuid, boolean)",
    ):
        assert f'"public.{signature}"' in source
    assert "_STATUS_LEGACY_LOCK_PATCH" in source
    assert "_STATUS_V61_LOCK_PATCH" in source
    assert "_STATUS_LEGACY_LOCK_PATCH + _STATUS_GUARD_PATCH" in source
    assert "_STATUS_V61_LOCK_PATCH + _STATUS_GUARD_PATCH" in source
    assert "public.assert_last_enabled_owner(p_target_account_id)" in source
    assert "PERFORM pg_catalog.pg_advisory_xact_lock(20261007, 32);" in source


def test_migration_reverts_only_its_function_patches_and_skips_sqlite() -> None:
    source = migration_source()
    downgrade = source.split("def downgrade()", 1)[1]

    assert 'return op.get_bind().dialect.name == "postgresql"' in source
    assert "tuple((new, old) for old, new in reversed(patches))" in downgrade
    assert (
        "tuple((new, old) for old, new in _ROLE_LOCK_PATCH + _ROLE_GUARD_PATCH)"
        in downgrade
    )
    assert "DROP FUNCTION IF EXISTS {_GUARD_SIGNATURE}" in downgrade
