"""Add shared, race-safe state for password login throttling."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261105_000034"
down_revision = "20261007_000033"
branch_labels = None
depends_on = None

_BEGIN_SIGNATURE = (
    "public.begin_auth_login_attempt_v1(uuid, uuid, boolean, boolean, "
    "integer, integer, integer, integer)"
)
_COMPLETE_SIGNATURE = (
    "public.complete_auth_login_attempt_v1(uuid, uuid, text, integer, "
    "integer, integer)"
)


def _is_postgresql() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgresql():
        return

    op.create_table(
        "auth_login_throttle_state",
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_accounts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "failure_count", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column(
            "window_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("blocked_until", sa.DateTime(timezone=True)),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "failure_count >= 0", name="ck_auth_login_throttle_failure_count"
        ),
    )
    op.create_table(
        "auth_login_attempt_reservations",
        sa.Column(
            "attempt_id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("auth_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_auth_login_attempt_reservations_account_expiry",
        "auth_login_attempt_reservations",
        ["account_id", "expires_at"],
    )

    for table in (
        "auth_login_throttle_state",
        "auth_login_attempt_reservations",
    ):
        op.execute(sa.text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"REVOKE ALL ON TABLE public.{table} FROM PUBLIC"))
        op.execute(
            sa.text(
                f"""
DO $migration$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.{table} FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.{table} FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.{table} TO service_role';
  END IF;
END
$migration$
"""
            )
        )

    op.execute(
        sa.text(
            f"""
CREATE FUNCTION public.begin_auth_login_attempt_v1(
  p_account_id uuid,
  p_attempt_id uuid,
  p_turnstile_enabled boolean,
  p_turnstile_verified boolean,
  p_challenge_threshold integer,
  p_max_failures integer,
  p_window_seconds integer,
  p_cooldown_seconds integer
)
RETURNS TABLE (
  allowed boolean,
  reason_code text,
  failure_count integer,
  reservation_id uuid
)
LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path = ''
AS $$
DECLARE
  v_now timestamptz := pg_catalog.clock_timestamp();
  v_state public.auth_login_throttle_state%ROWTYPE;
  v_active_attempts integer := 0;
  v_next_failures integer;
BEGIN
  IF p_account_id IS NULL OR p_attempt_id IS NULL
     OR p_turnstile_enabled IS NULL OR p_turnstile_verified IS NULL
     OR p_challenge_threshold IS NULL OR p_max_failures IS NULL
     OR p_window_seconds IS NULL OR p_cooldown_seconds IS NULL
     OR p_max_failures NOT BETWEEN 2 AND 20
     OR p_challenge_threshold NOT BETWEEN 1 AND p_max_failures - 1
     OR p_window_seconds NOT BETWEEN 1 AND 3600
     OR p_cooldown_seconds NOT BETWEEN 1 AND 3600 THEN
    RAISE EXCEPTION 'invalid login throttle policy' USING ERRCODE = '22023';
  END IF;

  INSERT INTO public.auth_login_throttle_state (account_id)
  VALUES (p_account_id)
  ON CONFLICT (account_id) DO NOTHING;

  SELECT state.*
  INTO v_state
  FROM public.auth_login_throttle_state AS state
  WHERE state.account_id = p_account_id
  FOR UPDATE;

  DELETE FROM public.auth_login_attempt_reservations AS reservation
  WHERE reservation.account_id = p_account_id
    AND reservation.expires_at <= v_now;

  SELECT pg_catalog.count(*)::integer
  INTO v_active_attempts
  FROM public.auth_login_attempt_reservations AS reservation
  WHERE reservation.account_id = p_account_id
    AND reservation.expires_at > v_now;

  IF v_state.blocked_until > v_now THEN
    RETURN QUERY SELECT false, 'IDENTIFIER_THROTTLED'::text,
      v_state.failure_count, NULL::uuid;
    RETURN;
  END IF;

  IF v_state.blocked_until IS NOT NULL
     OR v_now - v_state.window_started_at >= pg_catalog.make_interval(secs => p_window_seconds) THEN
    UPDATE public.auth_login_throttle_state AS state
    SET failure_count = 0,
        window_started_at = v_now,
        blocked_until = NULL,
        updated_at = v_now
    WHERE state.account_id = p_account_id;
    v_state.failure_count := 0;
    v_state.window_started_at := v_now;
    v_state.blocked_until := NULL;
  END IF;

  v_next_failures := v_state.failure_count + v_active_attempts;
  IF v_state.failure_count >= p_max_failures THEN
    UPDATE public.auth_login_throttle_state AS state
    SET blocked_until = v_now + pg_catalog.make_interval(secs => p_cooldown_seconds),
        updated_at = v_now
    WHERE state.account_id = p_account_id
    RETURNING state.failure_count INTO v_next_failures;
    RETURN QUERY SELECT false, 'IDENTIFIER_THROTTLED'::text,
      v_next_failures, NULL::uuid;
    RETURN;
  END IF;

  IF v_next_failures >= p_max_failures THEN
    RETURN QUERY SELECT false, 'IDENTIFIER_THROTTLED'::text,
      v_state.failure_count, NULL::uuid;
    RETURN;
  END IF;

  IF p_turnstile_enabled
     AND v_next_failures >= p_challenge_threshold
     AND NOT p_turnstile_verified THEN
    RETURN QUERY SELECT false, 'VERIFICATION_REQUIRED'::text,
      v_state.failure_count, NULL::uuid;
    RETURN;
  END IF;

  INSERT INTO public.auth_login_attempt_reservations (
    attempt_id, account_id, expires_at
  ) VALUES (
    p_attempt_id, p_account_id, v_now + interval '60 seconds'
  );

  RETURN QUERY SELECT true, NULL::text, v_state.failure_count, p_attempt_id;
