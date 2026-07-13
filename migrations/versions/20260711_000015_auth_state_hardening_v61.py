"""Add database-authoritative V6.1 MFA state transitions.

This revision is additive.  The original V6.1 functions remain available for
mixed-version rollback, while new consumers use the purpose-bound contracts
defined here.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260711_000015"
down_revision = "20260710_000014"
branch_labels = None
depends_on = None


_FUNCTION_SIGNATURES = (
    "public.begin_mfa_challenge_v61(uuid, text, timestamp with time zone)",
    "public.mfa_enrollment_challenge_available_v61(uuid, text)",
    "public.begin_totp_enrollment_v61(uuid, uuid, text, text, integer, timestamp with time zone, text)",
    "public.record_totp_attempt_v61(uuid, text, uuid, boolean, bigint, text, timestamp with time zone)",
    "public.complete_totp_enrollment_v61(uuid, text, uuid, boolean, bigint, jsonb, text, timestamp with time zone)",
    "public.begin_email_recovery_challenge_v61(uuid, text, text, timestamp with time zone, text, text, text)",
    "public.consume_email_otp_for_recovery_v61(uuid, text)",
    "public.consume_backup_code_for_recovery_v61(uuid, uuid, text, timestamp with time zone)",
    "public.consume_mfa_completion_token_v61(text)",
    "public.consume_mfa_recovery_completion_token_v61(text)",
    "public.preflight_password_token_v61(text, text)",
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
    op.add_column(
        "auth_mfa_completion_tokens",
        sa.Column("handoff_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "auth_mfa_completion_tokens",
        sa.Column("retry_until", sa.DateTime(timezone=True)),
    )
    op.create_check_constraint(
        "ck_auth_mfa_completion_handoff_attempts",
        "auth_mfa_completion_tokens",
        "handoff_attempts BETWEEN 0 AND 2",
    )
    op.create_check_constraint(
        "ck_auth_mfa_verified_method_v61",
        "auth_mfa_challenges",
        "verified_method IS NULL OR verified_method IN ('totp', 'backup_code', 'email_otp')",
    )

    op.execute(
        sa.text(
            """
CREATE FUNCTION public.begin_mfa_challenge_v61(
  p_account_id uuid,
  p_preauth_handle_hash text,
  p_expires_at timestamptz
) RETURNS TABLE(challenge_id uuid, purpose text, expires_at timestamptz)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_purpose text;
  v_id uuid;
  v_expires timestamptz;
BEGIN
  IF p_preauth_handle_hash !~ '^[a-f0-9]{64}$'
     OR p_expires_at <= clock_timestamp()
     OR p_expires_at > clock_timestamp() + interval '15 minutes' THEN
    RAISE EXCEPTION 'invalid challenge';
  END IF;

  SELECT CASE WHEN EXISTS (
      SELECT 1 FROM public.auth_mfa_factors f
      WHERE f.account_id = a.id AND f.factor_type = 'totp' AND f.status = 'active'
    ) THEN 'login_mfa' ELSE 'mfa_enrollment' END
  INTO v_purpose
  FROM public.auth_accounts a
  WHERE a.id = p_account_id
    AND a.disabled_at IS NULL
    AND a.mfa_required = true
    AND a.role IN ('ADMIN', 'ANALYST')
  FOR UPDATE;

  IF v_purpose IS NULL THEN
    RAISE EXCEPTION 'account is not eligible for MFA';
  END IF;

  UPDATE public.auth_mfa_challenges AS c
  SET status = 'expired', used_at = clock_timestamp()
  WHERE c.account_id = p_account_id
    AND c.status = 'pending'
    AND c.purpose IN ('login_mfa', 'mfa_enrollment', 'recent_reauthentication');

  INSERT INTO public.auth_mfa_challenges (
    account_id, challenge_hash, purpose, preauth_handle_hash, status, expires_at
  ) VALUES (
    p_account_id, p_preauth_handle_hash, v_purpose, p_preauth_handle_hash,
    'pending', p_expires_at
  ) RETURNING id, auth_mfa_challenges.expires_at
  INTO v_id, v_expires;

  RETURN QUERY SELECT v_id, v_purpose, v_expires;
