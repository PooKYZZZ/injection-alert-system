"""Add V6.1 ADMIN account-management and setup transitions.

Revision ID: 20260710_000010
Revises: 20260710_000009
Create Date: 2026-07-10 18:30:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260710_000010"
down_revision = "20260710_000009"
branch_labels = None
depends_on = None


_SIGNATURES = (
    "public.admin_create_auth_account(uuid, text, text, text, text, timestamp with time zone, text, text, text)",
    "public.admin_resend_password_setup(uuid, uuid, text, timestamp with time zone, text, text, text)",
    "public.consume_password_setup_token(text, text)",
    "public.admin_change_account_role(uuid, uuid, text)",
    "public.admin_set_account_enabled(uuid, uuid, boolean)",
    "public.admin_request_managed_email_change(uuid, uuid, text, text, timestamp with time zone, text, text, text)",
    "public.activate_verified_managed_email(text)",
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
    op.add_column("auth_accounts", sa.Column("pending_email", sa.Text()))
    op.add_column(
        "auth_accounts",
        sa.Column("pending_email_requested_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "auth_accounts_pending_email_unique",
        "auth_accounts",
        [sa.text("lower(pending_email)")],
        unique=True,
        postgresql_where=sa.text("pending_email is not null"),
    )
    op.create_check_constraint(
        "ck_auth_accounts_pending_email_state",
        "auth_accounts",
        "(pending_email IS NULL AND pending_email_requested_at IS NULL) OR (pending_email IS NOT NULL AND pending_email_requested_at IS NOT NULL)",
    )
    op.drop_constraint(
        "ck_auth_reset_token_purpose", "auth_reset_tokens", type_="check"
    )
    op.create_check_constraint(
        "ck_auth_reset_token_purpose_v61",
        "auth_reset_tokens",
        "purpose IN ('password_setup', 'password_reset', 'mfa_reset', 'email_verification')",
    )

    op.execute(
        sa.text(
            """
CREATE FUNCTION public.admin_create_auth_account(
  p_actor_account_id uuid,
  p_email text,
  p_name text,
  p_role text,
  p_setup_token_hash text,
  p_expires_at timestamp with time zone,
  p_setup_url text,
  p_dedupe_key text,
  p_provider_idempotency_key text
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  new_account_id uuid;
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
  IF p_setup_token_hash !~ '^[a-f0-9]{64}$' OR p_expires_at <= clock_timestamp() THEN
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
    'password_setup', 'email', p_email, 'pending',
    jsonb_build_object('setup_url', p_setup_url), 1,
    p_dedupe_key, p_provider_idempotency_key
  );
  RETURN new_account_id;
END;
$$
"""
        )
    )
    op.execute(
        sa.text(
            """
CREATE FUNCTION public.admin_resend_password_setup(
  p_actor_account_id uuid,
  p_target_account_id uuid,
  p_setup_token_hash text,
  p_expires_at timestamp with time zone,
  p_setup_url text,
  p_dedupe_key text,
  p_provider_idempotency_key text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  target_email text;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM public.auth_accounts
    WHERE id = p_actor_account_id AND role = 'ADMIN' AND disabled_at IS NULL
  ) THEN RAISE EXCEPTION 'admin authorization failed'; END IF;
  SELECT email INTO target_email FROM public.auth_accounts
  WHERE id = p_target_account_id AND disabled_at IS NULL AND password_hash IS NULL
  FOR UPDATE;
  IF target_email IS NULL THEN RAISE EXCEPTION 'account is not eligible'; END IF;
  UPDATE public.auth_reset_tokens SET status = 'revoked'
  WHERE account_id = p_target_account_id AND purpose = 'password_setup'
    AND status = 'pending' AND used_at IS NULL;
  INSERT INTO public.auth_reset_tokens (account_id, purpose, token_hash, status, expires_at)
  VALUES (p_target_account_id, 'password_setup', p_setup_token_hash, 'pending', p_expires_at);
  INSERT INTO public.notification_outbox (
    kind, channel, recipient, status, payload_safe_json, template_version,
    dedupe_key, provider_idempotency_key
  ) VALUES (
    'password_setup', 'email', target_email, 'pending',
    jsonb_build_object('setup_url', p_setup_url), 1,
    p_dedupe_key, p_provider_idempotency_key
  );
  RETURN true;
