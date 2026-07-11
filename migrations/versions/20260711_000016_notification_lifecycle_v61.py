"""Harden notification lifecycle, deadlines, and terminal payload retention.

This revision is additive.  The versioned outbox functions are used by the
current worker while the original functions remain available to older
application versions during the staged rollout.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260711_000016"
down_revision = "20260711_000015"
branch_labels = None
depends_on = None


SUPPORTED_KINDS = (
    "legacy_notification",
    "password_setup",
    "password_reset",
    "password_changed",
    "email_verification",
    "email_recovery_otp",
    "email_recovery_completed",
    "totp_enrolled",
    "totp_replaced",
    "backup_code_used",
    "admin_mfa_reset",
    "account_disabled",
    "account_reenabled",
    "managed_email_changed",
    "threat_detected",
)


_VERSIONED_FUNCTION_SIGNATURES = (
    "public.claim_notification_outbox_batch_v61(text, integer, integer)",
    "public.complete_notification_outbox_job_v61(uuid, text, text)",
    "public.fail_notification_outbox_job_v61(uuid, text, text, boolean, integer)",
    "public.cancel_notification_outbox_jobs_v61(uuid, text)",
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
            "deliver_before",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now() + interval '24 hours'"),
        ),
    )
    op.add_column(
        "notification_outbox",
        sa.Column("terminalized_at", sa.DateTime(timezone=True)),
    )

    supported_sql = ", ".join(f"'{kind}'" for kind in SUPPORTED_KINDS)
    op.execute(
        sa.text(
            f"""
-- Rows without a repository-backed template are retained as history but can
-- never be delivered.  Normalize unknown legacy kinds before adding the
-- registry constraint.
UPDATE public.notification_outbox
SET kind = 'legacy_notification',
    status = CASE WHEN status = 'sent' THEN 'sent' ELSE 'permanent_failure' END,
    last_error_class = COALESCE(last_error_class, 'unsupported_notification_kind'),
    payload_safe_json = '{{}}'::jsonb,
    terminalized_at = COALESCE(terminalized_at, clock_timestamp())
WHERE kind IS NULL OR kind NOT IN ({supported_sql});

-- The current worker is email-only.  Historical non-email rows are
-- terminalized before the current-scope channel constraint is installed.
UPDATE public.notification_outbox
SET channel = 'email',
    status = CASE WHEN status = 'sent' THEN 'sent' ELSE 'permanent_failure' END,
    last_error_class = COALESCE(last_error_class, 'unsupported_notification_channel'),
    payload_safe_json = '{{}}'::jsonb,
    terminalized_at = COALESCE(terminalized_at, clock_timestamp())
WHERE channel <> 'email';

UPDATE public.notification_outbox
SET payload_safe_json = '{{}}'::jsonb,
    terminalized_at = COALESCE(terminalized_at, clock_timestamp())
