"""Add the Owner role and align database authorization with the RBAC policy."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# The migration rewrites existing function definitions from PostgreSQL's
# canonical source, rather than copying their full bodies into another
# revision. This keeps the change focused on the authorization predicates and
# preserves the existing notification, audit, and MFA behavior.
# ruff: noqa: E501

revision = "20260905_000029"
down_revision = "20260803_000028"
branch_labels = None
depends_on = None

_HELPER_SIGNATURE = "public.auth_actor_can_manage_account(uuid, uuid, text)"
_ROLE_CONSTRAINT_NAMES = (
    "ck_auth_accounts_role",
    "ck_auth_accounts_ck_auth_accounts_role",
)

_NO_TARGET_ACCOUNT_FUNCTIONS = (
    "public.admin_create_auth_account(uuid, text, text, text, text, timestamp with time zone, text, text, text)",
    "public.admin_create_auth_account_protected_v61(uuid, text, text, text, text, timestamp with time zone, jsonb, text, text)",
)

_TARGET_ACCOUNT_FUNCTIONS = (
    "public.admin_resend_password_setup(uuid, uuid, text, timestamp with time zone, text, text, text)",
    "public.admin_resend_password_setup_protected_v61(uuid, uuid, text, text, timestamp with time zone, jsonb, text, text)",
    "public.admin_request_managed_email_change(uuid, uuid, text, text, timestamp with time zone, text, text, text)",
    "public.admin_request_managed_email_change_protected_v61(uuid, uuid, text, text, timestamp with time zone, jsonb, text, text)",
    "public.admin_set_account_enabled(uuid, uuid, boolean)",
    "public.admin_set_account_enabled_v61(uuid, uuid, boolean)",
)

_ROLE_CHANGE_FUNCTION = (
    "public.admin_change_account_role(uuid, uuid, text)",
)

_MFA_ROLE_FUNCTIONS = (
    "public.consume_backup_code_for_recovery(uuid, uuid, text, timestamp with time zone)",
    "public.begin_email_recovery_challenge(uuid, text, text, timestamp with time zone)",
    "public.begin_mfa_challenge_v61(uuid, text, timestamp with time zone)",
    "public.mfa_enrollment_challenge_available_v61(uuid, text)",
    "public.begin_email_recovery_challenge_v61(uuid, text, text, timestamp with time zone, text, text, text)",
    "public.consume_backup_code_for_recovery_v61(uuid, uuid, text, timestamp with time zone)",
    "public.begin_email_recovery_challenge_protected_v61(uuid, text, text, text, timestamp with time zone, jsonb, text, text)",
    "public.begin_recovery_totp_enrollment_v61(uuid, uuid, text, text, integer, timestamp with time zone, text)",
)

_RECENT_TOTP_FUNCTION = (
    "public.begin_recent_totp_challenge_v61(uuid, text, timestamp with time zone)"
)

_ACCOUNT_AUTHORIZATION_PATCH = (
    (
        "role = 'ADMIN' AND disabled_at IS NULL",
        "public.auth_actor_can_manage_account(p_actor_account_id, NULL, p_role) AND disabled_at IS NULL",
    ),
    (
        "p_role NOT IN ('ADMIN', 'ANALYST', 'VIEWER')",
        "p_role NOT IN ('OWNER', 'ADMIN', 'ANALYST', 'VIEWER')",
    ),
)

_TARGET_ACCOUNT_AUTHORIZATION_PATCH = (
    (
        "role = 'ADMIN' AND disabled_at IS NULL",
        "public.auth_actor_can_manage_account(p_actor_account_id, p_target_account_id, NULL) AND disabled_at IS NULL",
    ),
)

_ROLE_CHANGE_AUTHORIZATION_PATCH = (
    (
        "role = 'ADMIN' AND disabled_at IS NULL",
        "public.auth_actor_can_manage_account(p_actor_account_id, p_target_account_id, p_role) AND disabled_at IS NULL",
    ),
    (
        "p_role NOT IN ('ADMIN', 'ANALYST', 'VIEWER')",
        "p_role NOT IN ('OWNER', 'ADMIN', 'ANALYST', 'VIEWER')",
    ),
)

_MFA_ROLE_PATCH = (
    (
        "role IN ('ADMIN', 'ANALYST')",
        "role IN ('OWNER', 'ADMIN', 'ANALYST')",
    ),
    (
        "v_role NOT IN ('ADMIN', 'ANALYST')",
        "v_role NOT IN ('OWNER', 'ADMIN', 'ANALYST')",
    ),
)

_RECENT_TOTP_ROLE_PATCH = (
    (
        "a.role = 'ADMIN'",
        "a.role IN ('OWNER', 'ADMIN')",
    ),
)

_RESET_MFA_FUNCTION = "public.admin_reset_mfa(uuid, uuid, text, text, text)"
_RESET_MFA_PATCH = (
    (
        "IF v_actor_role <> 'ADMIN' THEN",
        "IF NOT public.auth_actor_can_manage_account(p_actor_account_id, p_target_account_id, NULL) THEN",
    ),
)


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _rewrite_function(
    signature: str,
    replacements: tuple[tuple[str, str], ...],
) -> None:
    expression = "pg_get_functiondef(v_oid)"
    for old, new in replacements:
        expression = (
            f"replace({expression}, {_sql_literal(old)}, {_sql_literal(new)})"
        )

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
    RAISE EXCEPTION 'authorization function is missing: %', {_sql_literal(signature)};
  END IF;
  v_before := pg_get_functiondef(v_oid);
  v_after := {expression};
  IF v_after = v_before THEN
    RAISE EXCEPTION 'authorization predicate was not found in: %', {_sql_literal(signature)};
  END IF;
  EXECUTE v_after;
END
$$;
"""
        )
    )


