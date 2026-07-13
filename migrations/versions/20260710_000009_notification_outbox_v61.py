"""Extend notification outbox for V6.1 leasing and Resend delivery.

Revision ID: 20260710_000009
Revises: 20260704_000008
Create Date: 2026-07-10 18:00:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260710_000009"
down_revision = "20260704_000008"
branch_labels = None
depends_on = None


_FUNCTION_SIGNATURES = (
    "public.claim_notification_outbox_batch(text, integer, integer)",
    "public.complete_notification_outbox_job(uuid, text, text)",
    "public.fail_notification_outbox_job(uuid, text, text, boolean, integer)",
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
    op.add_column(
        "notification_outbox",
        sa.Column(
            "kind", sa.Text(), nullable=False, server_default="legacy_notification"
        ),
    )
    op.add_column(
        "notification_outbox",
        sa.Column(
            "template_version", sa.Integer(), nullable=False, server_default="1"
        ),
    )
    op.add_column(
        "notification_outbox",
        sa.Column("provider_idempotency_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "notification_outbox",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "notification_outbox", sa.Column("last_error_class", sa.Text())
    )
    op.add_column(
        "notification_outbox", sa.Column("provider_message_id", sa.Text())
    )

    op.execute(
        sa.text(
            """
UPDATE public.notification_outbox
SET provider_idempotency_key = COALESCE(
  dedupe_key,
  'legacy/' || id::text
)
WHERE provider_idempotency_key IS NULL
"""
        )
    )
    op.alter_column(
        "notification_outbox", "provider_idempotency_key", nullable=False
    )
    op.create_index(
        "notification_outbox_provider_idempotency_unique",
        "notification_outbox",
        ["provider_idempotency_key"],
        unique=True,
    )
    op.create_check_constraint(
        "ck_notification_outbox_template_version",
        "notification_outbox",
        "template_version >= 1",
    )
    op.create_check_constraint(
        "ck_notification_outbox_provider_key_length",
        "notification_outbox",
        "char_length(provider_idempotency_key) BETWEEN 1 AND 256",
    )

    op.drop_constraint(
        "ck_notification_outbox_status", "notification_outbox", type_="check"
    )
    op.execute(
        sa.text(
            """
UPDATE public.notification_outbox
SET lease_expires_at = CASE
      WHEN status = 'sending' THEN clock_timestamp()
      ELSE lease_expires_at
    END,
    status = CASE status
      WHEN 'sending' THEN 'leased'
      WHEN 'failed' THEN 'retry_wait'
      WHEN 'skipped' THEN 'permanent_failure'
      ELSE status
    END
"""
        )
    )
    op.create_check_constraint(
        "ck_notification_outbox_status_v61",
        "notification_outbox",
        "status IN ('pending', 'leased', 'retry_wait', 'sent', 'permanent_failure')",
    )
    op.drop_index("idx_notification_outbox_pending", table_name="notification_outbox")
    op.create_index(
        "idx_notification_outbox_claimable",
        "notification_outbox",
        ["next_attempt_at", "created_at", "id"],
        postgresql_where=sa.text(
            "status IN ('pending', 'retry_wait') OR status = 'leased'"
        ),
    )

    op.execute(
        sa.text(
            """
