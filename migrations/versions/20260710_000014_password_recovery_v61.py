"""Add atomic password reset and ADMIN MFA reset transitions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260710_000014"
down_revision = "20260710_000013"
branch_labels = None
depends_on = None


_FUNCTION_SIGNATURES = (
    "public.create_password_reset_token(uuid, text, timestamp with time zone, text, text, text, text)",
    "public.consume_password_reset_and_change_password(text, text)",
    "public.admin_reset_mfa(uuid, uuid, text, text, text)",
    "public.operator_reset_admin_mfa(uuid, text, text)",
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
$$
"""
        )
    )


def upgrade() -> None:
    op.execute(
        sa.text(
            """
CREATE OR REPLACE FUNCTION public.create_password_reset_token(
  p_account_id uuid, p_token_hash text, p_expires_at timestamptz,
  p_reset_url text, p_dedupe_key text, p_provider_idempotency_key text,
  p_reason text
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_email text; v_event uuid;
BEGIN
  IF char_length(p_token_hash) <> 64 OR p_expires_at <= clock_timestamp()
     OR char_length(p_reset_url) < 1 OR char_length(p_reset_url) > 1024
     OR char_length(p_reason) > 128 THEN RAISE EXCEPTION 'invalid reset request'; END IF;
  SELECT email INTO v_email FROM public.auth_accounts
  WHERE id = p_account_id AND disabled_at IS NULL AND email_verified_at IS NOT NULL;
  IF v_email IS NULL THEN RETURN false; END IF;
  UPDATE public.auth_reset_tokens SET status = 'revoked'
  WHERE account_id = p_account_id AND purpose = 'password_reset' AND status = 'pending';
  INSERT INTO public.auth_reset_tokens (account_id, purpose, token_hash, status, expires_at)
  VALUES (p_account_id, 'password_reset', p_token_hash, 'pending', p_expires_at);
  INSERT INTO public.security_events (source, event_type, severity, outcome, account_id, safe_summary_json)
  VALUES ('auth', 'auth.password_reset_requested', 'medium', 'success', p_account_id, jsonb_build_object('reason', p_reason))
  RETURNING id INTO v_event;
  INSERT INTO public.notification_outbox (event_id, dedupe_key, channel, recipient, kind, template_version, provider_idempotency_key, payload_safe_json)
  VALUES (v_event, p_dedupe_key, 'email', v_email, 'password_reset', 1, p_provider_idempotency_key, jsonb_build_object('reset_url', p_reset_url));
  RETURN true;
END
$$;

CREATE OR REPLACE FUNCTION public.consume_password_reset_and_change_password(
  p_token_hash text, p_password_hash text
) RETURNS uuid
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_account_id uuid; v_email text; v_event uuid;
BEGIN
  IF char_length(p_token_hash) <> 64 OR char_length(p_password_hash) < 20 THEN
    RAISE EXCEPTION 'invalid reset request';
  END IF;
  SELECT account_id INTO v_account_id FROM public.auth_reset_tokens
  WHERE token_hash = p_token_hash AND purpose = 'password_reset'
    AND status = 'pending' AND expires_at > clock_timestamp()
  FOR UPDATE;
  IF v_account_id IS NULL THEN RAISE EXCEPTION 'reset token is invalid or expired'; END IF;
  UPDATE public.auth_reset_tokens SET status = 'used', used_at = clock_timestamp()
  WHERE token_hash = p_token_hash AND status = 'pending';
  UPDATE public.auth_accounts
  SET password_hash = p_password_hash, password_set_at = clock_timestamp(), authz_version = authz_version + 1
  WHERE id = v_account_id RETURNING email INTO v_email;
  UPDATE public.auth_mfa_challenges SET status = 'expired', used_at = clock_timestamp()
  WHERE account_id = v_account_id AND status IN ('pending', 'verified');
  UPDATE public.auth_mfa_completion_tokens SET status = 'expired'
  WHERE account_id = v_account_id AND status = 'pending';
  INSERT INTO public.security_events (source, event_type, severity, outcome, account_id, safe_summary_json)
  VALUES ('auth', 'auth.password_reset_completed', 'high', 'success', v_account_id, '{}'::jsonb)
  RETURNING id INTO v_event;
  INSERT INTO public.notification_outbox (event_id, dedupe_key, channel, recipient, kind, template_version, provider_idempotency_key, payload_safe_json)
  VALUES (v_event, 'password-changed/' || v_account_id::text || '/' || v_event::text, 'email', v_email, 'password_changed', 1, 'password-changed/' || v_event::text, '{}'::jsonb);
  RETURN v_account_id;
END
$$;

CREATE OR REPLACE FUNCTION public.admin_reset_mfa(
  p_actor_account_id uuid, p_target_account_id uuid, p_reason text,
  p_dedupe_key text, p_provider_idempotency_key text
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_email text; v_actor_role text; v_event uuid;
BEGIN
  IF p_actor_account_id = p_target_account_id OR char_length(trim(p_reason)) < 1 OR char_length(p_reason) > 128 THEN
    RAISE EXCEPTION 'invalid MFA reset request';
  END IF;
  SELECT role INTO v_actor_role FROM public.auth_accounts
  WHERE id = p_actor_account_id AND disabled_at IS NULL;
  IF v_actor_role <> 'ADMIN' THEN RAISE EXCEPTION 'MFA reset is unavailable'; END IF;
  SELECT email INTO v_email FROM public.auth_accounts WHERE id = p_target_account_id;
  IF v_email IS NULL THEN RAISE EXCEPTION 'account not found'; END IF;
  UPDATE public.auth_mfa_factors SET status = 'revoked', revoked_at = clock_timestamp()
  WHERE account_id = p_target_account_id AND factor_type = 'totp' AND status = 'active';
  UPDATE public.auth_backup_codes SET revoked_at = clock_timestamp()
  WHERE account_id = p_target_account_id AND used_at IS NULL AND revoked_at IS NULL;
  UPDATE public.auth_mfa_challenges SET status = 'expired', used_at = clock_timestamp()
  WHERE account_id = p_target_account_id AND status IN ('pending', 'verified');
  UPDATE public.auth_mfa_completion_tokens SET status = 'expired'
  WHERE account_id = p_target_account_id AND status = 'pending';
  UPDATE public.auth_accounts SET authz_version = authz_version + 1 WHERE id = p_target_account_id;
  INSERT INTO public.security_events (source, event_type, severity, outcome, account_id, safe_summary_json)
  VALUES ('auth', 'auth.admin_mfa_reset', 'high', 'success', p_target_account_id, jsonb_build_object('reason', p_reason, 'actor_account_id', p_actor_account_id::text))
  RETURNING id INTO v_event;
  INSERT INTO public.notification_outbox (event_id, dedupe_key, channel, recipient, kind, template_version, provider_idempotency_key, payload_safe_json)
  VALUES (v_event, p_dedupe_key, 'email', v_email, 'admin_mfa_reset', 1, p_provider_idempotency_key, '{}'::jsonb);
  RETURN true;
END
$$;

CREATE OR REPLACE FUNCTION public.operator_reset_admin_mfa(
  p_target_account_id uuid, p_confirmation text, p_reason text
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_email text; v_event uuid;
BEGIN
  IF p_confirmation <> 'CYBERTRACE_BREAK_GLASS' OR char_length(trim(p_reason)) < 1 OR char_length(p_reason) > 128 THEN
    RAISE EXCEPTION 'operator confirmation is invalid';
  END IF;
  SELECT email INTO v_email FROM public.auth_accounts WHERE id = p_target_account_id AND role = 'ADMIN';
  IF v_email IS NULL THEN RAISE EXCEPTION 'ADMIN account not found'; END IF;
  UPDATE public.auth_mfa_factors SET status = 'revoked', revoked_at = clock_timestamp()
  WHERE account_id = p_target_account_id AND factor_type = 'totp' AND status = 'active';
  UPDATE public.auth_backup_codes SET revoked_at = clock_timestamp()
  WHERE account_id = p_target_account_id AND used_at IS NULL AND revoked_at IS NULL;
  UPDATE public.auth_mfa_challenges SET status = 'expired', used_at = clock_timestamp()
  WHERE account_id = p_target_account_id AND status IN ('pending', 'verified');
  UPDATE public.auth_mfa_completion_tokens SET status = 'expired'
  WHERE account_id = p_target_account_id AND status = 'pending';
  UPDATE public.auth_accounts SET authz_version = authz_version + 1 WHERE id = p_target_account_id;
  INSERT INTO public.security_events (source, event_type, severity, outcome, account_id, safe_summary_json)
  VALUES ('auth', 'auth.operator_admin_recovery', 'critical', 'success', p_target_account_id, jsonb_build_object('reason', p_reason, 'operator_confirmed', true))
  RETURNING id INTO v_event;
  INSERT INTO public.notification_outbox (event_id, dedupe_key, channel, recipient, kind, template_version, provider_idempotency_key, payload_safe_json)
  VALUES (v_event, 'operator-admin-recovery/' || p_target_account_id::text || '/' || v_event::text, 'email', v_email, 'admin_mfa_reset', 1, 'operator-admin-recovery/' || v_event::text, '{}'::jsonb);
  RETURN true;
END
$$;
"""
        )
    )
    for signature in _FUNCTION_SIGNATURES:
        _restrict(signature)


def downgrade() -> None:
    for signature in reversed(_FUNCTION_SIGNATURES):
        op.execute(sa.text(f"DROP FUNCTION IF EXISTS {signature}"))