WHERE status IN ('sent', 'permanent_failure');
"""
        )
    )

    op.drop_constraint(
        "ck_notification_outbox_channel", "notification_outbox", type_="check"
    )
    op.create_check_constraint(
        "ck_notification_outbox_channel_v61",
        "notification_outbox",
        "channel = 'email'",
    )
    op.drop_constraint(
        "ck_notification_outbox_status_v61", "notification_outbox", type_="check"
    )
    op.create_check_constraint(
        "ck_notification_outbox_status_v61",
        "notification_outbox",
        "status IN ('pending', 'leased', 'retry_wait', 'sent', 'permanent_failure', 'cancelled', 'expired')",
    )
    op.create_check_constraint(
        "ck_notification_outbox_kind_v61",
        "notification_outbox",
        f"kind IN ({supported_sql})",
    )

    op.drop_index("idx_notification_outbox_claimable", table_name="notification_outbox")
    op.create_index(
        "idx_notification_outbox_claimable",
        "notification_outbox",
        ["next_attempt_at", "deliver_before", "created_at", "id"],
        postgresql_where=sa.text(
            "status IN ('pending', 'retry_wait') AND channel = 'email'"
        ),
    )

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
    NEW.payload_safe_json := '{}'::jsonb;
    NEW.terminalized_at := COALESCE(NEW.terminalized_at, clock_timestamp());
  END IF;
  RETURN NEW;
END
$$;

CREATE TRIGGER notification_outbox_guard_v61
BEFORE INSERT OR UPDATE ON public.notification_outbox
FOR EACH ROW EXECUTE FUNCTION public.notification_outbox_guard_v61();

CREATE OR REPLACE FUNCTION public.cancel_notification_outbox_jobs_v61(
  p_account_id uuid,
  p_kind text
) RETURNS integer
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
DECLARE
  v_changed integer;
BEGIN
  IF p_kind NOT IN ('password_setup', 'password_reset', 'email_verification', 'email_recovery_otp') THEN
    RAISE EXCEPTION 'unsupported cancellation kind';
  END IF;
  UPDATE public.notification_outbox AS n
  SET status = 'cancelled', last_error_class = 'superseded'
  WHERE n.kind = p_kind
    AND n.status IN ('pending', 'retry_wait')
    AND n.recipient IN (
      SELECT a.email FROM public.auth_accounts AS a WHERE a.id = p_account_id
      UNION
      SELECT a.pending_email FROM public.auth_accounts AS a WHERE a.id = p_account_id
    );
  GET DIAGNOSTICS v_changed = ROW_COUNT;
  RETURN v_changed;
END
$$;

CREATE OR REPLACE FUNCTION public.notification_outbox_reset_token_supersession_v61()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
  IF OLD.status = 'pending' AND NEW.status <> 'pending' THEN
    IF NEW.purpose IN ('password_setup', 'password_reset', 'email_verification') THEN
      PERFORM public.cancel_notification_outbox_jobs_v61(
        NEW.account_id,
        NEW.purpose
      );
    END IF;
  END IF;
  RETURN NEW;
END
$$;

CREATE TRIGGER auth_reset_tokens_notification_supersession_v61
AFTER UPDATE OF status ON public.auth_reset_tokens
FOR EACH ROW EXECUTE FUNCTION public.notification_outbox_reset_token_supersession_v61();

CREATE OR REPLACE FUNCTION public.notification_outbox_email_otp_supersession_v61()
RETURNS trigger
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = ''
AS $$
BEGIN
  IF OLD.status = 'pending' AND NEW.status <> 'pending' THEN
    UPDATE public.notification_outbox AS n
    SET status = 'cancelled', last_error_class = 'superseded'
    WHERE n.kind = 'email_recovery_otp'
      AND n.recipient = NEW.email_to
      AND n.status IN ('pending', 'retry_wait');
  END IF;
  RETURN NEW;
END
$$;

CREATE TRIGGER auth_email_otp_notification_supersession_v61
AFTER UPDATE OF status ON public.auth_email_otp_challenges
FOR EACH ROW EXECUTE FUNCTION public.notification_outbox_email_otp_supersession_v61();
"""
        )
    )

    op.execute(
        sa.text(
            f"""
CREATE FUNCTION public.claim_notification_outbox_batch_v61(
  p_worker_id text,
  p_batch_size integer DEFAULT 1,
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

  -- Deadline reconciliation runs before candidate selection.  A job whose
  -- lease expires on its last attempt is terminalized rather than stranded.
  UPDATE public.notification_outbox AS o
  SET status = 'expired',
      last_error_class = 'delivery_deadline_expired',
      locked_at = NULL,
      locked_by = NULL,
      lease_expires_at = NULL
  WHERE o.status IN ('pending', 'retry_wait', 'leased')
    AND o.deliver_before <= clock_timestamp();

  UPDATE public.notification_outbox AS o
  SET status = CASE WHEN o.attempts >= o.max_attempts
                    THEN 'permanent_failure' ELSE 'retry_wait' END,
      next_attempt_at = CASE WHEN o.attempts < o.max_attempts
                             THEN clock_timestamp() ELSE o.next_attempt_at END,
      last_error_class = CASE WHEN o.attempts >= o.max_attempts
                              THEN 'lease_expired_final_attempt' ELSE o.last_error_class END,
      locked_at = NULL,
      locked_by = NULL,
      lease_expires_at = NULL
  WHERE o.status = 'leased'
    AND o.lease_expires_at <= clock_timestamp()
    AND o.deliver_before > clock_timestamp();

  RETURN QUERY
  WITH candidates AS (
    SELECT o.id
    FROM public.notification_outbox AS o
    WHERE o.channel = 'email'
      AND o.kind IN ({supported_sql})
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
    RETURNING o.id, o.kind, o.recipient, o.payload_safe_json,
      o.template_version, o.dedupe_key, o.provider_idempotency_key,
      o.attempts, o.max_attempts, o.deliver_before
  )
  SELECT * FROM claimed;
END
$$;

CREATE FUNCTION public.complete_notification_outbox_job_v61(
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
  IF p_worker_id IS NULL OR char_length(p_worker_id) NOT BETWEEN 1 AND 128
     OR p_provider_message_id IS NULL
     OR char_length(p_provider_message_id) > 256
     OR p_provider_message_id !~ '^[A-Za-z0-9_-]+$' THEN
    RAISE EXCEPTION 'invalid completion';
  END IF;

  UPDATE public.notification_outbox AS o
  SET status = 'expired', last_error_class = 'delivery_deadline_expired',
      locked_at = NULL, locked_by = NULL, lease_expires_at = NULL
  WHERE o.id = p_job_id AND o.status = 'leased' AND o.locked_by = p_worker_id
    AND o.deliver_before <= clock_timestamp();
  GET DIAGNOSTICS changed = ROW_COUNT;
  IF changed = 1 THEN RETURN false; END IF;

  UPDATE public.notification_outbox AS o
  SET status = 'sent', sent_at = clock_timestamp(),
      provider_message_id = p_provider_message_id,
      locked_at = NULL, locked_by = NULL, lease_expires_at = NULL,
      last_error_class = NULL
  WHERE o.id = p_job_id AND o.status = 'leased' AND o.locked_by = p_worker_id
    AND o.deliver_before > clock_timestamp();
  GET DIAGNOSTICS changed = ROW_COUNT;
  RETURN changed = 1;
END
$$;

CREATE FUNCTION public.fail_notification_outbox_job_v61(
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
  IF p_worker_id IS NULL OR char_length(p_worker_id) NOT BETWEEN 1 AND 128
     OR p_error_class IS NULL OR p_error_class !~ '^[a-z0-9_]{{1,64}}$'
     OR p_retry_delay_seconds NOT BETWEEN 0 AND 86400 THEN
    RAISE EXCEPTION 'invalid failure';
  END IF;
  UPDATE public.notification_outbox AS o
  SET status = CASE
        WHEN o.deliver_before <= clock_timestamp()
          OR (p_retryable AND clock_timestamp() + make_interval(secs => p_retry_delay_seconds) >= o.deliver_before)
          THEN 'expired'
        WHEN p_retryable AND o.attempts < o.max_attempts THEN 'retry_wait'
        ELSE 'permanent_failure'
      END,
      next_attempt_at = CASE
        WHEN p_retryable AND o.attempts < o.max_attempts
             AND clock_timestamp() + make_interval(secs => p_retry_delay_seconds) < o.deliver_before
          THEN clock_timestamp() + make_interval(secs => p_retry_delay_seconds)
        ELSE o.next_attempt_at
      END,
      last_error_class = CASE
        WHEN o.deliver_before <= clock_timestamp()
          OR (p_retryable AND clock_timestamp() + make_interval(secs => p_retry_delay_seconds) >= o.deliver_before)
          THEN 'delivery_deadline_expired'
        ELSE p_error_class
      END,
      locked_at = NULL, locked_by = NULL, lease_expires_at = NULL
  WHERE o.id = p_job_id AND o.status = 'leased' AND o.locked_by = p_worker_id;
  GET DIAGNOSTICS changed = ROW_COUNT;
  RETURN changed = 1;
END
$$;
"""
        )
    )

    for signature in _VERSIONED_FUNCTION_SIGNATURES:
        _restrict_function(signature)


