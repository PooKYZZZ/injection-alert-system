"""Add a least-privilege role and function for emergency ADMIN MFA recovery."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260712_000020"
down_revision = "20260711_000019"
branch_labels = None
depends_on = None


ROLE_NAME = "cybertrace_break_glass"
RESTRICTED_SIGNATURE = (
    "public.operator_reset_admin_mfa_restricted_v61(uuid, text, text, text)"
)
LEGACY_SIGNATURE = "public.operator_reset_admin_mfa(uuid, text, text)"


def _revoke_from_role_if_present(signature: str, role: str) -> None:
    op.execute(
        sa.text(
            f"""
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION {signature} FROM {role}';
  END IF;
END
$$
"""
        )
    )


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = '{ROLE_NAME}'
  ) THEN
    CREATE ROLE cybertrace_break_glass NOLOGIN NOINHERIT NOBYPASSRLS;
  END IF;
END
$$;

REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public
FROM cybertrace_break_glass;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public
FROM cybertrace_break_glass;
GRANT USAGE ON SCHEMA public TO cybertrace_break_glass;

CREATE FUNCTION public.operator_reset_admin_mfa_restricted_v61(
  p_target_account_id uuid,
  p_operator_identity text,
  p_reason text,
  p_confirmation text
) RETURNS TABLE(result text, event_id uuid, performed_at timestamptz)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  v_email text;
  v_event_id uuid;
  v_performed_at timestamptz := clock_timestamp();
BEGIN
  IF p_confirmation <> 'CYBERTRACE_BREAK_GLASS' THEN
    RAISE EXCEPTION 'operator confirmation is invalid';
  END IF;
  IF p_operator_identity IS NULL
     OR p_operator_identity <> btrim(p_operator_identity)
     OR char_length(p_operator_identity) NOT BETWEEN 3 AND 128
     OR p_operator_identity ~ '[[:cntrl:]]' THEN
    RAISE EXCEPTION 'operator identity is invalid';
  END IF;
  IF p_reason IS NULL
     OR p_reason <> btrim(p_reason)
     OR char_length(p_reason) NOT BETWEEN 3 AND 128
     OR p_reason ~ '[[:cntrl:]]' THEN
    RAISE EXCEPTION 'operator reason is invalid';
  END IF;

  SELECT a.email INTO v_email
  FROM public.auth_accounts AS a
  WHERE a.id = p_target_account_id AND a.role = 'ADMIN'
  FOR UPDATE;
  IF v_email IS NULL THEN
    RAISE EXCEPTION 'ADMIN account not found';
  END IF;

  UPDATE public.auth_mfa_factors
  SET status = 'revoked', revoked_at = v_performed_at
  WHERE account_id = p_target_account_id
    AND factor_type = 'totp' AND status = 'active';
  UPDATE public.auth_backup_codes
  SET revoked_at = v_performed_at
  WHERE account_id = p_target_account_id
    AND used_at IS NULL AND revoked_at IS NULL;
  UPDATE public.auth_mfa_challenges
  SET status = 'expired', used_at = v_performed_at
  WHERE account_id = p_target_account_id
    AND status IN ('pending', 'verified');
  UPDATE public.auth_mfa_completion_tokens
  SET status = 'expired'
  WHERE account_id = p_target_account_id AND status = 'pending';
  UPDATE public.auth_accounts
  SET authz_version = authz_version + 1
  WHERE id = p_target_account_id;

  INSERT INTO public.security_events (
    source, event_type, severity, outcome, account_id,
    safe_summary_json, created_at
  ) VALUES (
    'auth', 'auth.operator_admin_recovery', 'critical', 'success',
    p_target_account_id,
    jsonb_build_object(
      'operator_identity', p_operator_identity,
      'database_session_user', session_user::text,
      'reason', p_reason,
      'result', 'reset',
      'performed_at', v_performed_at
    ),
    v_performed_at
  ) RETURNING id INTO v_event_id;

  INSERT INTO public.notification_outbox (
    event_id, dedupe_key, channel, recipient, kind, template_version,
    provider_idempotency_key, payload_safe_json
  ) VALUES (
    v_event_id,
    'operator-admin-recovery/' || p_target_account_id::text || '/' || v_event_id::text,
    'email', v_email, 'admin_mfa_reset', 1,
    'operator-admin-recovery/' || v_event_id::text,
    '{{}}'::jsonb
  );

  RETURN QUERY SELECT 'reset'::text, v_event_id, v_performed_at;
END
$$;
"""
        )
    )

    op.execute(
        sa.text(
            f"REVOKE EXECUTE ON FUNCTION {RESTRICTED_SIGNATURE} FROM PUBLIC"
        )
    )
    for role in ("anon", "authenticated", "service_role"):
        _revoke_from_role_if_present(RESTRICTED_SIGNATURE, role)
    _revoke_from_role_if_present(LEGACY_SIGNATURE, "service_role")
    op.execute(
        sa.text(
            f"GRANT EXECUTE ON FUNCTION {RESTRICTED_SIGNATURE} TO {ROLE_NAME}"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"REVOKE EXECUTE ON FUNCTION {RESTRICTED_SIGNATURE} FROM {ROLE_NAME}"
        )
    )
    op.execute(sa.text(f"DROP FUNCTION IF EXISTS {RESTRICTED_SIGNATURE}"))
    op.execute(sa.text(f"REVOKE USAGE ON SCHEMA public FROM {ROLE_NAME}"))
    op.execute(
        sa.text(
            f"""
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT EXECUTE ON FUNCTION {LEGACY_SIGNATURE} TO service_role';
  END IF;
END
$$
"""
        )
    )