END;
$$
"""
        )
    )
    op.execute(
        sa.text(
            """
CREATE FUNCTION public.consume_password_setup_token(
  p_token_hash text,
  p_password_hash text
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  token_id uuid;
  target_id uuid;
  target_email text;
  notification_key text;
BEGIN
  SELECT id, account_id INTO token_id, target_id
  FROM public.auth_reset_tokens
  WHERE token_hash = p_token_hash AND purpose = 'password_setup'
    AND status = 'pending' AND used_at IS NULL AND expires_at > clock_timestamp()
  FOR UPDATE;
  IF token_id IS NULL THEN RAISE EXCEPTION 'invalid or expired token'; END IF;
  IF p_password_hash IS NULL OR p_password_hash NOT LIKE '$argon2id$%' THEN
    RAISE EXCEPTION 'invalid password hash';
  END IF;

  UPDATE public.auth_reset_tokens
  SET status = 'used', used_at = clock_timestamp()
  WHERE id = token_id AND status = 'pending' AND used_at IS NULL;
  UPDATE public.auth_accounts
  SET password_hash = p_password_hash,
      password_set_at = clock_timestamp(),
      email_verified_at = COALESCE(email_verified_at, clock_timestamp()),
      authz_version = authz_version + 1
  WHERE id = target_id AND disabled_at IS NULL AND password_hash IS NULL
  RETURNING email INTO target_email;
  IF target_email IS NULL THEN RAISE EXCEPTION 'account is not eligible'; END IF;
  UPDATE public.auth_reset_tokens SET status = 'revoked'
  WHERE account_id = target_id AND id <> token_id AND status = 'pending';
  INSERT INTO public.security_events (
    source, event_type, severity, outcome, account_id, safe_summary_json
  ) VALUES ('auth', 'password_setup_completed', 'medium', 'success', target_id, '{}'::jsonb);
  notification_key := 'password-setup-completed/' || target_id::text || '/' || token_id::text;
  INSERT INTO public.notification_outbox (
    kind, channel, recipient, status, payload_safe_json, template_version,
    dedupe_key, provider_idempotency_key
  ) VALUES (
    'password_changed', 'email', target_email, 'pending', '{}'::jsonb, 1,
    notification_key, notification_key
  );
  RETURN target_id;
END;
$$
"""
        )
    )
    op.execute(
        sa.text(
            """
CREATE FUNCTION public.admin_change_account_role(
  p_actor_account_id uuid,
  p_target_account_id uuid,
  p_role text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
  IF p_actor_account_id = p_target_account_id THEN RAISE EXCEPTION 'self role change forbidden'; END IF;
  IF NOT EXISTS (SELECT 1 FROM public.auth_accounts WHERE id = p_actor_account_id AND role = 'ADMIN' AND disabled_at IS NULL) THEN
    RAISE EXCEPTION 'admin authorization failed';
  END IF;
  IF p_role NOT IN ('ADMIN', 'ANALYST', 'VIEWER') THEN RAISE EXCEPTION 'invalid role'; END IF;
  UPDATE public.auth_accounts
  SET role = p_role, mfa_required = p_role <> 'VIEWER',
      authz_version = authz_version + 1
  WHERE id = p_target_account_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'account not found'; END IF;
  INSERT INTO public.security_events (source, event_type, severity, outcome, account_id, safe_summary_json)
  VALUES ('auth', 'account_role_changed', 'high', 'success', p_target_account_id,
    jsonb_build_object('actor_account_id', p_actor_account_id, 'role', p_role));
  RETURN true;
END;
$$
"""
        )
    )
    op.execute(
        sa.text(
            """
CREATE FUNCTION public.admin_set_account_enabled(
  p_actor_account_id uuid,
  p_target_account_id uuid,
  p_enabled boolean
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  target_email text;
  event_name text;
  notification_kind text;
  notification_key text;
BEGIN
  IF p_actor_account_id = p_target_account_id THEN RAISE EXCEPTION 'self status change forbidden'; END IF;
  IF NOT EXISTS (SELECT 1 FROM public.auth_accounts WHERE id = p_actor_account_id AND role = 'ADMIN' AND disabled_at IS NULL) THEN
    RAISE EXCEPTION 'admin authorization failed';
  END IF;
  UPDATE public.auth_accounts
  SET disabled_at = CASE WHEN p_enabled THEN NULL ELSE clock_timestamp() END,
      authz_version = authz_version + 1
  WHERE id = p_target_account_id
  RETURNING email INTO target_email;
  IF target_email IS NULL THEN RAISE EXCEPTION 'account not found'; END IF;
  event_name := CASE WHEN p_enabled THEN 'account_reenabled' ELSE 'account_disabled' END;
  notification_kind := event_name;
  notification_key := event_name || '/' || p_target_account_id::text || '/' || extract(epoch from clock_timestamp())::bigint::text;
  INSERT INTO public.security_events (source, event_type, severity, outcome, account_id, safe_summary_json)
  VALUES ('auth', event_name, 'high', 'success', p_target_account_id,
    jsonb_build_object('actor_account_id', p_actor_account_id));
  INSERT INTO public.notification_outbox (
    kind, channel, recipient, status, payload_safe_json, template_version,
    dedupe_key, provider_idempotency_key
  ) VALUES (notification_kind, 'email', target_email, 'pending', '{}'::jsonb, 1,
    notification_key, notification_key);
  RETURN true;
END;
$$
"""
        )
    )
    op.execute(
        sa.text(
            """
CREATE FUNCTION public.admin_request_managed_email_change(
  p_actor_account_id uuid,
  p_target_account_id uuid,
  p_new_email text,
  p_token_hash text,
  p_expires_at timestamp with time zone,
  p_verification_url text,
  p_dedupe_key text,
  p_provider_idempotency_key text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM public.auth_accounts WHERE id = p_actor_account_id AND role = 'ADMIN' AND disabled_at IS NULL) THEN
    RAISE EXCEPTION 'admin authorization failed';
  END IF;
  IF p_new_email IS NULL OR p_new_email <> lower(btrim(p_new_email)) OR char_length(p_new_email) NOT BETWEEN 3 AND 320 THEN
    RAISE EXCEPTION 'invalid email';
  END IF;
  IF EXISTS (
    SELECT 1 FROM public.auth_accounts
    WHERE lower(email) = p_new_email
       OR (pending_email IS NOT NULL AND lower(pending_email) = p_new_email)
  ) THEN RAISE EXCEPTION 'email already in use'; END IF;
  IF p_token_hash !~ '^[a-f0-9]{64}$' OR p_expires_at <= clock_timestamp() THEN RAISE EXCEPTION 'invalid token'; END IF;
  UPDATE public.auth_accounts
  SET pending_email = p_new_email, pending_email_requested_at = clock_timestamp()
  WHERE id = p_target_account_id AND disabled_at IS NULL;
  IF NOT FOUND THEN RAISE EXCEPTION 'account not found'; END IF;
  UPDATE public.auth_reset_tokens SET status = 'revoked'
  WHERE account_id = p_target_account_id AND purpose = 'email_verification'
    AND status = 'pending' AND used_at IS NULL;
  INSERT INTO public.auth_reset_tokens (account_id, purpose, token_hash, status, expires_at)
  VALUES (p_target_account_id, 'email_verification', p_token_hash, 'pending', p_expires_at);
  INSERT INTO public.security_events (source, event_type, severity, outcome, account_id, safe_summary_json)
  VALUES ('auth', 'managed_email_change_requested', 'high', 'success', p_target_account_id,
    jsonb_build_object('actor_account_id', p_actor_account_id));
  INSERT INTO public.notification_outbox (
    kind, channel, recipient, status, payload_safe_json, template_version,
    dedupe_key, provider_idempotency_key
  ) VALUES ('email_verification', 'email', p_new_email, 'pending',
    jsonb_build_object('verification_url', p_verification_url), 1,
    p_dedupe_key, p_provider_idempotency_key);
  RETURN true;
END;
$$
"""
        )
    )
    op.execute(
        sa.text(
            """
CREATE FUNCTION public.activate_verified_managed_email(p_token_hash text)
RETURNS uuid
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  token_id uuid;
  target_id uuid;
  old_email text;
  new_email text;
  notification_key text;
BEGIN
  SELECT id, account_id INTO token_id, target_id
  FROM public.auth_reset_tokens
  WHERE token_hash = p_token_hash AND purpose = 'email_verification'
    AND status = 'pending' AND used_at IS NULL AND expires_at > clock_timestamp()
  FOR UPDATE;
  IF token_id IS NULL THEN RAISE EXCEPTION 'invalid or expired token'; END IF;
  SELECT email, pending_email INTO old_email, new_email
  FROM public.auth_accounts WHERE id = target_id AND disabled_at IS NULL FOR UPDATE;
  IF new_email IS NULL THEN RAISE EXCEPTION 'email change is not pending'; END IF;
  UPDATE public.auth_reset_tokens SET status = 'used', used_at = clock_timestamp()
  WHERE id = token_id AND status = 'pending' AND used_at IS NULL;
  UPDATE public.auth_accounts
  SET email = new_email, pending_email = NULL, pending_email_requested_at = NULL,
      email_verified_at = clock_timestamp(), authz_version = authz_version + 1
  WHERE id = target_id;
  UPDATE public.auth_email_otp_challenges SET status = 'expired'
  WHERE account_id = target_id AND status = 'pending';
  UPDATE public.auth_reset_tokens SET status = 'revoked'
  WHERE account_id = target_id AND id <> token_id AND status = 'pending';
  INSERT INTO public.security_events (source, event_type, severity, outcome, account_id, safe_summary_json)
  VALUES ('auth', 'managed_email_verified', 'high', 'success', target_id, '{}'::jsonb);
  notification_key := 'managed-email-changed/' || target_id::text || '/' || token_id::text;
  INSERT INTO public.notification_outbox (
    kind, channel, recipient, status, payload_safe_json, template_version,
    dedupe_key, provider_idempotency_key
  ) VALUES ('managed_email_changed', 'email', old_email, 'pending', '{}'::jsonb, 1,
    notification_key, notification_key);
  RETURN target_id;
END;
$$
"""
        )
    )

    for signature in _SIGNATURES:
        _restrict(signature)


def downgrade() -> None:
    op.execute(sa.text("DROP FUNCTION IF EXISTS public.activate_verified_managed_email(text)"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS public.admin_request_managed_email_change(uuid, uuid, text, text, timestamp with time zone, text, text, text)"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS public.admin_set_account_enabled(uuid, uuid, boolean)"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS public.admin_change_account_role(uuid, uuid, text)"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS public.consume_password_setup_token(text, text)"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS public.admin_resend_password_setup(uuid, uuid, text, timestamp with time zone, text, text, text)"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS public.admin_create_auth_account(uuid, text, text, text, text, timestamp with time zone, text, text, text)"))
    op.drop_constraint("ck_auth_reset_token_purpose_v61", "auth_reset_tokens", type_="check")
    op.execute(
        sa.text(
            "DELETE FROM public.auth_reset_tokens WHERE purpose = 'email_verification'"
        )
    )
    op.create_check_constraint(
        "ck_auth_reset_token_purpose",
        "auth_reset_tokens",
        "purpose IN ('password_setup', 'password_reset', 'mfa_reset')",
    )
    op.drop_constraint("ck_auth_accounts_pending_email_state", "auth_accounts", type_="check")
    op.drop_index("auth_accounts_pending_email_unique", table_name="auth_accounts")
    op.drop_column("auth_accounts", "pending_email_requested_at")
    op.drop_column("auth_accounts", "pending_email")
