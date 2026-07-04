"""Add the auth/security schema foundation.

Revision ID: 20260704_000008
Revises: 20260324_000007
Create Date: 2026-07-04 03:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260704_000008"
down_revision = "20260324_000007"
branch_labels = None
depends_on = None

AUTH_SECURITY_TABLES = (
    "auth_accounts",
    "auth_mfa_factors",
    "auth_mfa_challenges",
    "auth_mfa_completion_tokens",
    "auth_email_otp_challenges",
    "auth_backup_codes",
    "auth_reset_tokens",
    "security_events",
    "notification_outbox",
)


def _uuid() -> sa.TypeEngine:
    return postgresql.UUID(as_uuid=True)


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def _enable_rls_and_revoke_access(table: str) -> None:
    op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"REVOKE ALL ON TABLE {table} FROM PUBLIC"))
    op.execute(
        sa.text(
            f"""
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE {table} FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE {table} FROM authenticated';
  END IF;
END
$$
"""
        )
    )


def upgrade() -> None:
    created_at, updated_at = _timestamps()
    op.create_table(
        "auth_accounts",
        sa.Column(
            "id",
            _uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("username", sa.Text()),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "authz_version", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("password_hash", sa.Text()),
        sa.Column("password_set_at", sa.DateTime(timezone=True)),
        sa.Column("email_verified_at", sa.DateTime(timezone=True)),
        sa.Column(
            "mfa_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
        created_at,
        updated_at,
        sa.CheckConstraint(
            "role IN ('ADMIN', 'ANALYST', 'VIEWER')",
            name="ck_auth_accounts_role",
        ),
        sa.CheckConstraint(
            "authz_version >= 1", name="ck_auth_accounts_authz_version"
        ),
        sa.CheckConstraint(
            """
            (password_hash IS NULL AND password_set_at IS NULL)
            OR
            (password_hash IS NOT NULL AND password_set_at IS NOT NULL)
            """,
            name="ck_auth_accounts_password_state",
        ),
    )
    op.create_index(
        "auth_accounts_email_unique",
        "auth_accounts",
        [sa.text("lower(email)")],
        unique=True,
    )
    op.create_index(
        "auth_accounts_username_unique",
        "auth_accounts",
        [sa.text("lower(username)")],
        unique=True,
        postgresql_where=sa.text("username is not null"),
    )
    op.execute(
        sa.text(
            """
CREATE FUNCTION set_auth_accounts_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$
"""
        )
    )
    op.execute(
        sa.text(
            """
