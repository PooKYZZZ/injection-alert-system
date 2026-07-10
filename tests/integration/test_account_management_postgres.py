from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
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
def clear_auth_state() -> Iterator[None]:
    if not POSTGRES_URL:
        yield
        return
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE public.auth_accounts CASCADE")
            cursor.execute("TRUNCATE TABLE public.security_events CASCADE")
            cursor.execute("TRUNCATE TABLE public.notification_outbox CASCADE")
    yield


def _admin() -> str:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (
  email, name, role, password_hash, password_set_at,
  email_verified_at, mfa_required
)
VALUES (
  'admin@example.test', 'SOC Admin', 'ADMIN', '$argon2id$test',
  clock_timestamp(), clock_timestamp(), true
)
RETURNING id
"""
            )
            return str(cursor.fetchone()[0])


def test_admin_create_derives_mfa_and_setup_token_is_consumed_once() -> None:
    admin_id = _admin()
    token_hash = "a" * 64
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
SELECT public.admin_create_auth_account(
  %s, %s, %s, %s, %s, %s, %s, %s, %s
)
""",
                (
                    admin_id,
                    "analyst@example.test",
                    "SOC Analyst",
                    "ANALYST",
                    token_hash,
                    expires_at,
                    "https://dashboard.example.test/setup-password?token=opaque",
                    "setup/test-1",
                    "setup/test-1",
                ),
            )
            target_id = str(cursor.fetchone()[0])
            cursor.execute(
                "SELECT mfa_required, password_hash, email_verified_at FROM public.auth_accounts WHERE id = %s",
                (target_id,),
            )
            assert cursor.fetchone() == (True, None, None)

    barrier = threading.Barrier(2)

    def consume() -> bool:
        try:
            with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
                barrier.wait(timeout=5)
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT public.consume_password_setup_token(%s, %s)",
                        (token_hash, "$argon2id$approved-test-hash"),
                    )
                    return str(cursor.fetchone()[0]) == target_id
        except psycopg.Error:
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(consume), executor.submit(consume)]
        results = [future.result(timeout=10) for future in futures]

    assert results.count(True) == 1
    assert results.count(False) == 1


def test_managed_email_activation_invalidates_sessions_and_preserves_old_notice() -> None:
    admin_id = _admin()
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (
  email, name, role, password_hash, password_set_at,
  email_verified_at, mfa_required
)
VALUES ('viewer@example.test', 'Viewer', 'VIEWER', '$argon2id$test',
  clock_timestamp(), clock_timestamp(), false)
RETURNING id, authz_version
"""
            )
            target_id, initial_version = cursor.fetchone()
            token_hash = "b" * 64
            key = f"email/{uuid4()}"
            cursor.execute(
                """
SELECT public.admin_request_managed_email_change(
  %s, %s, %s, %s, %s, %s, %s, %s
)
""",
                (
                    admin_id,
                    target_id,
                    "new-viewer@example.test",
                    token_hash,
                    datetime.now(timezone.utc) + timedelta(minutes=30),
                    "https://dashboard.example.test/verify-email?token=opaque",
                    key,
                    key,
                ),
            )
            assert cursor.fetchone()[0] is True
            cursor.execute(
                "SELECT public.activate_verified_managed_email(%s)",
                (token_hash,),
            )
            assert cursor.fetchone()[0] == target_id
            cursor.execute(
                "SELECT email, pending_email, authz_version FROM public.auth_accounts WHERE id = %s",
                (target_id,),
            )
            assert cursor.fetchone() == (
                "new-viewer@example.test",
                None,
                initial_version + 1,
            )
            cursor.execute(
                "SELECT recipient, kind FROM public.notification_outbox WHERE kind = 'managed_email_changed'"
            )
            assert cursor.fetchone() == (
                "viewer@example.test",
                "managed_email_changed",
            )


def test_role_and_status_changes_derive_mfa_and_increment_authz_version() -> None:
    admin_id = _admin()
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (
  email, name, role, password_hash, password_set_at,
  email_verified_at, mfa_required
)
VALUES ('target@example.test', 'Target', 'VIEWER', '$argon2id$test',
  clock_timestamp(), clock_timestamp(), false)
RETURNING id
"""
            )
            target_id = cursor.fetchone()[0]
            cursor.execute(
                "SELECT public.admin_change_account_role(%s, %s, 'ANALYST')",
                (admin_id, target_id),
            )
            assert cursor.fetchone()[0] is True
            cursor.execute(
                "SELECT public.admin_set_account_enabled(%s, %s, false)",
                (admin_id, target_id),
            )
            assert cursor.fetchone()[0] is True
            cursor.execute(
                "SELECT role, mfa_required, authz_version, disabled_at IS NOT NULL FROM public.auth_accounts WHERE id = %s",
                (target_id,),
            )
            assert cursor.fetchone() == ('ANALYST', True, 3, True)


def test_managed_email_request_rejects_another_accounts_current_email() -> None:
    admin_id = _admin()
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (
  email, name, role, password_hash, password_set_at,
  email_verified_at, mfa_required
)
VALUES ('viewer@example.test', 'Viewer', 'VIEWER', '$argon2id$test',
  clock_timestamp(), clock_timestamp(), false)
RETURNING id
"""
            )
            target_id = cursor.fetchone()[0]
            key = f"collision/{uuid4()}"
            with pytest.raises(psycopg.Error):
                cursor.execute(
                    """
SELECT public.admin_request_managed_email_change(
  %s, %s, %s, %s, %s, %s, %s, %s
)
""",
                    (
                        admin_id,
                        target_id,
                        'admin@example.test',
                        'c' * 64,
                        datetime.now(timezone.utc) + timedelta(minutes=30),
                        'https://dashboard.example.test/verify-email?token=opaque',
                        key,
                        key,
                    ),
                )
