"""Use security-event UUIDs for account-status notification idempotency."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260711_000018"
down_revision = "20260711_000017"
branch_labels = None
depends_on = None


_SIGNATURE = "public.admin_set_account_enabled_v61(uuid, uuid, boolean)"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
CREATE FUNCTION public.admin_set_account_enabled_v61(
  p_actor_account_id uuid,
  p_target_account_id uuid,
  p_enabled boolean
) RETURNS boolean
LANGUAGE plpgsql SECURITY INVOKER SET search_path = '' AS $$
DECLARE
  v_email text;
  v_event_name text;
  v_key text;
  v_event uuid;
BEGIN
  IF p_actor_account_id = p_target_account_id THEN
    RAISE EXCEPTION 'self status change forbidden';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM public.auth_accounts
    WHERE id = p_actor_account_id AND role = 'ADMIN' AND disabled_at IS NULL
  ) THEN
    RAISE EXCEPTION 'admin authorization failed';
  END IF;
  UPDATE public.auth_accounts
  SET disabled_at = CASE WHEN p_enabled THEN NULL ELSE clock_timestamp() END,
      authz_version = authz_version + 1
  WHERE id = p_target_account_id
  RETURNING email INTO v_email;
  IF v_email IS NULL THEN RAISE EXCEPTION 'account not found'; END IF;

  v_event_name := CASE WHEN p_enabled THEN 'account_reenabled' ELSE 'account_disabled' END;
  INSERT INTO public.security_events (
    source, event_type, severity, outcome, account_id, safe_summary_json
  ) VALUES (
    'auth', v_event_name, 'high', 'success', p_target_account_id,
    jsonb_build_object('actor_account_id', p_actor_account_id)
  ) RETURNING id INTO v_event;
  v_key := v_event_name || '/' || v_event::text;
  INSERT INTO public.notification_outbox (
    event_id, kind, channel, recipient, status, payload_safe_json,
    template_version, dedupe_key, provider_idempotency_key
  ) VALUES (
    v_event, v_event_name, 'email', v_email, 'pending', '{}'::jsonb,
    1, v_key, v_key
  );
  RETURN true;
END
$$;
"""
        )
    )
    op.execute(sa.text(f"REVOKE EXECUTE ON FUNCTION {_SIGNATURE} FROM PUBLIC"))
    op.execute(
        sa.text(
            f"""
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION {_SIGNATURE} FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE EXECUTE ON FUNCTION {_SIGNATURE} FROM authenticated';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
    EXECUTE 'GRANT EXECUTE ON FUNCTION {_SIGNATURE} TO service_role';
  END IF;
END
$$
"""
        )
    )


def downgrade() -> None:
    op.execute(sa.text(f"DROP FUNCTION IF EXISTS {_SIGNATURE}"))