END
$$
"""
        )
    )
    op.execute(
        sa.text(
            f"""
CREATE FUNCTION public.complete_auth_login_attempt_v1(
  p_account_id uuid,
  p_attempt_id uuid,
  p_outcome text,
  p_max_failures integer,
  p_window_seconds integer,
  p_cooldown_seconds integer
)
RETURNS TABLE (
  completed boolean,
  failure_count integer,
  cooldown_active boolean
)
LANGUAGE plpgsql VOLATILE SECURITY INVOKER SET search_path = ''
AS $$
DECLARE
  v_now timestamptz := pg_catalog.clock_timestamp();
  v_state public.auth_login_throttle_state%ROWTYPE;
  v_reservation uuid;
  v_failures integer;
  v_blocked_until timestamptz;
BEGIN
  IF p_account_id IS NULL OR p_attempt_id IS NULL OR p_outcome IS NULL
     OR p_max_failures IS NULL OR p_window_seconds IS NULL
     OR p_cooldown_seconds IS NULL
     OR p_outcome NOT IN ('success', 'failure', 'abandoned')
     OR p_max_failures NOT BETWEEN 2 AND 20
     OR p_window_seconds NOT BETWEEN 1 AND 3600
     OR p_cooldown_seconds NOT BETWEEN 1 AND 3600 THEN
    RAISE EXCEPTION 'invalid login attempt completion' USING ERRCODE = '22023';
  END IF;

  SELECT state.*
  INTO v_state
  FROM public.auth_login_throttle_state AS state
  WHERE state.account_id = p_account_id
  FOR UPDATE;

  IF NOT FOUND THEN
    RETURN QUERY SELECT false, 0, false;
    RETURN;
  END IF;

  DELETE FROM public.auth_login_attempt_reservations AS reservation
  WHERE reservation.account_id = p_account_id
    AND reservation.attempt_id = p_attempt_id
  RETURNING reservation.attempt_id INTO v_reservation;

  IF NOT FOUND THEN
    RETURN QUERY SELECT false, v_state.failure_count,
      COALESCE(v_state.blocked_until > v_now, false);
    RETURN;
  END IF;

  IF p_outcome = 'abandoned' THEN
    RETURN QUERY SELECT true, v_state.failure_count,
      COALESCE(v_state.blocked_until > v_now, false);
    RETURN;
  END IF;

  IF p_outcome = 'success' THEN
    UPDATE public.auth_login_throttle_state AS state
    SET failure_count = 0,
        window_started_at = v_now,
        blocked_until = NULL,
        updated_at = v_now
    WHERE state.account_id = p_account_id;
    RETURN QUERY SELECT true, 0, false;
    RETURN;
  END IF;

  v_failures := v_state.failure_count;
  v_blocked_until := v_state.blocked_until;
  IF COALESCE(v_blocked_until <= v_now, true)
     AND v_now - v_state.window_started_at >= pg_catalog.make_interval(secs => p_window_seconds) THEN
    v_failures := 0;
    v_blocked_until := NULL;
  END IF;
  v_failures := LEAST(v_failures + 1, p_max_failures);
  IF v_failures >= p_max_failures THEN
    v_blocked_until := COALESCE(
      CASE WHEN v_blocked_until > v_now THEN v_blocked_until END,
      v_now + pg_catalog.make_interval(secs => p_cooldown_seconds)
    );
  END IF;

  UPDATE public.auth_login_throttle_state AS state
  SET failure_count = v_failures,
      window_started_at = CASE
        WHEN v_failures = 1 THEN v_now
        ELSE state.window_started_at
      END,
      blocked_until = v_blocked_until,
      updated_at = v_now
  WHERE state.account_id = p_account_id;

  RETURN QUERY SELECT true, v_failures,
    COALESCE(v_blocked_until > v_now, false);
END
$$
"""
        )
    )

    for signature in (_BEGIN_SIGNATURE, _COMPLETE_SIGNATURE):
        op.execute(sa.text(f"REVOKE EXECUTE ON FUNCTION {signature} FROM PUBLIC"))
        op.execute(
            sa.text(
                f"""
DO $migration$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION {signature} FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION {signature} FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT EXECUTE ON FUNCTION {signature} TO service_role';
  END IF;
END
$migration$
"""
            )
        )


def downgrade() -> None:
    if not _is_postgresql():
        return

    op.execute(sa.text(f"DROP FUNCTION IF EXISTS {_COMPLETE_SIGNATURE}"))
    op.execute(sa.text(f"DROP FUNCTION IF EXISTS {_BEGIN_SIGNATURE}"))
    op.drop_index(
        "ix_auth_login_attempt_reservations_account_expiry",
        table_name="auth_login_attempt_reservations",
    )
    op.drop_table("auth_login_attempt_reservations")
    op.drop_table("auth_login_throttle_state")
