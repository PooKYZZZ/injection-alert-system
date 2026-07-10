"""Add pre-auth MFA challenge binding and one-time Auth.js completion."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260710_000012"
down_revision = "20260710_000011"
branch_labels = None
depends_on = None


_FUNCTION_SIGNATURES = (
    "public.begin_login_mfa_challenge(uuid, text, timestamp with time zone)",
    "public.verify_totp_and_issue_completion(uuid, text, uuid, bigint, text, timestamp with time zone)",
    "public.consume_mfa_completion_token(text)",
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
        "auth_mfa_challenges",
        sa.Column("purpose", sa.Text(), nullable=False, server_default="login_mfa"),
    )
    op.add_column("auth_mfa_challenges", sa.Column("preauth_handle_hash", sa.Text()))
    op.add_column("auth_mfa_challenges", sa.Column("verified_method", sa.Text()))
    op.add_column("auth_mfa_challenges", sa.Column("verified_at", sa.DateTime(timezone=True)))
    op.add_column("auth_mfa_challenges", sa.Column("completion_token_hash", sa.Text()))
    op.add_column("auth_mfa_challenges", sa.Column("completion_expires_at", sa.DateTime(timezone=True)))
    op.add_column("auth_mfa_challenges", sa.Column("consumed_at", sa.DateTime(timezone=True)))
    op.drop_constraint("ck_auth_mfa_challenge_status", "auth_mfa_challenges", type_="check")
    op.execute(sa.text("UPDATE auth_mfa_challenges SET status = CASE status WHEN 'passed' THEN 'verified' WHEN 'cancelled' THEN 'expired' ELSE status END"))
    op.create_check_constraint(
        "ck_auth_mfa_challenge_status_v61",
        "auth_mfa_challenges",
        "status IN ('pending', 'verified', 'consumed', 'expired', 'locked')",
    )
    op.create_check_constraint(
        "ck_auth_mfa_challenge_purpose_v61",
        "auth_mfa_challenges",
        "purpose IN ('login_mfa', 'mfa_enrollment', 'mfa_recovery', 'recent_reauthentication')",
    )
    op.create_index(
        "idx_auth_mfa_challenges_preauth_hash",
        "auth_mfa_challenges",
        ["preauth_handle_hash"],
        unique=True,
        postgresql_where=sa.text("preauth_handle_hash is not null"),
    )

    op.execute(
        sa.text(
            """
CREATE OR REPLACE FUNCTION public.begin_login_mfa_challenge(
  p_account_id uuid, p_preauth_handle_hash text, p_expires_at timestamptz
) RETURNS uuid
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_id uuid;
BEGIN
  IF char_length(p_preauth_handle_hash) <> 64 OR p_expires_at <= clock_timestamp() THEN
    RAISE EXCEPTION 'invalid challenge';
  END IF;
  UPDATE public.auth_mfa_challenges SET status = 'expired', used_at = clock_timestamp()
  WHERE account_id = p_account_id AND purpose = 'login_mfa' AND status = 'pending';
  INSERT INTO public.auth_mfa_challenges (
    account_id, challenge_hash, purpose, preauth_handle_hash, status, expires_at
  ) VALUES (
    p_account_id, p_preauth_handle_hash, 'login_mfa', p_preauth_handle_hash, 'pending', p_expires_at
  ) RETURNING id INTO v_id;
  RETURN v_id;
END
$$;

CREATE OR REPLACE FUNCTION public.verify_totp_and_issue_completion(
  p_account_id uuid, p_preauth_handle_hash text, p_factor_id uuid,
  p_time_step bigint, p_completion_token_hash text, p_completion_expires_at timestamptz
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_challenge_id uuid;
BEGIN
  IF char_length(p_completion_token_hash) <> 64 OR p_completion_expires_at <= clock_timestamp() THEN
    RAISE EXCEPTION 'invalid completion token';
  END IF;
  SELECT id INTO v_challenge_id FROM public.auth_mfa_challenges
  WHERE account_id = p_account_id AND purpose = 'login_mfa'
    AND preauth_handle_hash = p_preauth_handle_hash AND status = 'pending'
    AND expires_at > clock_timestamp()
  FOR UPDATE;
  IF v_challenge_id IS NULL THEN RAISE EXCEPTION 'challenge is invalid or expired'; END IF;
  UPDATE public.auth_mfa_factors
  SET last_used_time_step = p_time_step
  WHERE id = p_factor_id AND account_id = p_account_id AND status = 'active'
    AND (last_used_time_step IS NULL OR p_time_step > last_used_time_step);
  IF NOT FOUND THEN RAISE EXCEPTION 'TOTP code is invalid or already used'; END IF;
  INSERT INTO public.auth_mfa_completion_tokens (
    account_id, mfa_challenge_id, token_hash, status, expires_at
  ) VALUES (
    p_account_id, v_challenge_id, p_completion_token_hash, 'pending', p_completion_expires_at
  );
  UPDATE public.auth_mfa_challenges
  SET status = 'verified', verified_method = 'totp', verified_at = clock_timestamp(),
      completion_token_hash = p_completion_token_hash, completion_expires_at = p_completion_expires_at
  WHERE id = v_challenge_id;
  RETURN true;
END
$$;

CREATE OR REPLACE FUNCTION public.consume_mfa_completion_token(
  p_completion_token_hash text
) RETURNS TABLE(account_id uuid, role text, authz_version integer)
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE v_account_id uuid; v_challenge_id uuid;
BEGIN
  SELECT t.account_id, t.mfa_challenge_id INTO v_account_id, v_challenge_id
  FROM public.auth_mfa_completion_tokens t
  WHERE t.token_hash = p_completion_token_hash AND t.status = 'pending'
    AND t.expires_at > clock_timestamp()
  FOR UPDATE;
  IF v_account_id IS NULL THEN RAISE EXCEPTION 'completion token is invalid or expired'; END IF;
  UPDATE public.auth_mfa_challenges SET status = 'consumed', consumed_at = clock_timestamp()
  WHERE id = v_challenge_id AND status = 'verified';
  IF NOT FOUND THEN RAISE EXCEPTION 'challenge is no longer usable'; END IF;
  UPDATE public.auth_mfa_completion_tokens SET status = 'used', used_at = clock_timestamp()
  WHERE token_hash = p_completion_token_hash AND status = 'pending';
  RETURN QUERY
  SELECT a.id, a.role, a.authz_version
  FROM public.auth_accounts a
  WHERE a.id = v_account_id AND a.disabled_at IS NULL;
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
    op.drop_index("idx_auth_mfa_challenges_preauth_hash", table_name="auth_mfa_challenges")
    op.drop_constraint("ck_auth_mfa_challenge_purpose_v61", "auth_mfa_challenges", type_="check")
    op.drop_constraint("ck_auth_mfa_challenge_status_v61", "auth_mfa_challenges", type_="check")
    op.execute(sa.text("UPDATE auth_mfa_challenges SET status = CASE status WHEN 'verified' THEN 'passed' WHEN 'consumed' THEN 'passed' ELSE status END"))
    op.create_check_constraint(
        "ck_auth_mfa_challenge_status",
        "auth_mfa_challenges",
        "status IN ('pending', 'passed', 'expired', 'locked', 'cancelled')",
    )
    for column in (
        "consumed_at",
        "completion_expires_at",
        "completion_token_hash",
        "verified_at",
        "verified_method",
        "preauth_handle_hash",
        "purpose",
    ):
        op.drop_column("auth_mfa_challenges", column)
