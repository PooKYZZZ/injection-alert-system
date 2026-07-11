from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest


POSTGRES_URL = os.getenv("CYBERTRACE_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires an explicit disposable PostgreSQL URL",
)


@pytest.fixture(autouse=True)
def clear_outbox():
    if not POSTGRES_URL:
        yield
        return
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE public.auth_accounts CASCADE")
            cursor.execute("TRUNCATE TABLE public.notification_outbox")
    yield


def _insert_job(
    *,
    kind: str = "password_changed",
    status: str = "pending",
    attempts: int = 0,
    max_attempts: int = 5,
    deliver_before: datetime | None = None,
    lease_expires_at: datetime | None = None,
    recipient: str = "owner@example.test",
) -> str:
    key = f"lifecycle/{uuid4()}"
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.notification_outbox (
  kind, channel, recipient, status, attempts, max_attempts,
  next_attempt_at, payload_safe_json, template_version,
  dedupe_key, provider_idempotency_key, deliver_before, lease_expires_at
)
VALUES (
  %s, 'email', %s, %s, %s, %s,
  now(), '{"secret":"bearer-value"}'::jsonb, 1,
  %s, %s, COALESCE(%s, now() + interval '1 day'), %s
)
RETURNING id
""",
                (
                    kind,
                    recipient,
                    status,
                    attempts,
                    max_attempts,
                    key,
                    key,
                    deliver_before,
                    lease_expires_at,
                ),
            )
            return str(cursor.fetchone()[0])


def _claim(worker_id: str = "lifecycle-worker") -> list[tuple]:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM public.claim_notification_outbox_batch_v61(%s, %s, %s)",
                (worker_id, 1, 60),
            )
            return cursor.fetchall()


def test_superseded_and_legacy_jobs_are_not_claimable() -> None:
    cancelled_id = _insert_job(status="cancelled")
    legacy_id = _insert_job(kind="legacy_notification")

    assert _claim() == []

    with psycopg.connect(POSTGRES_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status, payload_safe_json FROM public.notification_outbox WHERE id IN (%s, %s) ORDER BY id",
                (cancelled_id, legacy_id),
            )
            rows = cursor.fetchall()
    assert all(status in {"cancelled", "permanent_failure"} for status, _ in rows)
    assert all(payload == {} for _, payload in rows)


def test_expired_job_is_reconciled_before_claim() -> None:
    job_id = _insert_job(
        deliver_before=datetime.now(timezone.utc) - timedelta(seconds=1)
    )

    assert _claim() == []

    with psycopg.connect(POSTGRES_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status, payload_safe_json, terminalized_at FROM public.notification_outbox WHERE id = %s",
                (job_id,),
            )
            status, payload, terminalized_at = cursor.fetchone()
    assert status == "expired"
    assert payload == {}
    assert terminalized_at is not None


def test_expired_final_lease_is_terminalized() -> None:
    job_id = _insert_job(
        status="leased",
        attempts=5,
        deliver_before=datetime.now(timezone.utc) + timedelta(minutes=5),
        lease_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )

    assert _claim() == []

    with psycopg.connect(POSTGRES_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT status, last_error_class, payload_safe_json FROM public.notification_outbox WHERE id = %s",
                (job_id,),
            )
            status, error_class, payload = cursor.fetchone()
    assert status == "permanent_failure"
    assert error_class == "lease_expired_final_attempt"
    assert payload == {}


def test_successful_terminal_transition_scrubs_payload_and_returns_deadline() -> None:
    job_id = _insert_job()
    claimed = _claim()

    assert len(claimed) == 1
    assert str(claimed[0][0]) == job_id
    assert claimed[0][-1] > datetime.now(timezone.utc)

    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT public.complete_notification_outbox_job_v61(%s, %s, %s)",
                (job_id, "lifecycle-worker", "provider-message-1"),
            )
            assert cursor.fetchone()[0] is True
            cursor.execute(
                "SELECT status, payload_safe_json, terminalized_at FROM public.notification_outbox WHERE id = %s",
                (job_id,),
            )
            status, payload, terminalized_at = cursor.fetchone()
    assert status == "sent"
    assert payload == {}
    assert terminalized_at is not None


def test_reset_token_supersession_cancels_pending_email_atomically() -> None:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (
  email, name, role, password_hash, password_set_at, email_verified_at, mfa_required
)
VALUES ('supersede@example.test', 'Supersede User', 'ANALYST', '$argon2id$test', now(), now(), true)
RETURNING id
"""
            )
            account_id = cursor.fetchone()[0]
            token_hash = 'e' * 64
            cursor.execute(
                """
INSERT INTO public.auth_reset_tokens (account_id, purpose, token_hash, status, expires_at)
VALUES (%s, 'password_reset', %s, 'pending', now() + interval '20 minutes')
""",
                (account_id, token_hash),
            )
            job_id = _insert_job(kind="password_reset", recipient="supersede@example.test")
            cursor.execute(
                "UPDATE public.auth_reset_tokens SET status = 'revoked' WHERE token_hash = %s",
                (token_hash,),
            )
            cursor.execute(
                "SELECT status, payload_safe_json FROM public.notification_outbox WHERE id = %s",
                (job_id,),
            )
            status, payload = cursor.fetchone()
    assert status == "cancelled"
    assert payload == {}
