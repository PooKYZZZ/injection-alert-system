import importlib.util
from pathlib import Path

MIGRATION = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260704_000008_add_auth_security_foundation.py"
)

TABLES = {
    "auth_accounts",
    "auth_mfa_factors",
    "auth_mfa_challenges",
    "auth_mfa_completion_tokens",
    "auth_email_otp_challenges",
    "auth_backup_codes",
    "auth_reset_tokens",
    "security_events",
    "notification_outbox",
}


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_migration_defines_every_auth_security_table() -> None:
    source = migration_source()

    for table in TABLES:
        assert f'op.create_table(\n        "{table}"' in source


def test_migration_defines_required_security_columns_and_indexes() -> None:
    source = migration_source()

    for required in (
        "secret_ciphertext",
        "secret_key_version",
        "last_used_time_step",
        "dedupe_key",
        "locked_at",
        "locked_by",
        "attempts",
        "max_attempts",
        "next_attempt_at",
        "last_error_code",
        "payload_safe_json",
        "auth_accounts_email_unique",
        "auth_accounts_username_unique",
        "idx_auth_mfa_challenges_active",
        "idx_auth_mfa_completion_tokens_active",
        "idx_auth_email_otp_challenges_active",
        "auth_backup_codes_account_code_unique",
        "idx_notification_outbox_pending",
        "idx_notification_outbox_dedupe",
    ):
        assert required in source

    assert "lower(email)" in source
    assert "lower(username)" in source
    assert "username is not null" in source


def test_migration_enforces_account_password_state_consistency() -> None:
    source = migration_source()

    assert "ck_auth_accounts_password_state" in source
    assert "password_hash IS NULL AND password_set_at IS NULL" in source
    assert "password_hash IS NOT NULL AND password_set_at IS NOT NULL" in source


def test_migration_maintains_auth_accounts_updated_at() -> None:
    source = migration_source().lower()

    assert "create function set_auth_accounts_updated_at()" in source
    assert "new.updated_at = now()" in source
    assert "create trigger trg_auth_accounts_set_updated_at" in source
    assert "before update on auth_accounts" in source
    assert "drop trigger if exists trg_auth_accounts_set_updated_at" in source
    assert "drop function if exists set_auth_accounts_updated_at()" in source


def test_migration_enables_rls_without_creating_policies_or_grants(
    monkeypatch,
) -> None:
    source = migration_source().lower()
    spec = importlib.util.spec_from_file_location("auth_security_migration", MIGRATION)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    statements: list[str] = []
    monkeypatch.setattr(
        migration.op,
        "execute",
        lambda statement: statements.append(str(statement).lower()),
    )

    for table in TABLES:
        migration._enable_rls_and_revoke_access(table)
        rendered = "\n".join(statements)
        assert f"alter table {table} enable row level security" in rendered
        assert f"revoke all on table {table} from public" in rendered

    assert "create policy" not in source
    assert " grant " not in source
    assert "anon" in source
    assert "authenticated" in source


def test_migration_is_additive_to_existing_schema() -> None:
    source = migration_source().lower()
    upgrade = source.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]

    assert "alter column" not in upgrade
    assert "drop table" not in upgrade
    assert "traffic_logs" not in upgrade


def test_downgrade_removes_only_pr1_foundation_objects() -> None:
    source = migration_source().lower()
    downgrade = source.split("def downgrade()", 1)[1]

    assert "drop trigger if exists trg_auth_accounts_set_updated_at" in downgrade
    assert "drop function if exists set_auth_accounts_updated_at()" in downgrade
    assert "op.drop_table(table)" in downgrade
    assert "drop column" not in downgrade
    assert "alter table" not in downgrade
    assert "traffic_logs" not in downgrade
