"""Require protected envelopes for active credential-equivalent notifications."""

# The migration intentionally keeps PostgreSQL function signatures and SQL statements
# intact for operational review. Some SQL source lines exceed the Python line limit.
# ruff: noqa: E501

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260711_000019"
down_revision = "20260711_000018"
branch_labels = None
depends_on = None


PROTECTED_KINDS = (
    "password_setup",
    "password_reset",
    "email_verification",
    "email_recovery_otp",
)

_PROTECTED_FUNCTION_SIGNATURES = (
    "public.admin_create_auth_account_protected_v61(uuid, text, text, text, text, timestamp with time zone, jsonb, text, text)",
    "public.admin_resend_password_setup_protected_v61(uuid, uuid, text, text, timestamp with time zone, jsonb, text, text)",
    "public.admin_request_managed_email_change_protected_v61(uuid, uuid, text, text, timestamp with time zone, jsonb, text, text)",
    "public.create_password_reset_token_protected_v61(uuid, text, timestamp with time zone, jsonb, text, text, text)",
    "public.begin_email_recovery_challenge_protected_v61(uuid, text, text, text, timestamp with time zone, jsonb, text, text)",
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
    protected_sql = ", ".join(f"'{kind}'" for kind in PROTECTED_KINDS)
    op.execute(
        sa.text(
            f"""
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM public.notification_outbox AS o
    WHERE o.kind IN ({protected_sql})
      AND o.status IN ('pending', 'leased', 'retry_wait')
      AND NOT (
        jsonb_typeof(o.payload_safe_json) = 'object'
        AND o.payload_safe_json ?& ARRAY['ciphertext', 'nonce', 'key_version']
        AND o.payload_safe_json - ARRAY['ciphertext', 'nonce', 'key_version'] = '{{}}'::jsonb
        AND o.payload_safe_json->>'ciphertext' ~ '^[A-Za-z0-9_-]+$'
        AND o.payload_safe_json->>'nonce' ~ '^[A-Za-z0-9_-]+$'
        AND o.payload_safe_json->>'key_version' = '1'
      )
  ) THEN
    RAISE EXCEPTION 'active plaintext notification payloads require reviewed remediation';
  END IF;
END
$$;

CREATE OR REPLACE FUNCTION public.notification_outbox_guard_v61()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_deadline timestamptz;
BEGIN
  IF NEW.channel <> 'email' THEN
    RAISE EXCEPTION 'notification channel is unsupported';
  END IF;

  IF NEW.kind = 'legacy_notification' THEN
    NEW.status := 'permanent_failure';
    NEW.last_error_class := COALESCE(NEW.last_error_class, 'unsupported_notification_kind');
  END IF;

  IF TG_OP = 'INSERT' THEN
    IF NEW.kind IN ('password_setup', 'password_reset') THEN
      SELECT max(t.expires_at) INTO v_deadline
      FROM public.auth_reset_tokens AS t
      JOIN public.auth_accounts AS a ON a.id = t.account_id
      WHERE a.email = NEW.recipient
        AND t.purpose = NEW.kind
        AND t.status = 'pending';
    ELSIF NEW.kind = 'email_verification' THEN
      SELECT max(t.expires_at) INTO v_deadline
      FROM public.auth_reset_tokens AS t
      JOIN public.auth_accounts AS a ON a.id = t.account_id
      WHERE a.pending_email = NEW.recipient
        AND t.purpose = 'email_verification'
        AND t.status = 'pending';
    ELSIF NEW.kind = 'email_recovery_otp' THEN
      SELECT max(e.expires_at) INTO v_deadline
      FROM public.auth_email_otp_challenges AS e
      WHERE e.email_to = NEW.recipient AND e.status = 'pending';
    END IF;

    IF v_deadline IS NOT NULL THEN
      NEW.deliver_before := v_deadline;
      IF v_deadline <= clock_timestamp() AND NEW.status IN ('pending', 'retry_wait', 'leased') THEN
        NEW.status := 'expired';
        NEW.last_error_class := 'delivery_deadline_expired';
      END IF;
    END IF;
  END IF;

  IF NEW.status IN ('sent', 'cancelled', 'expired', 'permanent_failure') THEN
    NEW.payload_safe_json := '{{}}'::jsonb;
    NEW.terminalized_at := COALESCE(NEW.terminalized_at, clock_timestamp());
  ELSIF NEW.kind IN ({protected_sql}) AND NOT (
    jsonb_typeof(NEW.payload_safe_json) = 'object'
    AND NEW.payload_safe_json ?& ARRAY['ciphertext', 'nonce', 'key_version']
    AND NEW.payload_safe_json - ARRAY['ciphertext', 'nonce', 'key_version'] = '{{}}'::jsonb
    AND NEW.payload_safe_json->>'ciphertext' ~ '^[A-Za-z0-9_-]+$'
    AND NEW.payload_safe_json->>'nonce' ~ '^[A-Za-z0-9_-]+$'
    AND NEW.payload_safe_json->>'key_version' = '1'
  ) THEN
    RAISE EXCEPTION 'notification payload protection is required';
  END IF;
  RETURN NEW;
END
$$;

CREATE FUNCTION public.admin_create_auth_account_protected_v61(
  p_actor_account_id uuid,
  p_email text,
  p_name text,
  p_role text,
  p_setup_token_hash text,
  p_expires_at timestamptz,
  p_protected_payload jsonb,
  p_dedupe_key text,
  p_provider_idempotency_key text
) RETURNS uuid
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE new_account_id uuid;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.auth_accounts
    WHERE id = p_actor_account_id AND role = 'ADMIN' AND disabled_at IS NULL
  ) THEN RAISE EXCEPTION 'admin authorization failed'; END IF;
  IF p_email IS NULL OR p_email <> lower(btrim(p_email)) OR char_length(p_email) NOT BETWEEN 3 AND 320 THEN
    RAISE EXCEPTION 'invalid email';
  END IF;
  IF p_name IS NULL OR char_length(btrim(p_name)) NOT BETWEEN 1 AND 120 THEN
    RAISE EXCEPTION 'invalid name';
  END IF;
  IF p_role NOT IN ('ADMIN', 'ANALYST', 'VIEWER') THEN RAISE EXCEPTION 'invalid role'; END IF;
  IF p_setup_token_hash !~ '^[a-f0-9]{{64}}$' OR p_expires_at <= clock_timestamp() THEN
    RAISE EXCEPTION 'invalid setup token';
  END IF;

  INSERT INTO public.auth_accounts (
    email, name, role, authz_version, password_hash, password_set_at,
    email_verified_at, mfa_required
  ) VALUES (
    p_email, btrim(p_name), p_role, 1, NULL, NULL, NULL, p_role <> 'VIEWER'
  ) RETURNING id INTO new_account_id;
  INSERT INTO public.auth_reset_tokens (
    account_id, purpose, token_hash, status, expires_at
  ) VALUES (
    new_account_id, 'password_setup', p_setup_token_hash, 'pending', p_expires_at
  );
  INSERT INTO public.security_events (
    source, event_type, severity, outcome, account_id, safe_summary_json
  ) VALUES (
    'auth', 'account_created', 'medium', 'success', new_account_id,
    jsonb_build_object('actor_account_id', p_actor_account_id, 'role', p_role)
  );
  INSERT INTO public.notification_outbox (
    kind, channel, recipient, status, payload_safe_json, template_version,
    dedupe_key, provider_idempotency_key
  ) VALUES (
    'password_setup', 'email', p_email, 'pending', p_protected_payload, 1,
    p_dedupe_key, p_provider_idempotency_key
  );
  RETURN new_account_id;
END
$$;

CREATE FUNCTION public.admin_resend_password_setup_protected_v61(
  p_actor_account_id uuid,
  p_target_account_id uuid,
  p_recipient text,
  p_setup_token_hash text,
  p_expires_at timestamptz,
  p_protected_payload jsonb,
  p_dedupe_key text,
  p_provider_idempotency_key text
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE target_email text;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.auth_accounts
    WHERE id = p_actor_account_id AND role = 'ADMIN' AND disabled_at IS NULL
  ) THEN RAISE EXCEPTION 'admin authorization failed'; END IF;
  SELECT email INTO target_email FROM public.auth_accounts
  WHERE id = p_target_account_id AND disabled_at IS NULL AND password_hash IS NULL
  FOR UPDATE;
  IF target_email IS NULL THEN RAISE EXCEPTION 'account is not eligible'; END IF;
  IF target_email <> p_recipient THEN RAISE EXCEPTION 'recipient changed'; END IF;
  UPDATE public.auth_reset_tokens SET status = 'revoked'
  WHERE account_id = p_target_account_id AND purpose = 'password_setup'
    AND status = 'pending' AND used_at IS NULL;
  INSERT INTO public.auth_reset_tokens (account_id, purpose, token_hash, status, expires_at)
  VALUES (p_target_account_id, 'password_setup', p_setup_token_hash, 'pending', p_expires_at);
  INSERT INTO public.notification_outbox (
    kind, channel, recipient, status, payload_safe_json, template_version,
    dedupe_key, provider_idempotency_key
  ) VALUES (
    'password_setup', 'email', target_email, 'pending', p_protected_payload, 1,
    p_dedupe_key, p_provider_idempotency_key
  );
  RETURN true;
END
$$;

CREATE FUNCTION public.admin_request_managed_email_change_protected_v61(
  p_actor_account_id uuid,
  p_target_account_id uuid,
  p_new_email text,
  p_token_hash text,
  p_expires_at timestamptz,
  p_protected_payload jsonb,
  p_dedupe_key text,
  p_provider_idempotency_key text
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.auth_accounts
    WHERE id = p_actor_account_id AND role = 'ADMIN' AND disabled_at IS NULL
  ) THEN RAISE EXCEPTION 'admin authorization failed'; END IF;
  IF p_new_email IS NULL OR p_new_email <> lower(btrim(p_new_email)) OR char_length(p_new_email) NOT BETWEEN 3 AND 320 THEN
    RAISE EXCEPTION 'invalid email';
  END IF;
  IF EXISTS (
    SELECT 1 FROM public.auth_accounts
    WHERE lower(email) = p_new_email
       OR (pending_email IS NOT NULL AND lower(pending_email) = p_new_email)
  ) THEN RAISE EXCEPTION 'email already in use'; END IF;
  IF p_token_hash !~ '^[a-f0-9]{{64}}$' OR p_expires_at <= clock_timestamp() THEN
    RAISE EXCEPTION 'invalid token';
  END IF;
  UPDATE public.auth_accounts
  SET pending_email = p_new_email, pending_email_requested_at = clock_timestamp()
  WHERE id = p_target_account_id AND disabled_at IS NULL;
  IF NOT FOUND THEN RAISE EXCEPTION 'account not found'; END IF;
  UPDATE public.auth_reset_tokens SET status = 'revoked'
  WHERE account_id = p_target_account_id AND purpose = 'email_verification'
    AND status = 'pending' AND used_at IS NULL;
  INSERT INTO public.auth_reset_tokens (account_id, purpose, token_hash, status, expires_at)
  VALUES (p_target_account_id, 'email_verification', p_token_hash, 'pending', p_expires_at);
  INSERT INTO public.security_events (
    source, event_type, severity, outcome, account_id, safe_summary_json
  ) VALUES (
    'auth', 'managed_email_change_requested', 'high', 'success', p_target_account_id,
    jsonb_build_object('actor_account_id', p_actor_account_id)
  );
  INSERT INTO public.notification_outbox (
    kind, channel, recipient, status, payload_safe_json, template_version,
    dedupe_key, provider_idempotency_key
  ) VALUES (
    'email_verification', 'email', p_new_email, 'pending', p_protected_payload,
    1, p_dedupe_key, p_provider_idempotency_key
  );
  RETURN true;
END
$$;

CREATE FUNCTION public.create_password_reset_token_protected_v61(
  p_account_id uuid,
  p_token_hash text,
  p_expires_at timestamptz,
  p_protected_payload jsonb,
  p_dedupe_key text,
  p_provider_idempotency_key text,
  p_reason text
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_email text; v_event uuid;
BEGIN
  IF char_length(p_token_hash) <> 64 OR p_expires_at <= clock_timestamp()
     OR char_length(p_reason) > 128 THEN
    RAISE EXCEPTION 'invalid reset request';
  END IF;
  SELECT email INTO v_email FROM public.auth_accounts
  WHERE id = p_account_id AND disabled_at IS NULL AND email_verified_at IS NOT NULL;
  IF v_email IS NULL THEN RETURN false; END IF;
  UPDATE public.auth_reset_tokens SET status = 'revoked'
  WHERE account_id = p_account_id AND purpose = 'password_reset' AND status = 'pending';
  INSERT INTO public.auth_reset_tokens (account_id, purpose, token_hash, status, expires_at)
  VALUES (p_account_id, 'password_reset', p_token_hash, 'pending', p_expires_at);
  INSERT INTO public.security_events (
    source, event_type, severity, outcome, account_id, safe_summary_json
  ) VALUES (
    'auth', 'auth.password_reset_requested', 'medium', 'success', p_account_id,
    jsonb_build_object('reason', p_reason)
  ) RETURNING id INTO v_event;
  INSERT INTO public.notification_outbox (
    event_id, dedupe_key, channel, recipient, kind, template_version,
    provider_idempotency_key, payload_safe_json
  ) VALUES (
    v_event, p_dedupe_key, 'email', v_email, 'password_reset', 1,
    p_provider_idempotency_key, p_protected_payload
  );
  RETURN true;
END
$$;

CREATE FUNCTION public.begin_email_recovery_challenge_protected_v61(
  p_account_id uuid,
  p_recipient text,
  p_otp_digest text,
  p_completion_token_hash text,
  p_expires_at timestamptz,
  p_protected_payload jsonb,
  p_dedupe_key text,
  p_provider_idempotency_key text
) RETURNS TABLE(status text)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_email text; v_challenge_id uuid;
BEGIN
  IF p_otp_digest !~ '^[a-f0-9]{{64}}$'
     OR p_completion_token_hash !~ '^[a-f0-9]{{64}}$'
     OR p_expires_at <= clock_timestamp() THEN
    RAISE EXCEPTION 'invalid recovery challenge';
  END IF;
  SELECT a.email INTO v_email
  FROM public.auth_accounts AS a
  WHERE a.id = p_account_id AND a.disabled_at IS NULL
    AND a.email_verified_at IS NOT NULL AND a.role IN ('ADMIN', 'ANALYST')
  FOR UPDATE;
  IF v_email IS NULL THEN RAISE EXCEPTION 'recovery is unavailable'; END IF;
  IF v_email <> p_recipient THEN RAISE EXCEPTION 'recipient changed'; END IF;
  IF EXISTS (
    SELECT 1 FROM public.auth_email_otp_challenges AS e
    WHERE e.account_id = p_account_id AND e.status = 'pending'
      AND e.created_at > clock_timestamp() - interval '60 seconds'
  ) THEN RAISE EXCEPTION 'recovery resend cooldown'; END IF;

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
  ) VALUES (
    v_challenge_id, p_account_id, v_email, p_otp_digest, 'pending', 5, p_expires_at
  );
  INSERT INTO public.notification_outbox (
    channel, recipient, kind, template_version, dedupe_key,
    provider_idempotency_key, payload_safe_json
  ) VALUES (
    'email', v_email, 'email_recovery_otp', 1, p_dedupe_key,
    p_provider_idempotency_key, p_protected_payload
  );
  RETURN QUERY SELECT 'sent';
END
$$;
"""
        )
    )

    for signature in _PROTECTED_FUNCTION_SIGNATURES:
        _restrict_function(signature)


def downgrade() -> None:
    protected_sql = ", ".join(f"'{kind}'" for kind in PROTECTED_KINDS)
    op.execute(
        sa.text(
            f"""
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM public.notification_outbox
    WHERE kind IN ({protected_sql})
      AND status IN ('pending', 'leased', 'retry_wait')
  ) THEN
    RAISE EXCEPTION 'active encrypted notification payloads prevent downgrade';
  END IF;
END
$$;
"""
        )
    )
    for signature in reversed(_PROTECTED_FUNCTION_SIGNATURES):
        op.execute(sa.text(f"DROP FUNCTION IF EXISTS {signature}"))

    op.execute(
        sa.text(
            """
CREATE OR REPLACE FUNCTION public.notification_outbox_guard_v61()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_deadline timestamptz;
BEGIN
  IF NEW.channel <> 'email' THEN
    RAISE EXCEPTION 'notification channel is unsupported';
  END IF;
  IF NEW.kind = 'legacy_notification' THEN
    NEW.status := 'permanent_failure';
    NEW.last_error_class := COALESCE(NEW.last_error_class, 'unsupported_notification_kind');
  END IF;
  IF TG_OP = 'INSERT' THEN
    IF NEW.kind IN ('password_setup', 'password_reset') THEN
      SELECT max(t.expires_at) INTO v_deadline
      FROM public.auth_reset_tokens AS t
      JOIN public.auth_accounts AS a ON a.id = t.account_id
      WHERE a.email = NEW.recipient AND t.purpose = NEW.kind AND t.status = 'pending';
    ELSIF NEW.kind = 'email_verification' THEN
      SELECT max(t.expires_at) INTO v_deadline
      FROM public.auth_reset_tokens AS t
      JOIN public.auth_accounts AS a ON a.id = t.account_id
      WHERE a.pending_email = NEW.recipient
        AND t.purpose = 'email_verification' AND t.status = 'pending';
    ELSIF NEW.kind = 'email_recovery_otp' THEN
      SELECT max(e.expires_at) INTO v_deadline
      FROM public.auth_email_otp_challenges AS e
      WHERE e.email_to = NEW.recipient AND e.status = 'pending';
    END IF;
    IF v_deadline IS NOT NULL THEN
      NEW.deliver_before := v_deadline;
      IF v_deadline <= clock_timestamp() AND NEW.status IN ('pending', 'retry_wait', 'leased') THEN
        NEW.status := 'expired';
        NEW.last_error_class := 'delivery_deadline_expired';
      END IF;
    END IF;
  END IF;
  IF NEW.status IN ('sent', 'cancelled', 'expired', 'permanent_failure') THEN
    NEW.payload_safe_json := '{}'::jsonb;
    NEW.terminalized_at := COALESCE(NEW.terminalized_at, clock_timestamp());
  END IF;
  RETURN NEW;
END
$$;
"""
        )
    )
