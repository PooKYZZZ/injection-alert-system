from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest


POSTGRES_URL = os.getenv("CYBERTRACE_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires an explicit disposable PostgreSQL URL",
)


@pytest.fixture(autouse=True)
def clear_outbox() -> Iterator[None]:
    if not POSTGRES_URL:
        yield
        return
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE public.notification_outbox")
    yield


def _insert_job(key: str) -> str:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.notification_outbox (
  kind, channel, recipient, status, payload_safe_json,
  template_version, dedupe_key, provider_idempotency_key
)
VALUES (
  'password_changed', 'email', 'owner@example.test', 'pending',
  '{}'::jsonb, 1, %s, %s
)
RETURNING id
""",
                (key, key),
            )
            return str(cursor.fetchone()[0])


def test_two_workers_never_claim_the_same_outbox_job() -> None:
    key = f"postgres-race/{uuid4()}"
    job_id = _insert_job(key)
    barrier = threading.Barrier(2)

    def claim(worker_id: str) -> list[str]:
        with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
            barrier.wait(timeout=5)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT id FROM public.claim_notification_outbox_batch(%s, %s, %s)",
                    (worker_id, 1, 60),
                )
                return [str(row[0]) for row in cursor.fetchall()]

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(claim, "worker-a")
        second = executor.submit(claim, "worker-b")
        claims = first.result(timeout=10) + second.result(timeout=10)

    assert claims == [job_id]


def test_outbox_claim_rolls_back_with_its_transaction() -> None:
    key = f"postgres-rollback/{uuid4()}"
    job_id = _insert_job(key)

    with psycopg.connect(POSTGRES_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM public.claim_notification_outbox_batch(%s, %s, %s)",
                ("rollback-worker", 1, 60),
            )
            assert str(cursor.fetchone()[0]) == job_id
        connection.rollback()

    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM public.claim_notification_outbox_batch(%s, %s, %s)",
                ("next-worker", 1, 60),
            )
            assert str(cursor.fetchone()[0]) == job_id
