"""Enable durable Telegram threat notifications without widening auth delivery."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260720_000022"
down_revision = "20260715_000021"
branch_labels = None
depends_on = None

_CLAIM_SIGNATURE = (
    "public.claim_notification_outbox_batch_v62(text, integer, integer)"
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


def _replace_guard(*, telegram_enabled: bool) -> None:
    channel_check = (
        "IF NEW.channel NOT IN ('email', 'telegram') THEN"
        if telegram_enabled
        else "IF NEW.channel <> 'email' THEN"
    )
    telegram_check = (
        """
  IF NEW.channel = 'telegram' AND NEW.kind <> 'threat_detected' THEN
    RAISE EXCEPTION 'Telegram channel supports threat_detected only';
  END IF;
"""
        if telegram_enabled
        else ""
    )
    op.execute(
        sa.text(
            f"""
CREATE OR REPLACE FUNCTION public.notification_outbox_guard_v61()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_deadline timestamptz;
BEGIN
  {channel_check}
    RAISE EXCEPTION 'notification channel is unsupported';
  END IF;
{telegram_check}
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
      IF v_deadline <= clock_timestamp()
         AND NEW.status IN ('pending', 'retry_wait', 'leased') THEN
        NEW.status := 'expired';
        NEW.last_error_class := 'delivery_deadline_expired';
      END IF;
    END IF;
  END IF;

  IF NEW.status IN ('sent', 'cancelled', 'expired', 'permanent_failure') THEN
    NEW.payload_safe_json := '{{}}'::jsonb;
    NEW.terminalized_at := COALESCE(NEW.terminalized_at, clock_timestamp());
  END IF;
  RETURN NEW;
END
$$
"""
        )
    )


def upgrade() -> None:
    op.drop_constraint(
        "ck_notification_outbox_channel_v61",
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "ck_notification_outbox_channel_v62",
        "notification_outbox",
        "channel IN ('email', 'telegram')",
    )
    op.create_check_constraint(
        "ck_notification_outbox_telegram_kind_v62",
        "notification_outbox",
        "channel <> 'telegram' OR kind = 'threat_detected'",
    )
    op.drop_index("idx_notification_outbox_claimable", table_name="notification_outbox")
    op.create_index(
        "idx_notification_outbox_claimable",
        "notification_outbox",
        ["next_attempt_at", "deliver_before", "created_at", "id"],
        postgresql_where=sa.text(
            "status IN ('pending', 'retry_wait') AND channel IN ('email', 'telegram')"
        ),
    )
    _replace_guard(telegram_enabled=True)
    op.execute(
        sa.text(
            """
CREATE FUNCTION public.claim_notification_outbox_batch_v62(
  p_worker_id text,
  p_batch_size integer DEFAULT 1,
  p_lease_seconds integer DEFAULT 60
)
RETURNS TABLE (
  id uuid,
  kind text,
  channel text,
  recipient text,
  payload_safe_json jsonb,
  template_version integer,
  dedupe_key text,
  provider_idempotency_key text,
  attempts integer,
  max_attempts integer,
  deliver_before timestamptz
)
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
  IF p_worker_id IS NULL OR char_length(p_worker_id) NOT BETWEEN 1 AND 128 THEN
    RAISE EXCEPTION 'invalid worker id';
  END IF;
  IF p_batch_size NOT BETWEEN 1 AND 100 THEN
    RAISE EXCEPTION 'invalid batch size';
  END IF;
  IF p_lease_seconds NOT BETWEEN 5 AND 300 THEN
    RAISE EXCEPTION 'invalid lease duration';
  END IF;

  UPDATE public.notification_outbox AS o
  SET status = 'expired',
      last_error_class = 'delivery_deadline_expired',
      locked_at = NULL, locked_by = NULL, lease_expires_at = NULL
  WHERE o.status IN ('pending', 'retry_wait', 'leased')
    AND o.deliver_before <= clock_timestamp();

  UPDATE public.notification_outbox AS o
  SET status = CASE WHEN o.attempts >= o.max_attempts
                    THEN 'permanent_failure' ELSE 'retry_wait' END,
      next_attempt_at = CASE WHEN o.attempts < o.max_attempts
                             THEN clock_timestamp() ELSE o.next_attempt_at END,
      last_error_class = CASE WHEN o.attempts >= o.max_attempts
                              THEN 'lease_expired_final_attempt' ELSE o.last_error_class END,
      locked_at = NULL, locked_by = NULL, lease_expires_at = NULL
  WHERE o.status = 'leased'
    AND o.lease_expires_at <= clock_timestamp()
    AND o.deliver_before > clock_timestamp();

  RETURN QUERY
  WITH candidates AS (
    SELECT o.id
    FROM public.notification_outbox AS o
    WHERE o.channel IN ('email', 'telegram')
      AND o.kind <> 'legacy_notification'
      AND o.status IN ('pending', 'retry_wait')
      AND o.attempts < o.max_attempts
      AND o.next_attempt_at <= clock_timestamp()
      AND o.deliver_before > clock_timestamp()
    ORDER BY o.next_attempt_at, o.deliver_before, o.created_at, o.id
    FOR UPDATE SKIP LOCKED
    LIMIT p_batch_size
  ), claimed AS (
    UPDATE public.notification_outbox AS o
    SET status = 'leased',
        attempts = o.attempts + 1,
        locked_at = clock_timestamp(),
        locked_by = p_worker_id,
        lease_expires_at = clock_timestamp() + make_interval(secs => p_lease_seconds)
    FROM candidates AS c
    WHERE o.id = c.id
    RETURNING o.id, o.kind, o.channel, o.recipient, o.payload_safe_json,
      o.template_version, o.dedupe_key, o.provider_idempotency_key,
      o.attempts, o.max_attempts, o.deliver_before
  )
  SELECT * FROM claimed;
END
$$
"""
        )
    )
    _restrict_function(_CLAIM_SIGNATURE)


def downgrade() -> None:
    op.execute(
        sa.text(
            """
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM public.notification_outbox WHERE channel = 'telegram'
  ) THEN
    RAISE EXCEPTION 'cannot downgrade while Telegram notification rows exist';
  END IF;
END
$$
"""
        )
    )
    op.execute(
        sa.text(
            "DROP FUNCTION IF EXISTS public.claim_notification_outbox_batch_v62(text, integer, integer)"
        )
    )
    _replace_guard(telegram_enabled=False)
    op.drop_index("idx_notification_outbox_claimable", table_name="notification_outbox")
    op.drop_constraint(
        "ck_notification_outbox_telegram_kind_v62",
        "notification_outbox",
        type_="check",
    )
    op.drop_constraint(
        "ck_notification_outbox_channel_v62",
        "notification_outbox",
        type_="check",
    )
    op.create_check_constraint(
        "ck_notification_outbox_channel_v61",
        "notification_outbox",
        "channel = 'email'",
    )
    op.create_index(
        "idx_notification_outbox_claimable",
        "notification_outbox",
        ["next_attempt_at", "deliver_before", "created_at", "id"],
        postgresql_where=sa.text(
            "status IN ('pending', 'retry_wait') AND channel = 'email'"
        ),
    )
