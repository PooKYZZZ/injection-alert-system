"""Add purpose-specific recent-TOTP and recovery enrollment contracts."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260711_000017"
down_revision = "20260711_000016"
branch_labels = None
depends_on = None


_FUNCTION_SIGNATURES = (
    "public.begin_recent_totp_challenge_v61(uuid, text, timestamp with time zone)",
    "public.record_recent_totp_attempt_v61(uuid, text, uuid, boolean, bigint, text, timestamp with time zone)",
    "public.begin_recovery_totp_enrollment_v61(uuid, uuid, text, text, integer, timestamp with time zone, text)",
)


def _restrict_function(signature: str) -> None:
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
CREATE FUNCTION public.begin_recent_totp_challenge_v61(
  p_account_id uuid,
  p_preauth_handle_hash text,
  p_expires_at timestamptz
) RETURNS TABLE(challenge_id uuid, purpose text, expires_at timestamptz)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_id uuid;
  v_expires timestamptz;
BEGIN
  IF p_preauth_handle_hash !~ '^[a-f0-9]{64}$'
     OR p_expires_at <= clock_timestamp()
     OR p_expires_at > clock_timestamp() + interval '15 minutes' THEN
    RAISE EXCEPTION 'invalid step-up challenge';
  END IF;
  IF NOT EXISTS (
    SELECT 1
    FROM public.auth_accounts AS a
    JOIN public.auth_mfa_factors AS f ON f.account_id = a.id
    WHERE a.id = p_account_id
      AND a.role = 'ADMIN'
      AND a.mfa_required = true
      AND a.disabled_at IS NULL
      AND f.factor_type = 'totp'
      AND f.status = 'active'
  ) THEN
    RAISE EXCEPTION 'step-up is unavailable';
  END IF;

  UPDATE public.auth_mfa_challenges AS c
  SET status = 'expired', used_at = clock_timestamp()
  WHERE c.account_id = p_account_id
    AND c.purpose = 'recent_reauthentication'
    AND c.status = 'pending';

  INSERT INTO public.auth_mfa_challenges (
    account_id, challenge_hash, purpose, preauth_handle_hash, status, expires_at
  ) VALUES (
    p_account_id, p_preauth_handle_hash, 'recent_reauthentication',
    p_preauth_handle_hash, 'pending', p_expires_at
  ) RETURNING id, auth_mfa_challenges.expires_at INTO v_id, v_expires;
  RETURN QUERY SELECT v_id, 'recent_reauthentication', v_expires;
END
$$;

CREATE FUNCTION public.record_recent_totp_attempt_v61(
  p_account_id uuid,
  p_preauth_handle_hash text,
  p_factor_id uuid,
  p_is_valid boolean,
  p_time_step bigint,
  p_completion_token_hash text,
  p_completion_expires_at timestamptz
) RETURNS TABLE(outcome text)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_challenge_id uuid;
  v_attempt integer;
  v_max_attempts integer;
  v_status text;
  v_expires_at timestamptz;
BEGIN
  SELECT c.id, c.attempt_count, c.max_attempts, c.status, c.expires_at
  INTO v_challenge_id, v_attempt, v_max_attempts, v_status, v_expires_at
  FROM public.auth_mfa_challenges AS c
  JOIN public.auth_accounts AS a ON a.id = c.account_id
  WHERE c.account_id = p_account_id
    AND c.preauth_handle_hash = p_preauth_handle_hash
    AND c.purpose = 'recent_reauthentication'
    AND a.disabled_at IS NULL
  ORDER BY c.created_at DESC
  LIMIT 1
  FOR UPDATE OF c, a;

  IF v_challenge_id IS NULL OR v_status IN ('expired', 'locked') THEN
    RETURN QUERY SELECT CASE WHEN v_status = 'locked' THEN 'locked' ELSE 'expired' END;
    RETURN;
  END IF;
  IF v_status <> 'pending' OR v_expires_at <= clock_timestamp() THEN
    UPDATE public.auth_mfa_challenges AS c
    SET status = 'expired', used_at = clock_timestamp()
    WHERE c.id = v_challenge_id AND c.status = 'pending';
    RETURN QUERY SELECT 'expired';
    RETURN;
  END IF;

  v_attempt := v_attempt + 1;
  UPDATE public.auth_mfa_challenges AS c
  SET attempt_count = v_attempt,
      status = CASE WHEN v_attempt >= v_max_attempts AND NOT p_is_valid
                    THEN 'locked' ELSE c.status END
  WHERE c.id = v_challenge_id;
  IF NOT p_is_valid THEN
    RETURN QUERY SELECT CASE WHEN v_attempt >= v_max_attempts THEN 'locked' ELSE 'invalid' END;
    RETURN;
  END IF;
  IF p_time_step IS NULL OR p_completion_token_hash IS NULL
     OR p_completion_token_hash !~ '^[a-f0-9]{64}$'
     OR p_completion_expires_at IS NULL
     OR p_completion_expires_at <= clock_timestamp() THEN
    RAISE EXCEPTION 'invalid step-up completion';
  END IF;
  UPDATE public.auth_mfa_factors AS f
  SET last_used_time_step = p_time_step
  WHERE f.id = p_factor_id AND f.account_id = p_account_id
    AND f.factor_type = 'totp' AND f.status = 'active'
    AND (f.last_used_time_step IS NULL OR p_time_step > f.last_used_time_step);
  IF NOT FOUND THEN
    RETURN QUERY SELECT CASE WHEN v_attempt >= v_max_attempts THEN 'locked' ELSE 'invalid' END;
    RETURN;
  END IF;
  INSERT INTO public.auth_mfa_completion_tokens (
    account_id, mfa_challenge_id, token_hash, status, expires_at
  ) VALUES (p_account_id, v_challenge_id, p_completion_token_hash, 'pending', p_completion_expires_at);
  UPDATE public.auth_mfa_challenges AS c
  SET status = 'verified', verified_method = 'totp', verified_at = clock_timestamp(),
      completion_token_hash = p_completion_token_hash,
      completion_expires_at = p_completion_expires_at
  WHERE c.id = v_challenge_id;
  RETURN QUERY SELECT 'verified';
END
$$;

CREATE FUNCTION public.begin_recovery_totp_enrollment_v61(
  p_account_id uuid,
  p_factor_id uuid,
  p_ciphertext text,
  p_nonce text,
  p_key_version integer,
  p_expires_at timestamptz,
  p_preauth_handle_hash text
) RETURNS uuid
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_recovery_id uuid;
  v_challenge_id uuid;
  v_factor_id uuid;
BEGIN
  IF p_expires_at <= clock_timestamp()
     OR char_length(p_ciphertext) < 16
     OR char_length(p_nonce) < 8
     OR p_preauth_handle_hash !~ '^[a-f0-9]{64}$' THEN
    RAISE EXCEPTION 'invalid recovery enrollment';
  END IF;
  SELECT c.id INTO v_recovery_id
  FROM public.auth_mfa_challenges AS c
  JOIN public.auth_accounts AS a ON a.id = c.account_id
  WHERE c.account_id = p_account_id
    AND c.purpose = 'mfa_recovery'
    AND c.status = 'consumed'
    AND c.verified_method IN ('backup_code', 'email_otp')
    AND c.consumed_at > clock_timestamp() - interval '10 minutes'
    AND c.completion_expires_at > clock_timestamp()
    AND a.disabled_at IS NULL
    AND a.mfa_required = true
    AND a.role IN ('ADMIN', 'ANALYST')
  ORDER BY c.consumed_at DESC
  LIMIT 1
  FOR UPDATE OF c, a;
  IF v_recovery_id IS NULL THEN
    RAISE EXCEPTION 'recovery enrollment is invalid or expired';
  END IF;
  IF EXISTS (
    SELECT 1 FROM public.auth_mfa_factors AS f
    WHERE f.account_id = p_account_id AND f.factor_type = 'totp' AND f.status = 'active'
  ) THEN
    RAISE EXCEPTION 'active factor exists';
  END IF;

  UPDATE public.auth_mfa_factors AS f
  SET status = 'revoked', revoked_at = clock_timestamp()
  WHERE f.account_id = p_account_id AND f.factor_type = 'totp' AND f.status = 'pending';
  INSERT INTO public.auth_mfa_challenges (
    account_id, challenge_hash, purpose, preauth_handle_hash, status, expires_at
  ) VALUES (
    p_account_id, p_preauth_handle_hash, 'mfa_enrollment', p_preauth_handle_hash,
    'pending', p_expires_at
  ) RETURNING id INTO v_challenge_id;
  INSERT INTO public.auth_mfa_factors (
    id, account_id, factor_type, status, secret_ciphertext, secret_nonce,
    secret_key_version, expires_at
  ) VALUES (
    p_factor_id, p_account_id, 'totp', 'pending', p_ciphertext, p_nonce,
    p_key_version, p_expires_at
  ) RETURNING id INTO v_factor_id;
  RETURN v_factor_id;
END
$$;
"""
        )
    )
    for signature in _FUNCTION_SIGNATURES:
        _restrict_function(signature)


def downgrade() -> None:
    for signature in reversed(_FUNCTION_SIGNATURES):
        op.execute(sa.text(f"DROP FUNCTION IF EXISTS {signature}"))
