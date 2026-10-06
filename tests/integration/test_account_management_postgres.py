from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import psycopg
import pytest
from psycopg.types.json import Jsonb

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


def _owner(email: str = "owner@example.test") -> str:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (
  email, name, role, password_hash, password_set_at,
  email_verified_at, mfa_required
)
VALUES (
  %s, 'SOC Owner', 'OWNER', '$argon2id$test',
  clock_timestamp(), clock_timestamp(), true
)
RETURNING id
""",
                (email,),
            )
            return str(cursor.fetchone()[0])


def _protected_payload() -> Jsonb:
    return Jsonb(
        {"ciphertext": "integration-test", "nonce": "test-nonce", "key_version": 1}
    )


def test_admin_create_derives_mfa_and_setup_token_is_consumed_once() -> None:
    admin_id = _admin()
    token_hash = "a" * 64
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
SELECT public.admin_create_auth_account_protected_v61(
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
                    _protected_payload(),
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
SELECT public.admin_request_managed_email_change_protected_v61(
  %s, %s, %s, %s, %s, %s, %s, %s
)
""",
                (
                    admin_id,
                    target_id,
                    "new-viewer@example.test",
                    token_hash,
                    datetime.now(timezone.utc) + timedelta(minutes=30),
                    _protected_payload(),
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
                "SELECT public.admin_set_account_enabled_v61(%s, %s, false)",
                (admin_id, target_id),
            )
            assert cursor.fetchone()[0] is True
            cursor.execute(
                "SELECT public.admin_set_account_enabled_v61(%s, %s, true)",
                (admin_id, target_id),
            )
            assert cursor.fetchone()[0] is True
            cursor.execute(
                "SELECT role, mfa_required, authz_version, disabled_at IS NOT NULL FROM public.auth_accounts WHERE id = %s",
                (target_id,),
            )
            assert cursor.fetchone() == ('ANALYST', True, 4, False)
            cursor.execute(
                """
SELECT count(*), count(DISTINCT provider_idempotency_key), bool_and(event_id IS NOT NULL)
FROM public.notification_outbox
WHERE recipient = 'target@example.test'
  AND kind IN ('account_disabled', 'account_reenabled')
"""
            )
            assert cursor.fetchone() == (2, 2, True)


def test_admin_cannot_manage_owners_or_promote_to_owner_but_owner_can_manage() -> None:
    admin_id = _admin()
    owner_id = _owner()
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (
  email, name, role, password_hash, password_set_at,
  email_verified_at, mfa_required
)
VALUES ('target@example.test', 'Target', 'ANALYST', '$argon2id$test',
  clock_timestamp(), clock_timestamp(), true)
RETURNING id
"""
            )
            target_id = cursor.fetchone()[0]
            with pytest.raises(psycopg.Error):
                cursor.execute(
                    "SELECT public.admin_change_account_role(%s, %s, 'OWNER')",
                    (admin_id, target_id),
                )
            with pytest.raises(psycopg.Error):
                cursor.execute(
                    "SELECT public.admin_change_account_role(%s, %s, 'ANALYST')",
                    (admin_id, owner_id),
                )
            with pytest.raises(psycopg.Error):
                cursor.execute(
                    "SELECT public.admin_set_account_enabled_v61(%s, %s, false)",
                    (admin_id, owner_id),
                )

            cursor.execute(
                "SELECT public.admin_change_account_role(%s, %s, 'ADMIN')",
                (owner_id, target_id),
            )
            assert cursor.fetchone()[0] is True
            cursor.execute(
                "SELECT role, mfa_required, authz_version FROM public.auth_accounts WHERE id = %s",
                (target_id,),
            )
            assert cursor.fetchone() == ('ADMIN', True, 2)


@pytest.mark.parametrize("transition", ["demote", "disable"])
def test_concurrent_last_owner_guard_preserves_one_enabled_owner(
    transition: str,
) -> None:
    first_owner = _owner("owner-one@example.test")
    second_owner = _owner("owner-two@example.test")
    barrier = threading.Barrier(2)

    def change_owner(target_id: str) -> bool:
        try:
            with psycopg.connect(POSTGRES_URL) as connection:
                barrier.wait(timeout=5)
                with connection.cursor() as cursor:
                    # Exercise the database guard and the following mutation in
                    # the same transaction, as the protected RPCs do.
                    cursor.execute(
                        "SELECT public.assert_last_enabled_owner(%s)",
                        (target_id,),
                    )
                    if transition == "demote":
                        cursor.execute(
                            "UPDATE public.auth_accounts SET role = 'ANALYST' "
                            "WHERE id = %s",
                            (target_id,),
                        )
                    else:
                        cursor.execute(
                            "UPDATE public.auth_accounts "
                            "SET disabled_at = clock_timestamp() WHERE id = %s",
                            (target_id,),
                        )
                    connection.commit()
                    return True
        except (psycopg.Error, threading.BrokenBarrierError):
            return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = [
            executor.submit(change_owner, second_owner),
            executor.submit(change_owner, first_owner),
        ]
        outcomes = [result.result(timeout=10) for result in results]

    assert outcomes.count(True) == 1
    assert outcomes.count(False) == 1
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM public.auth_accounts "
                "WHERE role = 'OWNER' AND disabled_at IS NULL"
            )
            assert cursor.fetchone()[0] == 1


def test_last_enabled_owner_guard_rejects_removing_the_only_owner() -> None:
    only_owner = _owner()
    with psycopg.connect(POSTGRES_URL) as connection:
        with connection.cursor() as cursor:
            with pytest.raises(psycopg.Error) as error:
                cursor.execute(
                    "SELECT public.assert_last_enabled_owner(%s)",
                    (only_owner,),
                )
            assert error.value.sqlstate == "23514"
            assert "LAST_ENABLED_OWNER" in str(error.value)


def test_last_enabled_owner_guard_fails_closed_outside_read_committed() -> None:
    only_owner = _owner()
    with psycopg.connect(POSTGRES_URL) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            with pytest.raises(psycopg.Error) as error:
                cursor.execute(
                    "SELECT public.assert_last_enabled_owner(%s)",
                    (only_owner,),
                )
            assert error.value.sqlstate == "40001"
            assert "LAST_OWNER_GUARD_REQUIRES_READ_COMMITTED" in str(error.value)


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
SELECT public.admin_request_managed_email_change_protected_v61(
  %s, %s, %s, %s, %s, %s, %s, %s
)
""",
                    (
                        admin_id,
                        target_id,
                        'admin@example.test',
                        'c' * 64,
                        datetime.now(timezone.utc) + timedelta(minutes=30),
                        _protected_payload(),
                        key,
                        key,
                    ),
                )