CREATE TRIGGER trg_auth_accounts_set_updated_at
BEFORE UPDATE ON auth_accounts
FOR EACH ROW
EXECUTE FUNCTION set_auth_accounts_updated_at()
"""
        )
    )

    op.create_table(
        "auth_mfa_factors",
        sa.Column(
            "id",
            _uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "account_id",
            _uuid(),
            sa.ForeignKey("auth_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("factor_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("secret_ciphertext", sa.Text(), nullable=False),
        sa.Column(
            "secret_key_version",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("last_used_time_step", sa.BigInteger()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("disabled_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("factor_type IN ('totp')", name="ck_auth_mfa_factor_type"),
        sa.CheckConstraint(
            "status IN ('pending', 'verified', 'disabled')",
            name="ck_auth_mfa_factor_status",
        ),
    )
    op.create_index(
        "idx_auth_mfa_factors_account", "auth_mfa_factors", ["account_id"]
    )
    op.create_index(
        "idx_auth_mfa_one_verified_totp",
        "auth_mfa_factors",
        ["account_id"],
        unique=True,
        postgresql_where=sa.text("factor_type = 'totp' and status = 'verified'"),
    )

    op.create_table(
        "auth_mfa_challenges",
        sa.Column(
            "id",
            _uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "account_id",
            _uuid(),
            sa.ForeignKey("auth_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("challenge_hash", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "max_attempts", sa.Integer(), nullable=False, server_default=sa.text("5")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('pending', 'passed', 'expired', 'locked', 'cancelled')",
            name="ck_auth_mfa_challenge_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0", name="ck_auth_mfa_challenge_attempt_count"
        ),
        sa.CheckConstraint(
            "max_attempts > 0", name="ck_auth_mfa_challenge_max_attempts"
        ),
    )
    op.create_index(
        "idx_auth_mfa_challenges_account",
        "auth_mfa_challenges",
        ["account_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_auth_mfa_challenges_active",
        "auth_mfa_challenges",
        ["expires_at"],
        postgresql_where=sa.text("status = 'pending' and used_at is null"),
    )

    op.create_table(
        "auth_mfa_completion_tokens",
        sa.Column(
            "id",
            _uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "account_id",
            _uuid(),
            sa.ForeignKey("auth_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "mfa_challenge_id",
            _uuid(),
            sa.ForeignKey("auth_mfa_challenges.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'used', 'expired')",
            name="ck_auth_mfa_completion_token_status",
        ),
    )
    op.create_index(
        "idx_auth_mfa_completion_tokens_account",
        "auth_mfa_completion_tokens",
        ["account_id"],
    )
    op.create_index(
        "idx_auth_mfa_completion_tokens_active",
        "auth_mfa_completion_tokens",
        ["expires_at"],
        postgresql_where=sa.text("status = 'pending' and used_at is null"),
    )

    op.create_table(
        "auth_email_otp_challenges",
        sa.Column(
            "id",
            _uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "mfa_challenge_id",
            _uuid(),
            sa.ForeignKey("auth_mfa_challenges.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            _uuid(),
            sa.ForeignKey("auth_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email_to", sa.Text(), nullable=False),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "max_attempts", sa.Integer(), nullable=False, server_default=sa.text("5")
        ),
        sa.Column(
            "resend_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("last_sent_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('pending', 'used', 'expired', 'locked')",
            name="ck_auth_email_otp_status",
        ),
        sa.CheckConstraint(
            "attempt_count >= 0", name="ck_auth_email_otp_attempt_count"
        ),
        sa.CheckConstraint(
            "max_attempts > 0", name="ck_auth_email_otp_max_attempts"
        ),
        sa.CheckConstraint(
            "resend_count >= 0", name="ck_auth_email_otp_resend_count"
        ),
    )
    op.create_index(
        "idx_auth_email_otp_challenges_mfa",
        "auth_email_otp_challenges",
        ["mfa_challenge_id"],
    )
    op.create_index(
        "idx_auth_email_otp_challenges_active",
        "auth_email_otp_challenges",
        ["expires_at"],
        postgresql_where=sa.text("status = 'pending' and used_at is null"),
    )

    op.create_table(
        "auth_backup_codes",
        sa.Column(
            "id",
            _uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "account_id",
            _uuid(),
            sa.ForeignKey("auth_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "idx_auth_backup_codes_account", "auth_backup_codes", ["account_id"]
    )
    op.create_index(
        "auth_backup_codes_account_code_unique",
        "auth_backup_codes",
        ["account_id", "code_hash"],
        unique=True,
    )
    op.create_index(
        "idx_auth_backup_codes_unused",
        "auth_backup_codes",
        ["account_id"],
        postgresql_where=sa.text("used_at is null"),
    )

    op.create_table(
        "auth_reset_tokens",
        sa.Column(
            "id",
            _uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "account_id",
            _uuid(),
            sa.ForeignKey("auth_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("purpose", sa.Text(), nullable=False),
        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "purpose IN ('password_setup', 'password_reset', 'mfa_reset')",
            name="ck_auth_reset_token_purpose",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'used', 'expired', 'revoked')",
            name="ck_auth_reset_token_status",
        ),
    )

    op.create_table(
        "security_events",
        sa.Column(
            "id",
            _uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("outcome", sa.Text()),
        sa.Column("action_taken", sa.Text()),
        sa.Column(
            "account_id",
            _uuid(),
            sa.ForeignKey("auth_accounts.id", ondelete="SET NULL"),
        ),
        sa.Column("transaction_id", sa.Text()),
        sa.Column("request_id", sa.Text()),
        sa.Column("route", sa.Text()),
        sa.Column(
            "safe_summary_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "source IN ('auth', 'waf', 'ml', 'bff', 'system')",
            name="ck_security_event_source",
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_security_event_severity",
        ),
    )

    op.create_table(
        "notification_outbox",
        sa.Column(
            "id",
            _uuid(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "event_id",
            _uuid(),
            sa.ForeignKey("security_events.id", ondelete="SET NULL"),
        ),
        sa.Column("dedupe_key", sa.Text()),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("recipient", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "attempts", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "max_attempts", sa.Integer(), nullable=False, server_default=sa.text("5")
        ),
        sa.Column(
            "next_attempt_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "payload_safe_json",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("last_error_code", sa.Text()),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("locked_by", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "channel IN ('email', 'telegram')",
            name="ck_notification_outbox_channel",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sending', 'sent', 'failed', 'skipped')",
            name="ck_notification_outbox_status",
        ),
        sa.CheckConstraint(
            "attempts >= 0", name="ck_notification_outbox_attempts"
        ),
        sa.CheckConstraint(
            "max_attempts > 0", name="ck_notification_outbox_max_attempts"
        ),
    )
    op.create_index(
        "idx_notification_outbox_dedupe",
        "notification_outbox",
        ["dedupe_key"],
        unique=True,
        postgresql_where=sa.text("dedupe_key is not null"),
    )
    op.create_index(
        "idx_notification_outbox_pending",
        "notification_outbox",
        ["status", "next_attempt_at", "created_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )

    for table in AUTH_SECURITY_TABLES:
        _enable_rls_and_revoke_access(table)


def downgrade() -> None:
    op.execute(
        sa.text(
            """
DROP TRIGGER IF EXISTS trg_auth_accounts_set_updated_at ON auth_accounts
"""
        )
    )
    op.execute(sa.text("DROP FUNCTION IF EXISTS set_auth_accounts_updated_at()"))
    for table in reversed(AUTH_SECURITY_TABLES):
        op.drop_table(table)
