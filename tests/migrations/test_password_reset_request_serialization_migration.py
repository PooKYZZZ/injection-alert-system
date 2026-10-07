from pathlib import Path

MIGRATION = Path(
    "migrations/versions/20261007_000033_serialize_password_reset_requests.py"
)


def test_migration_locks_the_account_before_reissuing_a_reset_token() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "20261007_000033"' in source
    assert 'down_revision = "20261007_000032"' in source
    assert "public.create_password_reset_token_protected_v61(" in source
    assert "AND email_verified_at IS NOT NULL\\n  FOR UPDATE;" in source
    assert "_rewrite_account_lookup(_ACCOUNT_LOOKUP," in source
    assert "_ACCOUNT_LOOKUP_WITH_LOCK)" in source
    assert "_rewrite_account_lookup(_ACCOUNT_LOOKUP_WITH_LOCK," in source
    assert "_ACCOUNT_LOOKUP)" in source
    assert "def downgrade()" in source