CREATE FUNCTION public.claim_notification_outbox_batch(
  p_worker_id text,
  p_batch_size integer DEFAULT 10,
  p_lease_seconds integer DEFAULT 60
)
RETURNS TABLE (
  id uuid,
  kind text,
  recipient text,
  payload_safe_json jsonb,
  template_version integer,
  dedupe_key text,
  provider_idempotency_key text,
  attempts integer,
  max_attempts integer
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

  RETURN QUERY
  WITH candidates AS (
    SELECT o.id
    FROM public.notification_outbox AS o
    WHERE o.attempts < o.max_attempts
      AND (
        (o.status IN ('pending', 'retry_wait') AND o.next_attempt_at <= clock_timestamp())
        OR
        (o.status = 'leased' AND o.lease_expires_at <= clock_timestamp())
      )
    ORDER BY o.next_attempt_at, o.created_at, o.id
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
    RETURNING o.id, o.kind, o.recipient, o.payload_safe_json,
      o.template_version, o.dedupe_key, o.provider_idempotency_key,
      o.attempts, o.max_attempts
  )
  SELECT * FROM claimed;
END;
$$
"""
        )
    )
    op.execute(
        sa.text(
            """
CREATE FUNCTION public.complete_notification_outbox_job(
  p_job_id uuid,
  p_worker_id text,
  p_provider_message_id text
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  changed integer;
BEGIN
  IF p_provider_message_id IS NULL OR char_length(p_provider_message_id) NOT BETWEEN 1 AND 256 THEN
    RAISE EXCEPTION 'invalid provider message id';
  END IF;
  UPDATE public.notification_outbox
  SET status = 'sent', sent_at = clock_timestamp(),
      provider_message_id = p_provider_message_id,
      locked_at = NULL, locked_by = NULL, lease_expires_at = NULL,
      last_error_class = NULL
  WHERE id = p_job_id AND status = 'leased' AND locked_by = p_worker_id;
  GET DIAGNOSTICS changed = ROW_COUNT;
  RETURN changed = 1;
END;
$$
"""
        )
    )
    op.execute(
        sa.text(
            """
CREATE FUNCTION public.fail_notification_outbox_job(
  p_job_id uuid,
  p_worker_id text,
  p_error_class text,
  p_retryable boolean,
  p_retry_delay_seconds integer
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  changed integer;
BEGIN
  IF p_error_class IS NULL OR p_error_class !~ '^[a-z0-9_]{1,64}$' THEN
    RAISE EXCEPTION 'invalid error class';
  END IF;
  IF p_retry_delay_seconds NOT BETWEEN 0 AND 86400 THEN
    RAISE EXCEPTION 'invalid retry delay';
  END IF;
  UPDATE public.notification_outbox
  SET status = CASE
        WHEN p_retryable AND attempts < max_attempts THEN 'retry_wait'
        ELSE 'permanent_failure'
      END,
      next_attempt_at = CASE
        WHEN p_retryable AND attempts < max_attempts
          THEN clock_timestamp() + make_interval(secs => p_retry_delay_seconds)
        ELSE next_attempt_at
      END,
      last_error_class = p_error_class,
      last_error_code = NULL,
      locked_at = NULL, locked_by = NULL, lease_expires_at = NULL
  WHERE id = p_job_id AND status = 'leased' AND locked_by = p_worker_id;
  GET DIAGNOSTICS changed = ROW_COUNT;
  RETURN changed = 1;
END;
$$
"""
        )
    )

    for signature in _FUNCTION_SIGNATURES:
        _restrict_function(signature)


def downgrade() -> None:
    op.execute(
        sa.text(
            "DROP FUNCTION IF EXISTS public.fail_notification_outbox_job(uuid, text, text, boolean, integer)"
        )
    )
    op.execute(
        sa.text(
            "DROP FUNCTION IF EXISTS public.complete_notification_outbox_job(uuid, text, text)"
        )
    )
    op.execute(
        sa.text(
            "DROP FUNCTION IF EXISTS public.claim_notification_outbox_batch(text, integer, integer)"
        )
    )

    op.drop_index(
        "idx_notification_outbox_claimable", table_name="notification_outbox"
    )
    op.drop_constraint(
        "ck_notification_outbox_status_v61",
        "notification_outbox",
        type_="check",
    )
    op.execute(
        sa.text(
            """
UPDATE public.notification_outbox
SET status = CASE status
  WHEN 'leased' THEN 'sending'
  WHEN 'retry_wait' THEN 'pending'
  WHEN 'permanent_failure' THEN 'failed'
  ELSE status
END
"""
        )
    )
    op.create_check_constraint(
        "ck_notification_outbox_status",
        "notification_outbox",
        "status IN ('pending', 'sending', 'sent', 'failed', 'skipped')",
    )
    op.create_index(
        "idx_notification_outbox_pending",
        "notification_outbox",
        ["status", "next_attempt_at", "created_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.drop_constraint(
        "ck_notification_outbox_provider_key_length",
        "notification_outbox",
        type_="check",
    )
    op.drop_constraint(
        "ck_notification_outbox_template_version",
        "notification_outbox",
        type_="check",
    )
    op.drop_index(
        "notification_outbox_provider_idempotency_unique",
        table_name="notification_outbox",
    )
    for column in (
        "provider_message_id",
        "last_error_class",
        "lease_expires_at",
        "provider_idempotency_key",
        "template_version",
        "kind",
    ):
        op.drop_column("notification_outbox", column)
