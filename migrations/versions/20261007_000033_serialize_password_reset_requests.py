"""Serialize concurrent password-reset issuance for the same account."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261007_000033"
down_revision = "20261007_000032"
branch_labels = None
depends_on = None

_RESET_FUNCTION_SIGNATURE = (
    "public.create_password_reset_token_protected_v61("
    "uuid, text, timestamp with time zone, jsonb, text, text, text)"
)
_ACCOUNT_LOOKUP = (
    "WHERE id = p_account_id AND disabled_at IS NULL "
    "AND email_verified_at IS NOT NULL;"
)
_ACCOUNT_LOOKUP_WITH_LOCK = (
    "WHERE id = p_account_id AND disabled_at IS NULL "
    "AND email_verified_at IS NOT NULL\n  FOR UPDATE;"
)


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _rewrite_account_lookup(expected: str, replacement: str) -> None:
    op.execute(
        sa.text(
            f"""
DO $migration$
DECLARE
  v_oid oid;
  v_before text;
  v_after text;
BEGIN
  v_oid := pg_catalog.to_regprocedure({_sql_literal(_RESET_FUNCTION_SIGNATURE)});
  IF v_oid IS NULL THEN
    RAISE EXCEPTION 'password reset issuance function is missing';
  END IF;
  v_before := pg_catalog.pg_get_functiondef(v_oid);

  IF pg_catalog.strpos(v_before, {_sql_literal(expected)}) > 0 THEN
    v_after := pg_catalog.replace(
      v_before, {_sql_literal(expected)}, {_sql_literal(replacement)}
    );
    IF v_after = v_before THEN
      RAISE EXCEPTION 'password reset issuance function was not updated';
    END IF;
    EXECUTE v_after;
  ELSIF pg_catalog.strpos(v_before, {_sql_literal(replacement)}) = 0 THEN
    RAISE EXCEPTION
      'password reset account lookup does not match the expected definition';
  END IF;
END
$migration$;
"""
        )
    )


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgresql():
        return
    _rewrite_account_lookup(_ACCOUNT_LOOKUP, _ACCOUNT_LOOKUP_WITH_LOCK)


def downgrade() -> None:
    if not _is_postgresql():
        return
    _rewrite_account_lookup(_ACCOUNT_LOOKUP_WITH_LOCK, _ACCOUNT_LOOKUP)
