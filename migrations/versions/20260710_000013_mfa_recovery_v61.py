"""Add atomic backup-code and verified-email recovery transitions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260710_000013"
down_revision = "20260710_000012"
branch_labels = None
depends_on = None


_FUNCTION_SIGNATURES = (
    "public.consume_backup_code_for_recovery(uuid, uuid, text, timestamp with time zone)",
    "public.begin_email_recovery_challenge(uuid, text, text, timestamp with time zone)",
    "public.consume_email_otp_for_recovery(uuid, text)",
    "public.consume_mfa_recovery_completion_token(text)",
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
CREATE OR REPLACE FUNCTION public.consume_backup_code_for_recovery(
  p_account_id uuid, p_code_id uuid, p_completion_token_hash text,
  p_completion_expires_at timestamptz
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_email text; v_role text; v_challenge_id uuid; v_event uuid;
BEGIN
  IF char_length(p_completion_token_hash) <> 64 OR p_completion_expires_at <= clock_timestamp() THEN
    RAISE EXCEPTION 'invalid recovery token';
  END IF;
  SELECT email, role INTO v_email, v_role FROM public.auth_accounts
  WHERE id = p_account_id AND disabled_at IS NULL AND email_verified_at IS NOT NULL;
  IF v_email IS NULL OR v_role NOT IN ('ADMIN', 'ANALYST') THEN RAISE EXCEPTION 'recovery is unavailable'; END IF;
  UPDATE public.auth_backup_codes SET used_at = clock_timestamp()
  WHERE id = p_code_id AND account_id = p_account_id AND used_at IS NULL AND revoked_at IS NULL;
  IF NOT FOUND THEN RAISE EXCEPTION 'backup code is invalid or already used'; END IF;
  UPDATE public.auth_mfa_factors SET status = 'revoked', revoked_at = clock_timestamp()
  WHERE account_id = p_account_id AND factor_type = 'totp' AND status = 'active';
  UPDATE public.auth_backup_codes SET revoked_at = clock_timestamp()
  WHERE account_id = p_account_id AND used_at IS NULL AND revoked_at IS NULL;
  UPDATE public.auth_mfa_challenges SET status = 'expired', used_at = clock_timestamp()
  WHERE account_id = p_account_id AND status IN ('pending', 'verified');
  UPDATE public.auth_mfa_completion_tokens SET status = 'expired'
  WHERE account_id = p_account_id AND status = 'pending';
  INSERT INTO public.auth_mfa_challenges (
    account_id, challenge_hash, purpose, status, expires_at,
    verified_method, verified_at, completion_token_hash, completion_expires_at
  ) VALUES (
    p_account_id, p_completion_token_hash, 'mfa_recovery', 'verified', p_completion_expires_at,
    'backup_code', clock_timestamp(), p_completion_token_hash, p_completion_expires_at
  ) RETURNING id INTO v_challenge_id;
  INSERT INTO public.auth_mfa_completion_tokens (account_id, mfa_challenge_id, token_hash, status, expires_at)
  VALUES (p_account_id, v_challenge_id, p_completion_token_hash, 'pending', p_completion_expires_at);
  UPDATE public.auth_accounts SET authz_version = authz_version + 1 WHERE id = p_account_id;
  INSERT INTO public.security_events (source, event_type, severity, outcome, account_id, safe_summary_json)
  VALUES ('auth', 'auth.backup_code_used', 'high', 'success', p_account_id, jsonb_build_object('method', 'backup_code', 'recovery', true))
  RETURNING id INTO v_event;
  INSERT INTO public.notification_outbox (event_id, dedupe_key, channel, recipient, kind, template_version, provider_idempotency_key, payload_safe_json)
  VALUES (v_event, 'backup-recovery/' || p_code_id::text, 'email', v_email, 'backup_code_used', 1, 'backup-recovery/' || p_code_id::text, '{}'::jsonb);
  RETURN true;
END
$$;

CREATE OR REPLACE FUNCTION public.begin_email_recovery_challenge(
  p_account_id uuid, p_otp_digest text, p_completion_token_hash text,
  p_expires_at timestamptz
) RETURNS uuid
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_email text; v_role text; v_challenge_id uuid;
BEGIN
  IF char_length(p_otp_digest) <> 64 OR char_length(p_completion_token_hash) <> 64 OR p_expires_at <= clock_timestamp() THEN
    RAISE EXCEPTION 'invalid recovery challenge';
  END IF;
  SELECT email, role INTO v_email, v_role FROM public.auth_accounts
  WHERE id = p_account_id AND disabled_at IS NULL AND email_verified_at IS NOT NULL;
  IF v_email IS NULL OR v_role NOT IN ('ADMIN', 'ANALYST') THEN RAISE EXCEPTION 'recovery is unavailable'; END IF;
  IF EXISTS (
    SELECT 1 FROM public.auth_email_otp_challenges
    WHERE account_id = p_account_id AND status = 'pending' AND created_at > clock_timestamp() - interval '60 seconds'
  ) THEN RAISE EXCEPTION 'recovery resend cooldown'; END IF;
  UPDATE public.auth_email_otp_challenges SET status = 'expired', used_at = clock_timestamp()
  WHERE account_id = p_account_id AND status = 'pending';
  INSERT INTO public.auth_mfa_challenges (
    account_id, challenge_hash, purpose, status, expires_at,
    completion_token_hash, completion_expires_at
  ) VALUES (
    p_account_id, p_completion_token_hash, 'mfa_recovery', 'pending', p_expires_at,
    p_completion_token_hash, p_expires_at
  ) RETURNING id INTO v_challenge_id;
  INSERT INTO public.auth_email_otp_challenges (
    mfa_challenge_id, account_id, email_to, code_hash, status, max_attempts, expires_at
  ) VALUES (v_challenge_id, p_account_id, v_email, p_otp_digest, 'pending', 5, p_expires_at);
  RETURN v_challenge_id;
END
$$;

CREATE OR REPLACE FUNCTION public.consume_email_otp_for_recovery(
  p_account_id uuid, p_otp_digest text
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_id uuid; v_challenge_id uuid; v_email text; v_code_hash text; v_token_hash text; v_expires timestamptz; v_event uuid;
BEGIN
  SELECT e.id, e.mfa_challenge_id, e.email_to, e.code_hash,
         c.completion_token_hash, c.completion_expires_at
  INTO v_id, v_challenge_id, v_email, v_code_hash, v_token_hash, v_expires
  FROM public.auth_email_otp_challenges e
  JOIN public.auth_mfa_challenges c ON c.id = e.mfa_challenge_id
  WHERE e.account_id = p_account_id AND e.status = 'pending' AND e.expires_at > clock_timestamp()
  ORDER BY e.created_at DESC LIMIT 1 FOR UPDATE;
  IF v_id IS NULL THEN RAISE EXCEPTION 'recovery code is invalid or expired'; END IF;
  IF p_otp_digest <> v_code_hash THEN
    UPDATE public.auth_email_otp_challenges
    SET attempt_count = attempt_count + 1,
        status = CASE WHEN attempt_count + 1 >= max_attempts THEN 'locked' ELSE status END
    WHERE id = v_id;
    RAISE EXCEPTION 'recovery code is invalid or expired';
  END IF;
  UPDATE public.auth_email_otp_challenges SET status = 'used', used_at = clock_timestamp() WHERE id = v_id;
  UPDATE public.auth_mfa_factors SET status = 'revoked', revoked_at = clock_timestamp()
  WHERE account_id = p_account_id AND factor_type = 'totp' AND status = 'active';
  UPDATE public.auth_backup_codes SET revoked_at = clock_timestamp()
  WHERE account_id = p_account_id AND used_at IS NULL AND revoked_at IS NULL;
  UPDATE public.auth_mfa_challenges SET status = 'expired', used_at = clock_timestamp()
  WHERE account_id = p_account_id AND status IN ('pending', 'verified') AND id <> v_challenge_id;
  INSERT INTO public.auth_mfa_completion_tokens (account_id, mfa_challenge_id, token_hash, status, expires_at)
  VALUES (p_account_id, v_challenge_id, v_token_hash, 'pending', v_expires);
  UPDATE public.auth_mfa_challenges
  SET status = 'verified', verified_method = 'email_otp', verified_at = clock_timestamp()
  WHERE id = v_challenge_id;
  UPDATE public.auth_accounts SET authz_version = authz_version + 1 WHERE id = p_account_id;
  INSERT INTO public.security_events (source, event_type, severity, outcome, account_id, safe_summary_json)
  VALUES ('auth', 'auth.email_recovery_completed', 'high', 'success', p_account_id, jsonb_build_object('method', 'email_otp'))
  RETURNING id INTO v_event;
  INSERT INTO public.notification_outbox (event_id, dedupe_key, channel, recipient, kind, template_version, provider_idempotency_key, payload_safe_json)
  VALUES (v_event, 'email-recovery-completed/' || v_challenge_id::text, 'email', v_email, 'email_recovery_completed', 1, 'email-recovery-completed/' || v_challenge_id::text, '{}'::jsonb);
  RETURN true;
END
$$;

CREATE OR REPLACE FUNCTION public.consume_mfa_recovery_completion_token(
  p_completion_token_hash text
) RETURNS TABLE(account_id uuid, role text, authz_version integer, auth_method text)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_account_id uuid; v_challenge_id uuid; v_method text;
BEGIN
  SELECT t.account_id, t.mfa_challenge_id, c.verified_method
  INTO v_account_id, v_challenge_id, v_method
  FROM public.auth_mfa_completion_tokens t
  JOIN public.auth_mfa_challenges c ON c.id = t.mfa_challenge_id
  WHERE t.token_hash = p_completion_token_hash AND t.status = 'pending'
    AND t.expires_at > clock_timestamp() AND c.purpose = 'mfa_recovery' AND c.status = 'verified'
  FOR UPDATE;
  IF v_account_id IS NULL THEN RAISE EXCEPTION 'recovery completion is invalid or expired'; END IF;
  UPDATE public.auth_mfa_completion_tokens SET status = 'used', used_at = clock_timestamp()
  WHERE token_hash = p_completion_token_hash AND status = 'pending';
  UPDATE public.auth_mfa_challenges SET status = 'consumed', consumed_at = clock_timestamp()
  WHERE id = v_challenge_id AND status = 'verified';
  RETURN QUERY SELECT a.id, a.role, a.authz_version, v_method
  FROM public.auth_accounts a WHERE a.id = v_account_id AND a.disabled_at IS NULL;
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