def _restrict(signature: str) -> None:
    op.execute(sa.text(f"REVOKE EXECUTE ON FUNCTION {signature} FROM PUBLIC"))
    op.execute(
        sa.text(
            f"""
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION {signature} FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION {signature} FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT EXECUTE ON FUNCTION {signature} TO service_role';
  END IF;
END
$$;
"""
        )
    )


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def _replace_role_constraint(definition: str) -> None:
    names = ", ".join(_sql_literal(name) for name in _ROLE_CONSTRAINT_NAMES)
    op.execute(
        sa.text(
            f"""
DO $$
DECLARE
  v_constraint_name text;
BEGIN
  SELECT c.conname INTO v_constraint_name
  FROM pg_constraint AS c
  WHERE c.conrelid = 'public.auth_accounts'::regclass
    AND c.contype = 'c'
    AND c.conname IN ({names})
  LIMIT 1;
  IF v_constraint_name IS NULL THEN
    RAISE EXCEPTION 'auth_accounts role constraint is missing';
  END IF;
  EXECUTE format('ALTER TABLE public.auth_accounts DROP CONSTRAINT %I', v_constraint_name);
END
$$;
ALTER TABLE public.auth_accounts
  ADD CONSTRAINT ck_auth_accounts_role CHECK ({definition});
"""
        )
    )


def _create_management_helper() -> None:
    op.execute(
        sa.text(
            """
CREATE FUNCTION public.auth_actor_can_manage_account(
  p_actor_account_id uuid,
  p_target_account_id uuid,
  p_requested_role text
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_actor_role text;
  v_target_role text;
BEGIN
  SELECT role INTO v_actor_role
  FROM public.auth_accounts
  WHERE id = p_actor_account_id AND disabled_at IS NULL;

  IF v_actor_role IS NULL OR v_actor_role NOT IN ('OWNER', 'ADMIN') THEN
    RETURN false;
  END IF;
  IF v_actor_role = 'ADMIN' AND upper(coalesce(p_requested_role, '')) = 'OWNER' THEN
    RETURN false;
  END IF;

  IF p_target_account_id IS NOT NULL THEN
    SELECT role INTO v_target_role
    FROM public.auth_accounts
    WHERE id = p_target_account_id;
    IF v_actor_role = 'ADMIN' AND v_target_role = 'OWNER' THEN
      RETURN false;
    END IF;
  END IF;
  RETURN true;
END
$$;
"""
        )
    )
    _restrict(_HELPER_SIGNATURE)


def upgrade() -> None:
    # The auth/security schema and its RPCs are PostgreSQL/Supabase-only. Keep
    # SQLite migration replay usable for the repository's non-auth tests while
    # applying the real role constraint and function changes on PostgreSQL.
    if not _is_postgresql():
        return
    _replace_role_constraint(
        "role IN ('OWNER', 'ADMIN', 'ANALYST', 'VIEWER')",
    )
    _create_management_helper()

    for signature in _NO_TARGET_ACCOUNT_FUNCTIONS:
        _rewrite_function(signature, _ACCOUNT_AUTHORIZATION_PATCH)
    for signature in _TARGET_ACCOUNT_FUNCTIONS:
        _rewrite_function(signature, _TARGET_ACCOUNT_AUTHORIZATION_PATCH)
    for signature in _ROLE_CHANGE_FUNCTION:
        _rewrite_function(signature, _ROLE_CHANGE_AUTHORIZATION_PATCH)
    _rewrite_function(_RESET_MFA_FUNCTION, _RESET_MFA_PATCH)

    for signature in _MFA_ROLE_FUNCTIONS:
        _rewrite_function(signature, _MFA_ROLE_PATCH)
    _rewrite_function(_RECENT_TOTP_FUNCTION, _RECENT_TOTP_ROLE_PATCH)


def downgrade() -> None:
    if not _is_postgresql():
        return
    op.execute(
        sa.text(
            """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.auth_accounts WHERE role = 'OWNER') THEN
    RAISE EXCEPTION 'Owner accounts must be reassigned before downgrading the role hierarchy';
  END IF;
END
$$;
"""
        )
    )

    _rewrite_function(
        _RESET_MFA_FUNCTION,
        tuple((new, old) for old, new in _RESET_MFA_PATCH),
    )
    for signature in reversed(_ROLE_CHANGE_FUNCTION):
        _rewrite_function(
            signature,
            tuple((new, old) for old, new in _ROLE_CHANGE_AUTHORIZATION_PATCH),
        )
    for signature in reversed(_TARGET_ACCOUNT_FUNCTIONS):
        _rewrite_function(
            signature,
            tuple((new, old) for old, new in _TARGET_ACCOUNT_AUTHORIZATION_PATCH),
        )
    for signature in reversed(_NO_TARGET_ACCOUNT_FUNCTIONS):
        _rewrite_function(
            signature,
            tuple((new, old) for old, new in _ACCOUNT_AUTHORIZATION_PATCH),
        )
    for signature in reversed((_RECENT_TOTP_FUNCTION,)):
        _rewrite_function(
            signature,
            tuple((new, old) for old, new in _RECENT_TOTP_ROLE_PATCH),
        )
    for signature in reversed(_MFA_ROLE_FUNCTIONS):
        _rewrite_function(
            signature,
            tuple((new, old) for old, new in _MFA_ROLE_PATCH),
        )

    op.execute(sa.text(f"DROP FUNCTION IF EXISTS {_HELPER_SIGNATURE}"))
    _replace_role_constraint(
        "role IN ('ADMIN', 'ANALYST', 'VIEWER')",
    )
