"""Add encrypted TOTP factors, replay-safe activation, and one-time backup codes."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260710_000011"
down_revision = "20260710_000010"
branch_labels = None
depends_on = None


_FUNCTION_SIGNATURES = (
    "public.begin_totp_enrollment(uuid, uuid, text, text, integer, timestamp with time zone)",
    "public.activate_totp_factor(uuid, uuid, bigint, jsonb)",
    "public.consume_totp_step(uuid, uuid, bigint)",
    "public.list_backup_code_candidates(uuid, text)",
    "public.consume_backup_code(uuid, uuid)",
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
    op.add_column("auth_mfa_factors", sa.Column("secret_nonce", sa.Text()))
    op.add_column("auth_mfa_factors", sa.Column("expires_at", sa.DateTime(timezone=True)))
    op.add_column("auth_mfa_factors", sa.Column("activated_at", sa.DateTime(timezone=True)))
    op.add_column("auth_mfa_factors", sa.Column("revoked_at", sa.DateTime(timezone=True)))
    op.drop_index("idx_auth_mfa_one_verified_totp", table_name="auth_mfa_factors")
    op.drop_constraint("ck_auth_mfa_factor_status", "auth_mfa_factors", type_="check")
    # Legacy factors have no nonce/AES-GCM key metadata; revoke them rather than
    # treating an unverifiable ciphertext as an active authentication factor.
    op.execute(sa.text("UPDATE auth_mfa_factors SET status = 'revoked', revoked_at = clock_timestamp() WHERE status IN ('verified', 'disabled')"))
    op.create_check_constraint(
        "ck_auth_mfa_factor_status_v61",
        "auth_mfa_factors",
        "status IN ('pending', 'active', 'revoked')",
    )
    op.create_index(
        "idx_auth_mfa_one_active_totp",
        "auth_mfa_factors",
        ["account_id"],
        unique=True,
        postgresql_where=sa.text("factor_type = 'totp' and status = 'active'"),
    )
    op.add_column("auth_backup_codes", sa.Column("lookup_prefix", sa.Text()))
    op.add_column("auth_backup_codes", sa.Column("revoked_at", sa.DateTime(timezone=True)))
    op.create_index(
        "idx_auth_backup_codes_lookup",
        "auth_backup_codes",
        ["account_id", "lookup_prefix"],
        postgresql_where=sa.text("used_at is null and revoked_at is null"),
    )

    op.execute(
        sa.text(
            """
CREATE OR REPLACE FUNCTION public.begin_totp_enrollment(
  p_account_id uuid, p_factor_id uuid, p_ciphertext text, p_nonce text,
  p_key_version integer, p_expires_at timestamptz
) RETURNS uuid
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_id uuid;
BEGIN
  IF p_expires_at <= clock_timestamp() OR char_length(p_ciphertext) < 16 OR char_length(p_nonce) < 8 THEN
    RAISE EXCEPTION 'invalid enrollment';
  END IF;
  IF EXISTS (SELECT 1 FROM public.auth_mfa_factors WHERE account_id = p_account_id AND factor_type = 'totp' AND status = 'active') THEN
    RAISE EXCEPTION 'active factor exists';
  END IF;
  UPDATE public.auth_mfa_factors SET status = 'revoked', revoked_at = clock_timestamp()
  WHERE account_id = p_account_id AND factor_type = 'totp' AND status = 'pending';
  INSERT INTO public.auth_mfa_factors (id, account_id, factor_type, status, secret_ciphertext, secret_nonce, secret_key_version, expires_at)
  VALUES (p_factor_id, p_account_id, 'totp', 'pending', p_ciphertext, p_nonce, p_key_version, p_expires_at)
  RETURNING id INTO v_id;
  RETURN v_id;
END
$$;

