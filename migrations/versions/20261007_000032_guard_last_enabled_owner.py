"""Prevent concurrent account RPCs from removing the last enabled Owner."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# These exact source fragments mirror PostgreSQL's canonical function text.
# ruff: noqa: E501

revision = "20261007_000032"
down_revision = "20260930_000031"
branch_labels = None
depends_on = None

_GUARD_SIGNATURE = "public.assert_last_enabled_owner(uuid)"
_ACCOUNT_ROLE_FUNCTIONS = (
    "public.admin_change_account_role(uuid, uuid, text)",
)
_ROLE_LOCK_PATCH = (
    (
        "BEGIN\n  IF p_actor_account_id = p_target_account_id THEN RAISE EXCEPTION 'self role change forbidden'; END IF;",
        "BEGIN\n  PERFORM pg_catalog.pg_advisory_xact_lock(20261007, 32);\n  IF p_actor_account_id = p_target_account_id THEN RAISE EXCEPTION 'self role change forbidden'; END IF;",
    ),
)

_ROLE_GUARD_PATCH = (
    (
        "  UPDATE public.auth_accounts\n  SET role = p_role, mfa_required = p_role <> 'VIEWER',\n      authz_version = authz_version + 1\n  WHERE id = p_target_account_id;",
        "  IF p_role <> 'OWNER' THEN\n    PERFORM public.assert_last_enabled_owner(p_target_account_id);\n  END IF;\n  UPDATE public.auth_accounts\n  SET role = p_role, mfa_required = p_role <> 'VIEWER',\n      authz_version = authz_version + 1\n  WHERE id = p_target_account_id;",
    ),
)

_STATUS_LEGACY_LOCK_PATCH = (
    (
        "BEGIN\n  IF p_actor_account_id = p_target_account_id THEN RAISE EXCEPTION 'self status change forbidden'; END IF;",
        "BEGIN\n  PERFORM pg_catalog.pg_advisory_xact_lock(20261007, 32);\n  IF p_actor_account_id = p_target_account_id THEN RAISE EXCEPTION 'self status change forbidden'; END IF;",
    ),
)

_STATUS_V61_LOCK_PATCH = (
    (
        "BEGIN\n  IF p_actor_account_id = p_target_account_id THEN\n    RAISE EXCEPTION 'self status change forbidden';\n  END IF;",
        "BEGIN\n  PERFORM pg_catalog.pg_advisory_xact_lock(20261007, 32);\n  IF p_actor_account_id = p_target_account_id THEN\n    RAISE EXCEPTION 'self status change forbidden';\n  END IF;",
    ),
)

_STATUS_GUARD_PATCH = (
    (
        "  UPDATE public.auth_accounts\n  SET disabled_at = CASE WHEN p_enabled THEN NULL ELSE clock_timestamp() END,\n      authz_version = authz_version + 1\n  WHERE id = p_target_account_id",
        "  IF p_enabled IS NOT TRUE THEN\n    PERFORM public.assert_last_enabled_owner(p_target_account_id);\n  END IF;\n  UPDATE public.auth_accounts\n  SET disabled_at = CASE WHEN p_enabled THEN NULL ELSE clock_timestamp() END,\n      authz_version = authz_version + 1\n  WHERE id = p_target_account_id",
    ),
)

_ACCOUNT_STATUS_FUNCTIONS = (
    (
        "public.admin_set_account_enabled(uuid, uuid, boolean)",
        _STATUS_LEGACY_LOCK_PATCH + _STATUS_GUARD_PATCH,
    ),
    (
        "public.admin_set_account_enabled_v61(uuid, uuid, boolean)",
        _STATUS_V61_LOCK_PATCH + _STATUS_GUARD_PATCH,
    ),
)


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _rewrite_function(
    signature: str,
    replacements: tuple[tuple[str, str], ...],
) -> None:
    op.execute(
        sa.text(
            f"""
DO $$
DECLARE
  v_oid oid;
  v_before text;
  v_after text;
BEGIN
  v_oid := to_regprocedure({_sql_literal(signature)});
  IF v_oid IS NULL THEN
    RAISE EXCEPTION 'account authorization function is missing: %', {_sql_literal(signature)};
  END IF;
  v_before := pg_get_functiondef(v_oid);
  v_after := v_before;
"""
            + "\n".join(
                f"  IF position({_sql_literal(old)} in v_after) = 0 THEN\n"
                f"    RAISE EXCEPTION 'account transition predicate was not found in: %', {_sql_literal(signature)};\n"
                "  END IF;\n"
                f"  v_after := replace(v_after, {_sql_literal(old)}, {_sql_literal(new)});"
                for old, new in replacements
            )
            + """
  IF v_after = v_before THEN
    RAISE EXCEPTION 'account authorization function was not updated: %', """
            + _sql_literal(signature)
            + """;
  END IF;
  EXECUTE v_after;
END
$$;
"""
        )
    )


def _restrict_guard() -> None:
    op.execute(sa.text(f"REVOKE EXECUTE ON FUNCTION {_GUARD_SIGNATURE} FROM PUBLIC"))
    op.execute(
        sa.text(
            f"""
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION {_GUARD_SIGNATURE} FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION {_GUARD_SIGNATURE} FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT EXECUTE ON FUNCTION {_GUARD_SIGNATURE} TO service_role';
  END IF;
END
$$;
"""
        )
    )


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgresql():
        return

    op.execute(
        sa.text(
            """
CREATE FUNCTION public.assert_last_enabled_owner(p_target_account_id uuid)
RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_target_is_enabled_owner boolean;
  v_enabled_owner_count bigint;
BEGIN
  IF pg_catalog.current_setting('transaction_isolation') <> 'read committed' THEN
    RAISE EXCEPTION 'LAST_OWNER_GUARD_REQUIRES_READ_COMMITTED'
      USING ERRCODE = '40001';
  END IF;
  PERFORM pg_catalog.pg_advisory_xact_lock(20261007, 32);
  SELECT EXISTS (
    SELECT 1 FROM public.auth_accounts
    WHERE id = p_target_account_id AND role = 'OWNER' AND disabled_at IS NULL
  ) INTO v_target_is_enabled_owner;
  IF NOT v_target_is_enabled_owner THEN
    RETURN;
  END IF;

  SELECT count(*) INTO v_enabled_owner_count
  FROM public.auth_accounts
  WHERE role = 'OWNER' AND disabled_at IS NULL;
  IF v_enabled_owner_count <= 1 THEN
    RAISE EXCEPTION 'LAST_ENABLED_OWNER' USING ERRCODE = '23514';
  END IF;
END
$$;
"""
        )
    )
    _restrict_guard()

    for signature in _ACCOUNT_ROLE_FUNCTIONS:
        _rewrite_function(signature, _ROLE_LOCK_PATCH + _ROLE_GUARD_PATCH)
    for signature, patches in _ACCOUNT_STATUS_FUNCTIONS:
        _rewrite_function(signature, patches)


def downgrade() -> None:
    if not _is_postgresql():
        return

    for signature, patches in reversed(_ACCOUNT_STATUS_FUNCTIONS):
        _rewrite_function(
            signature,
            tuple((new, old) for old, new in reversed(patches)),
        )
    for signature in reversed(_ACCOUNT_ROLE_FUNCTIONS):
        _rewrite_function(
            signature,
            tuple((new, old) for old, new in _ROLE_LOCK_PATCH + _ROLE_GUARD_PATCH),
        )
    op.execute(sa.text(f"DROP FUNCTION IF EXISTS {_GUARD_SIGNATURE}"))