END
$$;

CREATE FUNCTION public.mfa_enrollment_challenge_available_v61(
  p_account_id uuid,
  p_preauth_handle_hash text
) RETURNS boolean
LANGUAGE sql SECURITY INVOKER SET search_path = '' AS $$
SELECT EXISTS (
  SELECT 1
  FROM public.auth_accounts a
  JOIN public.auth_mfa_challenges c ON c.account_id = a.id
  WHERE a.id = p_account_id
    AND a.disabled_at IS NULL
    AND a.mfa_required = true
    AND a.role IN ('ADMIN', 'ANALYST')
    AND NOT EXISTS (
      SELECT 1 FROM public.auth_mfa_factors f
      WHERE f.account_id = a.id AND f.factor_type = 'totp' AND f.status = 'active'
    )
    AND c.purpose = 'mfa_enrollment'
    AND c.preauth_handle_hash = p_preauth_handle_hash
    AND c.status = 'pending'
    AND c.expires_at > clock_timestamp()
    AND c.attempt_count < c.max_attempts
)
$$;

CREATE FUNCTION public.begin_totp_enrollment_v61(
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
  v_challenge_id uuid;
  v_factor_id uuid;
BEGIN
  IF p_expires_at <= clock_timestamp()
     OR char_length(p_ciphertext) < 16
     OR char_length(p_nonce) < 8
     OR p_preauth_handle_hash !~ '^[a-f0-9]{64}$' THEN
    RAISE EXCEPTION 'invalid enrollment';
  END IF;

  SELECT c.id INTO v_challenge_id
  FROM public.auth_mfa_challenges c
  JOIN public.auth_accounts a ON a.id = c.account_id
  WHERE c.account_id = p_account_id
    AND c.preauth_handle_hash = p_preauth_handle_hash
    AND c.purpose = 'mfa_enrollment'
    AND c.status = 'pending'
    AND c.expires_at > clock_timestamp()
    AND a.disabled_at IS NULL
    AND a.mfa_required = true
  FOR UPDATE OF c, a;

  IF v_challenge_id IS NULL THEN
    RAISE EXCEPTION 'enrollment challenge is invalid or expired';
  END IF;
  IF EXISTS (
    SELECT 1 FROM public.auth_mfa_factors
    WHERE account_id = p_account_id AND factor_type = 'totp' AND status = 'active'
  ) THEN
    RAISE EXCEPTION 'active factor exists';
  END IF;

  UPDATE public.auth_mfa_factors
  SET status = 'revoked', revoked_at = clock_timestamp()
  WHERE account_id = p_account_id AND factor_type = 'totp' AND status = 'pending';

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

CREATE FUNCTION public.record_totp_attempt_v61(
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
  FROM public.auth_mfa_challenges c
  JOIN public.auth_accounts a ON a.id = c.account_id
  WHERE c.account_id = p_account_id
    AND c.preauth_handle_hash = p_preauth_handle_hash
    AND c.purpose = 'login_mfa'
    AND a.disabled_at IS NULL
  ORDER BY c.created_at DESC
  LIMIT 1
  FOR UPDATE OF c, a;

  IF v_challenge_id IS NULL OR v_status IN ('expired', 'locked') THEN
    RETURN QUERY SELECT CASE WHEN v_status = 'locked' THEN 'locked' ELSE 'expired' END;
    RETURN;
  END IF;
  IF v_status <> 'pending' OR v_expires_at <= clock_timestamp() THEN
    UPDATE public.auth_mfa_challenges
    SET status = 'expired', used_at = clock_timestamp()
    WHERE id = v_challenge_id AND status = 'pending';
    RETURN QUERY SELECT 'expired';
    RETURN;
  END IF;

  v_attempt := v_attempt + 1;
  UPDATE public.auth_mfa_challenges
  SET attempt_count = v_attempt,
      status = CASE WHEN v_attempt >= v_max_attempts AND NOT p_is_valid THEN 'locked' ELSE status END
  WHERE id = v_challenge_id;

  IF NOT p_is_valid THEN
    RETURN QUERY SELECT CASE WHEN v_attempt >= v_max_attempts THEN 'locked' ELSE 'invalid' END;
    RETURN;
  END IF;
  IF p_time_step IS NULL OR p_completion_token_hash IS NULL
     OR p_completion_token_hash !~ '^[a-f0-9]{64}$'
     OR p_completion_expires_at IS NULL
     OR p_completion_expires_at <= clock_timestamp() THEN
    RAISE EXCEPTION 'invalid completion token';
  END IF;

  UPDATE public.auth_mfa_factors
  SET last_used_time_step = p_time_step
  WHERE id = p_factor_id AND account_id = p_account_id AND factor_type = 'totp'
    AND status = 'active'
    AND (last_used_time_step IS NULL OR p_time_step > last_used_time_step);
  IF NOT FOUND THEN
    RETURN QUERY SELECT CASE WHEN v_attempt >= v_max_attempts THEN 'locked' ELSE 'invalid' END;
    RETURN;
  END IF;

  INSERT INTO public.auth_mfa_completion_tokens (
    account_id, mfa_challenge_id, token_hash, status, expires_at
  ) VALUES (
    p_account_id, v_challenge_id, p_completion_token_hash, 'pending', p_completion_expires_at
  );
  UPDATE public.auth_mfa_challenges
  SET status = 'verified', verified_method = 'totp', verified_at = clock_timestamp(),
      completion_token_hash = p_completion_token_hash,
      completion_expires_at = p_completion_expires_at
  WHERE id = v_challenge_id;
  RETURN QUERY SELECT 'verified';
END
$$;

CREATE FUNCTION public.complete_totp_enrollment_v61(
  p_account_id uuid,
  p_preauth_handle_hash text,
  p_factor_id uuid,
  p_is_valid boolean,
  p_time_step bigint,
  p_backup_codes jsonb,
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
  v_email text;
  v_event uuid;
  v_code jsonb;
BEGIN
  SELECT c.id, c.attempt_count, c.max_attempts, c.status, c.expires_at, a.email
  INTO v_challenge_id, v_attempt, v_max_attempts, v_status, v_expires_at, v_email
  FROM public.auth_mfa_challenges c
  JOIN public.auth_accounts a ON a.id = c.account_id
  JOIN public.auth_mfa_factors f ON f.account_id = a.id AND f.id = p_factor_id
  WHERE c.account_id = p_account_id
    AND c.preauth_handle_hash = p_preauth_handle_hash
    AND c.purpose = 'mfa_enrollment'
    AND f.status = 'pending'
    AND a.disabled_at IS NULL
  ORDER BY c.created_at DESC
  LIMIT 1
  FOR UPDATE OF c, f, a;

  IF v_challenge_id IS NULL OR v_status IN ('expired', 'locked') THEN
    RETURN QUERY SELECT CASE WHEN v_status = 'locked' THEN 'locked' ELSE 'expired' END;
    RETURN;
  END IF;
  IF v_status <> 'pending' OR v_expires_at <= clock_timestamp() THEN
    UPDATE public.auth_mfa_challenges
    SET status = 'expired', used_at = clock_timestamp()
    WHERE id = v_challenge_id AND status = 'pending';
    RETURN QUERY SELECT 'expired';
    RETURN;
  END IF;

  v_attempt := v_attempt + 1;
  UPDATE public.auth_mfa_challenges
  SET attempt_count = v_attempt,
      status = CASE WHEN v_attempt >= v_max_attempts AND NOT p_is_valid THEN 'locked' ELSE status END
  WHERE id = v_challenge_id;

  IF NOT p_is_valid THEN
    RETURN QUERY SELECT CASE WHEN v_attempt >= v_max_attempts THEN 'locked' ELSE 'invalid' END;
    RETURN;
  END IF;
  IF p_time_step IS NULL OR p_completion_token_hash IS NULL
     OR p_completion_token_hash !~ '^[a-f0-9]{64}$'
     OR p_completion_expires_at IS NULL
     OR p_completion_expires_at <= clock_timestamp()
     OR jsonb_typeof(p_backup_codes) <> 'array'
     OR jsonb_array_length(p_backup_codes) <> 8 THEN
    RAISE EXCEPTION 'invalid enrollment completion';
  END IF;

  UPDATE public.auth_mfa_factors
  SET status = 'active', activated_at = clock_timestamp(), last_used_time_step = p_time_step,
      expires_at = NULL
  WHERE id = p_factor_id AND account_id = p_account_id AND factor_type = 'totp'
    AND status = 'pending' AND expires_at > clock_timestamp();
  IF NOT FOUND THEN
    RETURN QUERY SELECT 'invalid';
    RETURN;
  END IF;
  IF EXISTS (
    SELECT 1 FROM public.auth_mfa_factors
    WHERE account_id = p_account_id AND factor_type = 'totp'
      AND status = 'active' AND id <> p_factor_id
  ) THEN
    RAISE EXCEPTION 'active factor exists';
  END IF;

  DELETE FROM public.auth_backup_codes
  WHERE account_id = p_account_id AND used_at IS NULL AND revoked_at IS NULL;
  FOR v_code IN SELECT value FROM jsonb_array_elements(p_backup_codes)
  LOOP
    IF v_code->>'lookup_prefix' IS NULL
       OR v_code->>'code_hash' IS NULL
       OR (v_code->>'code_hash') NOT LIKE '$argon2id$%' THEN
      RAISE EXCEPTION 'invalid backup code material';
    END IF;
    INSERT INTO public.auth_backup_codes (account_id, lookup_prefix, code_hash)
    VALUES (p_account_id, v_code->>'lookup_prefix', v_code->>'code_hash');
  END LOOP;

  INSERT INTO public.auth_mfa_completion_tokens (
    account_id, mfa_challenge_id, token_hash, status, expires_at
  ) VALUES (
    p_account_id, v_challenge_id, p_completion_token_hash, 'pending', p_completion_expires_at
  );
  UPDATE public.auth_mfa_challenges
  SET status = 'verified', verified_method = 'totp', verified_at = clock_timestamp(),
      completion_token_hash = p_completion_token_hash,
      completion_expires_at = p_completion_expires_at
  WHERE id = v_challenge_id;
  UPDATE public.auth_accounts
  SET authz_version = authz_version + 1
  WHERE id = p_account_id;
  INSERT INTO public.security_events (
    source, event_type, severity, outcome, account_id, safe_summary_json
  ) VALUES (
    'auth', 'auth.totp_enrolled', 'medium', 'success', p_account_id,
    jsonb_build_object('factor_type', 'totp')
  ) RETURNING id INTO v_event;
  INSERT INTO public.notification_outbox (
    event_id, dedupe_key, channel, recipient, kind, template_version,
    provider_idempotency_key, payload_safe_json
  ) VALUES (
    v_event, 'totp-enrolled/' || p_factor_id::text, 'email', v_email,
    'totp_enrolled', 1, 'totp-enrolled/' || p_factor_id::text, '{}'::jsonb
  );
  RETURN QUERY SELECT 'verified';
END
$$;

CREATE FUNCTION public.begin_email_recovery_challenge_v61(
  p_account_id uuid,
  p_otp_digest text,
  p_completion_token_hash text,
  p_expires_at timestamptz,
  p_otp text,
  p_dedupe_key text,
  p_provider_idempotency_key text
) RETURNS TABLE(status text)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_email text;
  v_challenge_id uuid;
BEGIN
  IF p_otp_digest !~ '^[a-f0-9]{64}$'
     OR p_completion_token_hash !~ '^[a-f0-9]{64}$'
     OR p_expires_at <= clock_timestamp()
     OR p_otp !~ '^[0-9]{6}$' THEN
    RAISE EXCEPTION 'invalid recovery challenge';
  END IF;
  SELECT a.email INTO v_email
  FROM public.auth_accounts a
  WHERE a.id = p_account_id AND a.disabled_at IS NULL
    AND a.email_verified_at IS NOT NULL AND a.role IN ('ADMIN', 'ANALYST')
  FOR UPDATE;
  IF v_email IS NULL THEN RAISE EXCEPTION 'recovery is unavailable'; END IF;
  IF EXISTS (
    SELECT 1 FROM public.auth_email_otp_challenges e
    WHERE e.account_id = p_account_id AND e.status = 'pending'
      AND e.created_at > clock_timestamp() - interval '60 seconds'
  ) THEN
    RAISE EXCEPTION 'recovery resend cooldown';
  END IF;

  UPDATE public.auth_email_otp_challenges AS e
  SET status = 'expired', used_at = clock_timestamp()
  WHERE e.account_id = p_account_id AND e.status = 'pending';
  UPDATE public.auth_mfa_challenges AS c
  SET status = 'expired', used_at = clock_timestamp()
  WHERE c.account_id = p_account_id AND c.purpose = 'mfa_recovery' AND c.status = 'pending';
  UPDATE public.auth_mfa_completion_tokens AS t
  SET status = 'expired'
  WHERE t.account_id = p_account_id AND t.status = 'pending';
  UPDATE public.notification_outbox AS n
  SET status = 'permanent_failure', last_error_class = 'superseded'
  WHERE n.recipient = v_email AND n.kind = 'email_recovery_otp'
    AND n.status IN ('pending', 'retry_wait');

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
  INSERT INTO public.notification_outbox (
    channel, recipient, kind, template_version, dedupe_key,
    provider_idempotency_key, payload_safe_json
  ) VALUES (
    'email', v_email, 'email_recovery_otp', 1, p_dedupe_key,
    p_provider_idempotency_key, jsonb_build_object('otp', p_otp)
  );
  RETURN QUERY SELECT 'sent';
END
$$;

CREATE FUNCTION public.consume_email_otp_for_recovery_v61(
  p_account_id uuid,
  p_otp_digest text
) RETURNS TABLE(outcome text)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_id uuid;
  v_challenge_id uuid;
  v_email text;
  v_code_hash text;
  v_token_hash text;
  v_completion_expires timestamptz;
  v_otp_expires timestamptz;
  v_attempt integer;
  v_max_attempts integer;
  v_event uuid;
BEGIN
  SELECT e.id, e.mfa_challenge_id, e.email_to, e.code_hash,
         e.attempt_count, e.max_attempts, c.completion_token_hash, c.completion_expires_at,
         e.expires_at
  INTO v_id, v_challenge_id, v_email, v_code_hash,
       v_attempt, v_max_attempts, v_token_hash, v_completion_expires, v_otp_expires
  FROM public.auth_email_otp_challenges e
  JOIN public.auth_mfa_challenges c ON c.id = e.mfa_challenge_id
  JOIN public.auth_accounts a ON a.id = e.account_id
  WHERE e.account_id = p_account_id AND e.status = 'pending'
  ORDER BY e.created_at DESC
  LIMIT 1
  FOR UPDATE OF e, c, a;

  IF v_id IS NULL THEN
    RETURN QUERY SELECT 'expired';
    RETURN;
  END IF;
  IF v_otp_expires <= clock_timestamp() THEN
    UPDATE public.auth_email_otp_challenges SET status = 'expired', used_at = clock_timestamp()
    WHERE id = v_id;
    UPDATE public.auth_mfa_challenges SET status = 'expired', used_at = clock_timestamp()
    WHERE id = v_challenge_id AND status = 'pending';
    RETURN QUERY SELECT 'expired';
    RETURN;
  END IF;

  v_attempt := v_attempt + 1;
  IF p_otp_digest IS NULL OR p_otp_digest <> v_code_hash THEN
    UPDATE public.auth_email_otp_challenges
    SET attempt_count = v_attempt,
        status = CASE WHEN v_attempt >= v_max_attempts THEN 'locked' ELSE 'pending' END
    WHERE id = v_id;
    RETURN QUERY SELECT CASE WHEN v_attempt >= v_max_attempts THEN 'locked' ELSE 'invalid' END;
    RETURN;
  END IF;

  UPDATE public.auth_email_otp_challenges
  SET status = 'used', used_at = clock_timestamp(), attempt_count = v_attempt
  WHERE id = v_id;
  UPDATE public.auth_mfa_factors SET status = 'revoked', revoked_at = clock_timestamp()
  WHERE account_id = p_account_id AND factor_type = 'totp' AND status = 'active';
  UPDATE public.auth_backup_codes SET revoked_at = clock_timestamp()
  WHERE account_id = p_account_id AND used_at IS NULL AND revoked_at IS NULL;
  UPDATE public.auth_mfa_challenges SET status = 'expired', used_at = clock_timestamp()
  WHERE account_id = p_account_id AND status IN ('pending', 'verified') AND id <> v_challenge_id;
  UPDATE public.auth_mfa_completion_tokens SET status = 'expired'
  WHERE account_id = p_account_id AND status = 'pending';
  INSERT INTO public.auth_mfa_completion_tokens (
    account_id, mfa_challenge_id, token_hash, status, expires_at
  ) VALUES (p_account_id, v_challenge_id, v_token_hash, 'pending', v_completion_expires);
  UPDATE public.auth_mfa_challenges
  SET status = 'verified', verified_method = 'email_otp', verified_at = clock_timestamp()
  WHERE id = v_challenge_id;
  UPDATE public.auth_accounts SET authz_version = authz_version + 1 WHERE id = p_account_id;
  INSERT INTO public.security_events (
    source, event_type, severity, outcome, account_id, safe_summary_json
  ) VALUES (
    'auth', 'auth.email_recovery_completed', 'high', 'success', p_account_id,
    jsonb_build_object('method', 'email_otp')
  ) RETURNING id INTO v_event;
  INSERT INTO public.notification_outbox (
    event_id, dedupe_key, channel, recipient, kind, template_version,
    provider_idempotency_key, payload_safe_json
  ) VALUES (
    v_event, 'email-recovery-completed/' || v_challenge_id::text, 'email', v_email,
    'email_recovery_completed', 1, 'email-recovery-completed/' || v_challenge_id::text, '{}'::jsonb
  );
  RETURN QUERY SELECT 'verified';
END
$$;

CREATE FUNCTION public.consume_backup_code_for_recovery_v61(
  p_account_id uuid,
  p_code_id uuid,
  p_completion_token_hash text,
  p_completion_expires_at timestamptz
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_email text;
  v_challenge_id uuid;
  v_event uuid;
BEGIN
  IF p_completion_token_hash !~ '^[a-f0-9]{64}$'
     OR p_completion_expires_at <= clock_timestamp() THEN
    RAISE EXCEPTION 'invalid recovery token';
  END IF;
  SELECT email INTO v_email FROM public.auth_accounts
  WHERE id = p_account_id AND disabled_at IS NULL
    AND password_hash IS NOT NULL AND role IN ('ADMIN', 'ANALYST')
  FOR UPDATE;
  IF v_email IS NULL THEN RAISE EXCEPTION 'recovery is unavailable'; END IF;
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
    p_account_id, p_completion_token_hash, 'mfa_recovery', 'verified',
    p_completion_expires_at, 'backup_code', clock_timestamp(),
    p_completion_token_hash, p_completion_expires_at
  ) RETURNING id INTO v_challenge_id;
  INSERT INTO public.auth_mfa_completion_tokens (
    account_id, mfa_challenge_id, token_hash, status, expires_at
  ) VALUES (p_account_id, v_challenge_id, p_completion_token_hash, 'pending', p_completion_expires_at);
  UPDATE public.auth_accounts SET authz_version = authz_version + 1 WHERE id = p_account_id;
  INSERT INTO public.security_events (
    source, event_type, severity, outcome, account_id, safe_summary_json
  ) VALUES (
    'auth', 'auth.backup_code_used', 'high', 'success', p_account_id,
    jsonb_build_object('method', 'backup_code', 'recovery', true)
  ) RETURNING id INTO v_event;
  INSERT INTO public.notification_outbox (
    event_id, dedupe_key, channel, recipient, kind, template_version,
    provider_idempotency_key, payload_safe_json
  ) VALUES (
    v_event, 'backup-recovery/' || p_code_id::text, 'email', v_email,
    'backup_code_used', 1, 'backup-recovery/' || p_code_id::text, '{}'::jsonb
  );
  RETURN true;
END
$$;

CREATE FUNCTION public.consume_mfa_completion_token_v61(
  p_completion_token_hash text
) RETURNS TABLE(
  account_id uuid, name text, email text, role text, authz_version integer,
  auth_level text, auth_method text, verified_at timestamptz, completion_purpose text
)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_account_id uuid;
  v_challenge_id uuid;
  v_status text;
  v_handoff_attempts integer;
  v_retry_until timestamptz;
  v_purpose text;
  v_method text;
  v_verified_at timestamptz;
BEGIN
  IF p_completion_token_hash !~ '^[a-f0-9]{64}$' THEN
    RAISE EXCEPTION 'completion token is invalid or expired';
  END IF;
  SELECT t.account_id, t.mfa_challenge_id, t.status, t.handoff_attempts, t.retry_until,
         c.purpose, c.verified_method, c.verified_at
  INTO v_account_id, v_challenge_id, v_status, v_handoff_attempts, v_retry_until,
       v_purpose, v_method, v_verified_at
  FROM public.auth_mfa_completion_tokens t
  JOIN public.auth_mfa_challenges c ON c.id = t.mfa_challenge_id
  JOIN public.auth_accounts a ON a.id = t.account_id
  WHERE t.token_hash = p_completion_token_hash
    AND t.expires_at > clock_timestamp()
    AND c.completion_expires_at > clock_timestamp()
    AND c.purpose IN ('login_mfa', 'mfa_enrollment', 'recent_reauthentication')
    AND c.verified_method = 'totp'
    AND c.status IN ('verified', 'consumed')
    AND a.disabled_at IS NULL
  FOR UPDATE OF t, c, a;
  IF v_account_id IS NULL OR v_verified_at IS NULL THEN
    RAISE EXCEPTION 'completion token is invalid or expired';
  END IF;
  IF v_status = 'pending' AND v_handoff_attempts = 0 THEN
    UPDATE public.auth_mfa_completion_tokens
    SET status = 'used', used_at = clock_timestamp(), handoff_attempts = 1,
        retry_until = LEAST(expires_at, clock_timestamp() + interval '30 seconds')
    WHERE token_hash = p_completion_token_hash;
    UPDATE public.auth_mfa_challenges
    SET status = 'consumed', consumed_at = clock_timestamp()
    WHERE id = v_challenge_id AND status = 'verified';
  ELSIF v_status = 'used' AND v_handoff_attempts = 1
        AND v_retry_until IS NOT NULL AND v_retry_until > clock_timestamp() THEN
    UPDATE public.auth_mfa_completion_tokens
    SET handoff_attempts = 2, retry_until = NULL
    WHERE token_hash = p_completion_token_hash;
  ELSE
    RAISE EXCEPTION 'completion token is no longer usable';
  END IF;
  RETURN QUERY
  SELECT a.id, a.name, a.email, a.role, a.authz_version,
         'mfa', v_method, v_verified_at, v_purpose
  FROM public.auth_accounts a
  WHERE a.id = v_account_id AND a.disabled_at IS NULL;
END
$$;

CREATE FUNCTION public.consume_mfa_recovery_completion_token_v61(
  p_completion_token_hash text
) RETURNS TABLE(
  account_id uuid, name text, email text, role text, authz_version integer,
  auth_level text, auth_method text, verified_at timestamptz, completion_purpose text
)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_account_id uuid;
  v_challenge_id uuid;
  v_status text;
  v_handoff_attempts integer;
  v_retry_until timestamptz;
  v_method text;
  v_verified_at timestamptz;
BEGIN
  IF p_completion_token_hash !~ '^[a-f0-9]{64}$' THEN
    RAISE EXCEPTION 'recovery completion is invalid or expired';
  END IF;
  SELECT t.account_id, t.mfa_challenge_id, t.status, t.handoff_attempts, t.retry_until,
         c.verified_method, c.verified_at
  INTO v_account_id, v_challenge_id, v_status, v_handoff_attempts, v_retry_until,
       v_method, v_verified_at
  FROM public.auth_mfa_completion_tokens t
  JOIN public.auth_mfa_challenges c ON c.id = t.mfa_challenge_id
  JOIN public.auth_accounts a ON a.id = t.account_id
  WHERE t.token_hash = p_completion_token_hash
    AND t.expires_at > clock_timestamp()
    AND c.completion_expires_at > clock_timestamp()
    AND c.purpose = 'mfa_recovery'
    AND c.verified_method IN ('backup_code', 'email_otp')
    AND c.status IN ('verified', 'consumed')
    AND a.disabled_at IS NULL
  FOR UPDATE OF t, c, a;
  IF v_account_id IS NULL OR v_verified_at IS NULL THEN
    RAISE EXCEPTION 'recovery completion is invalid or expired';
  END IF;
  IF v_status = 'pending' AND v_handoff_attempts = 0 THEN
    UPDATE public.auth_mfa_completion_tokens
    SET status = 'used', used_at = clock_timestamp(), handoff_attempts = 1,
        retry_until = LEAST(expires_at, clock_timestamp() + interval '30 seconds')
    WHERE token_hash = p_completion_token_hash;
    UPDATE public.auth_mfa_challenges
    SET status = 'consumed', consumed_at = clock_timestamp()
    WHERE id = v_challenge_id AND status = 'verified';
  ELSIF v_status = 'used' AND v_handoff_attempts = 1
        AND v_retry_until IS NOT NULL AND v_retry_until > clock_timestamp() THEN
    UPDATE public.auth_mfa_completion_tokens
    SET handoff_attempts = 2, retry_until = NULL
    WHERE token_hash = p_completion_token_hash;
  ELSE
    RAISE EXCEPTION 'recovery completion is no longer usable';
  END IF;
  RETURN QUERY
  SELECT a.id, a.name, a.email, a.role, a.authz_version,
         'recovery', v_method, v_verified_at, 'mfa_recovery'
  FROM public.auth_accounts a
  WHERE a.id = v_account_id AND a.disabled_at IS NULL;
END
$$;

CREATE FUNCTION public.preflight_password_token_v61(
  p_token_hash text,
  p_purpose text
) RETURNS boolean
LANGUAGE sql SECURITY INVOKER SET search_path = '' AS $$
SELECT EXISTS (
  SELECT 1
  FROM public.auth_reset_tokens t
  JOIN public.auth_accounts a ON a.id = t.account_id
  WHERE t.token_hash = p_token_hash
    AND t.purpose = p_purpose
    AND t.status = 'pending'
    AND t.used_at IS NULL
    AND t.expires_at > clock_timestamp()
    AND a.disabled_at IS NULL
    AND (
      (p_purpose = 'password_setup' AND a.password_hash IS NULL)
      OR
      (p_purpose = 'password_reset' AND a.email_verified_at IS NOT NULL)
    )
)
$$;
"""
        )
    )
    for signature in _FUNCTION_SIGNATURES:
        _restrict(signature)


def downgrade() -> None:
    for signature in reversed(_FUNCTION_SIGNATURES):
        op.execute(sa.text(f"DROP FUNCTION IF EXISTS {signature}"))
    op.drop_constraint(
        "ck_auth_mfa_verified_method_v61", "auth_mfa_challenges", type_="check"
    )
    op.drop_constraint(
        "ck_auth_mfa_completion_handoff_attempts",
        "auth_mfa_completion_tokens",
        type_="check",
    )
    op.drop_column("auth_mfa_completion_tokens", "retry_until")
    op.drop_column("auth_mfa_completion_tokens", "handoff_attempts")