CREATE OR REPLACE FUNCTION public.activate_totp_factor(
  p_account_id uuid, p_factor_id uuid, p_time_step bigint, p_backup_codes jsonb
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_email text; v_event uuid; v_code jsonb;
BEGIN
  UPDATE public.auth_mfa_factors
  SET status = 'active', activated_at = clock_timestamp(), last_used_time_step = p_time_step,
      expires_at = NULL
  WHERE id = p_factor_id AND account_id = p_account_id AND factor_type = 'totp'
    AND status = 'pending' AND expires_at > clock_timestamp();
  IF NOT FOUND THEN RAISE EXCEPTION 'enrollment is invalid or expired'; END IF;
  IF EXISTS (SELECT 1 FROM public.auth_mfa_factors WHERE account_id = p_account_id AND factor_type = 'totp' AND status = 'active' AND id <> p_factor_id) THEN
    RAISE EXCEPTION 'active factor exists';
  END IF;
  DELETE FROM public.auth_backup_codes WHERE account_id = p_account_id AND used_at IS NULL AND revoked_at IS NULL;
  FOR v_code IN SELECT value FROM jsonb_array_elements(p_backup_codes)
  LOOP
    INSERT INTO public.auth_backup_codes (account_id, lookup_prefix, code_hash)
    VALUES (p_account_id, v_code->>'lookup_prefix', v_code->>'code_hash');
  END LOOP;
  UPDATE public.auth_accounts SET authz_version = authz_version + 1 WHERE id = p_account_id RETURNING email INTO v_email;
  INSERT INTO public.security_events (source, event_type, severity, outcome, account_id, safe_summary_json)
  VALUES ('auth', 'auth.totp_enrolled', 'medium', 'success', p_account_id, jsonb_build_object('factor_type', 'totp')) RETURNING id INTO v_event;
  INSERT INTO public.notification_outbox (event_id, dedupe_key, channel, recipient, kind, template_version, provider_idempotency_key, payload_safe_json)
  VALUES (v_event, 'totp-enrolled/' || p_factor_id::text, 'email', v_email, 'totp_enrolled', 1, 'totp-enrolled/' || p_factor_id::text, '{}'::jsonb);
  RETURN true;
END
$$;

CREATE OR REPLACE FUNCTION public.consume_totp_step(
  p_account_id uuid, p_factor_id uuid, p_time_step bigint
) RETURNS boolean
LANGUAGE sql SECURITY INVOKER SET search_path = '' AS $$
UPDATE public.auth_mfa_factors
SET last_used_time_step = p_time_step
WHERE id = p_factor_id AND account_id = p_account_id AND status = 'active'
  AND (last_used_time_step IS NULL OR p_time_step > last_used_time_step)
RETURNING true
$$;

CREATE OR REPLACE FUNCTION public.list_backup_code_candidates(
  p_account_id uuid, p_lookup_prefix text
) RETURNS TABLE(id uuid, code_hash text)
LANGUAGE sql SECURITY INVOKER SET search_path = '' AS $$
SELECT id, code_hash FROM public.auth_backup_codes
WHERE account_id = p_account_id AND lookup_prefix = p_lookup_prefix
  AND used_at IS NULL AND revoked_at IS NULL
FOR UPDATE
$$;

CREATE OR REPLACE FUNCTION public.consume_backup_code(
  p_account_id uuid, p_code_id uuid
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_email text; v_event uuid;
BEGIN
  UPDATE public.auth_backup_codes SET used_at = clock_timestamp()
  WHERE id = p_code_id AND account_id = p_account_id AND used_at IS NULL AND revoked_at IS NULL;
  IF NOT FOUND THEN RETURN false; END IF;
  UPDATE public.auth_accounts SET authz_version = authz_version + 1 WHERE id = p_account_id RETURNING email INTO v_email;
  INSERT INTO public.security_events (source, event_type, severity, outcome, account_id, safe_summary_json)
  VALUES ('auth', 'auth.backup_code_used', 'high', 'success', p_account_id, jsonb_build_object('method', 'backup_code')) RETURNING id INTO v_event;
  INSERT INTO public.notification_outbox (event_id, dedupe_key, channel, recipient, kind, template_version, provider_idempotency_key, payload_safe_json)
  VALUES (v_event, 'backup-code-used/' || p_code_id::text, 'email', v_email, 'backup_code_used', 1, 'backup-code-used/' || p_code_id::text, '{}'::jsonb);
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
    op.drop_index("idx_auth_backup_codes_lookup", table_name="auth_backup_codes")
    op.drop_column("auth_backup_codes", "revoked_at")
    op.drop_column("auth_backup_codes", "lookup_prefix")
    op.drop_index("idx_auth_mfa_one_active_totp", table_name="auth_mfa_factors")
    op.drop_constraint("ck_auth_mfa_factor_status_v61", "auth_mfa_factors", type_="check")
    op.execute(sa.text("UPDATE auth_mfa_factors SET status = CASE WHEN status = 'active' THEN 'verified' ELSE 'disabled' END"))
    op.create_check_constraint(
        "ck_auth_mfa_factor_status",
        "auth_mfa_factors",
        "status IN ('pending', 'verified', 'disabled')",
    )
    op.create_index(
        "idx_auth_mfa_one_verified_totp",
        "auth_mfa_factors",
        ["account_id"],
        unique=True,
        postgresql_where=sa.text("factor_type = 'totp' and status = 'verified'"),
    )
    for column in ("revoked_at", "activated_at", "expires_at", "secret_nonce"):
        op.drop_column("auth_mfa_factors", column)