def downgrade() -> None:
    op.execute(
        sa.text(
            """
DROP TRIGGER IF EXISTS auth_email_otp_notification_supersession_v61 ON public.auth_email_otp_challenges;
DROP TRIGGER IF EXISTS auth_reset_tokens_notification_supersession_v61 ON public.auth_reset_tokens;
DROP TRIGGER IF EXISTS notification_outbox_guard_v61 ON public.notification_outbox;
DROP FUNCTION IF EXISTS public.notification_outbox_email_otp_supersession_v61();
DROP FUNCTION IF EXISTS public.notification_outbox_reset_token_supersession_v61();
DROP FUNCTION IF EXISTS public.notification_outbox_guard_v61();
"""
        )
    )
    for signature in reversed(_VERSIONED_FUNCTION_SIGNATURES):
        op.execute(sa.text(f"DROP FUNCTION IF EXISTS {signature}"))

    op.execute(
        sa.text(
            """
UPDATE public.notification_outbox
SET status = CASE status
  WHEN 'cancelled' THEN 'permanent_failure'
  WHEN 'expired' THEN 'permanent_failure'
  ELSE status
END
WHERE status IN ('cancelled', 'expired');
"""
        )
    )
    op.drop_index("idx_notification_outbox_claimable", table_name="notification_outbox")
    op.drop_constraint(
        "ck_notification_outbox_kind_v61", "notification_outbox", type_="check"
    )
    op.drop_constraint(
        "ck_notification_outbox_channel_v61", "notification_outbox", type_="check"
    )
    op.drop_constraint(
        "ck_notification_outbox_status_v61", "notification_outbox", type_="check"
    )
    op.create_check_constraint(
        "ck_notification_outbox_channel",
        "notification_outbox",
        "channel IN ('email', 'telegram')",
    )
    op.create_check_constraint(
        "ck_notification_outbox_status_v61",
        "notification_outbox",
        "status IN ('pending', 'leased', 'retry_wait', 'sent', 'permanent_failure')",
    )
    op.create_index(
        "idx_notification_outbox_claimable",
        "notification_outbox",
        ["next_attempt_at", "created_at", "id"],
        postgresql_where=sa.text(
            "status IN ('pending', 'retry_wait') OR status = 'leased'"
        ),
    )
    op.drop_column("notification_outbox", "terminalized_at")
    op.drop_column("notification_outbox", "deliver_before")
