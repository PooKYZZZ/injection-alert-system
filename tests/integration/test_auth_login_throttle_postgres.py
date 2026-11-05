from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import psycopg
import pytest

POSTGRES_URL = os.getenv('CYBERTRACE_POSTGRES_TEST_URL')
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason='requires an explicit disposable PostgreSQL URL',
)


def account() -> str:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (email, name, role)
VALUES (%s, 'Throttle test', 'ANALYST')
RETURNING id
""",
                (f'{uuid4()}@example.test',),
            )
            return str(cursor.fetchone()[0])


def begin(
    account_id: str,
    *,
    enabled: bool = True,
    verified: bool = False,
    attempt_id: str | None = None,
) -> tuple[bool, str | None, int, str | None]:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
SELECT * FROM public.begin_auth_login_attempt_v1(
  %s, %s, %s, %s, 3, 5, 300, 300
)
""",
                (account_id, attempt_id or str(uuid4()), enabled, verified),
            )
            row = cursor.fetchone()
            return bool(row[0]), row[1], int(row[2]), str(row[3]) if row[3] else None


def complete(account_id: str, attempt_id: str, outcome: str) -> tuple[bool, int, bool]:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
SELECT * FROM public.complete_auth_login_attempt_v1(
  %s, %s, %s, 5, 300, 300
)
""",
                (account_id, attempt_id, outcome),
            )
            row = cursor.fetchone()
            return bool(row[0]), int(row[1]), bool(row[2])


def delete_account(account_id: str) -> None:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'DELETE FROM public.auth_accounts WHERE id = %s',
                (account_id,),
            )


def test_threshold_requires_turnstile_after_three_failures_and_cooldown_after_five() -> None:
    account_id = account()
    try:
        for expected_count in (1, 2, 3):
            allowed, _, _, attempt_id = begin(account_id)
            assert allowed and attempt_id
            completed, failure_count, cooldown = complete(
                account_id, attempt_id, 'failure'
            )
            assert completed and failure_count == expected_count
            assert not cooldown

        allowed, reason, failure_count, attempt_id = begin(account_id)
        assert not allowed and reason == 'VERIFICATION_REQUIRED'
        assert failure_count == 3 and attempt_id is None

        for expected_count in (4, 5):
            allowed, _, _, attempt_id = begin(
                account_id, verified=True
            )
            assert allowed and attempt_id
            completed, failure_count, cooldown = complete(
                account_id, attempt_id, 'failure'
            )
            assert completed and failure_count == expected_count
            assert cooldown is (expected_count == 5)

        allowed, reason, _, _ = begin(account_id, verified=True)
        assert not allowed and reason == 'IDENTIFIER_THROTTLED'
    finally:
        delete_account(account_id)


def test_disabled_turnstile_preserves_the_five_failure_cooldown() -> None:
    account_id = account()
    try:
        for expected_count in range(1, 6):
            allowed, reason, _, attempt_id = begin(
                account_id,
                enabled=False,
            )
            assert allowed and reason is None and attempt_id
            completed, failure_count, cooldown = complete(
                account_id, attempt_id, 'failure'
            )
            assert completed and failure_count == expected_count
            assert cooldown is (expected_count == 5)

        allowed, reason, failure_count, attempt_id = begin(
            account_id,
            enabled=False,
        )
        assert not allowed and reason == 'IDENTIFIER_THROTTLED'
        assert failure_count == 5 and attempt_id is None
    finally:
        delete_account(account_id)


def test_concurrent_admission_is_atomic_and_caps_reserved_password_checks() -> None:
    account_id = account()
    try:
        with ThreadPoolExecutor(max_workers=12) as executor:
            results = list(executor.map(lambda _: begin(account_id, enabled=False), range(12)))

        allowed = [result for result in results if result[0]]
        blocked = [result for result in results if not result[0]]
        assert len(allowed) == 5
        assert all(result[1] == 'IDENTIFIER_THROTTLED' for result in blocked)
        for _, _, _, attempt_id in allowed:
            assert attempt_id
            assert complete(account_id, attempt_id, 'abandoned') == (True, 0, False)
    finally:
        delete_account(account_id)


def test_success_clears_failures_and_abandoned_reservations_are_released() -> None:
    account_id = account()
    try:
        for _ in range(2):
            allowed, _, _, attempt_id = begin(account_id)
            assert allowed and attempt_id
            complete(account_id, attempt_id, 'failure')

        allowed, _, _, attempt_id = begin(account_id)
        assert allowed and attempt_id
        assert complete(account_id, attempt_id, 'success') == (True, 0, False)

        allowed, _, failures, attempt_id = begin(account_id)
        assert allowed and failures == 0 and attempt_id
        assert complete(account_id, attempt_id, 'abandoned') == (True, 0, False)
    finally:
        delete_account(account_id)


def test_failure_window_expiry_resets_the_counter() -> None:
    account_id = account()
    try:
        for expected_count in (1, 2):
            allowed, _, _, attempt_id = begin(account_id)
            assert allowed and attempt_id
            assert complete(account_id, attempt_id, 'failure') == (
                True,
                expected_count,
                False,
            )

        with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
UPDATE public.auth_login_throttle_state
SET window_started_at = clock_timestamp() - interval '301 seconds'
WHERE account_id = %s
""",
                    (account_id,),
                )

        allowed, reason, failure_count, attempt_id = begin(account_id)
        assert allowed and reason is None and failure_count == 0 and attempt_id
        assert complete(account_id, attempt_id, 'abandoned') == (True, 0, False)
    finally:
        delete_account(account_id)


def test_cooldown_expiry_reopens_the_account_with_a_fresh_window() -> None:
    account_id = account()
    try:
        for attempt_number in range(5):
            allowed, _, _, attempt_id = begin(
                account_id,
                verified=attempt_number >= 3,
            )
            assert allowed and attempt_id
            completed, failure_count, cooldown = complete(
                account_id, attempt_id, 'failure'
            )
            assert completed and failure_count == attempt_number + 1
            assert cooldown is (attempt_number == 4)

        with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
UPDATE public.auth_login_throttle_state
SET blocked_until = clock_timestamp() - interval '1 second'
WHERE account_id = %s
""",
                    (account_id,),
                )

        allowed, reason, failure_count, attempt_id = begin(account_id)
        assert allowed and reason is None and failure_count == 0 and attempt_id
        assert complete(account_id, attempt_id, 'abandoned') == (True, 0, False)
    finally:
        delete_account(account_id)


def test_expired_password_reservations_are_pruned_before_admission() -> None:
    account_id = account()
    try:
        allowed, _, _, expired_attempt_id = begin(account_id, enabled=False)
        assert allowed and expired_attempt_id

        with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
UPDATE public.auth_login_attempt_reservations
SET expires_at = clock_timestamp() - interval '1 second'
WHERE attempt_id = %s
""",
                    (expired_attempt_id,),
                )

        allowed, reason, failure_count, attempt_id = begin(account_id, enabled=False)
        assert allowed and reason is None and failure_count == 0 and attempt_id
        with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
SELECT count(*)
FROM public.auth_login_attempt_reservations
WHERE attempt_id = %s
""",
                    (expired_attempt_id,),
                )
                assert cursor.fetchone()[0] == 0
        assert complete(account_id, attempt_id, 'abandoned') == (True, 0, False)
    finally:
        delete_account(account_id)


def test_expired_reservation_cannot_be_completed_or_counted_as_a_failure() -> None:
    account_id = account()
    try:
        allowed, _, _, attempt_id = begin(account_id, enabled=False)
        assert allowed and attempt_id

        with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
UPDATE public.auth_login_attempt_reservations
SET expires_at = clock_timestamp() - interval '1 second'
WHERE attempt_id = %s
""",
                    (attempt_id,),
                )

        assert complete(account_id, attempt_id, 'failure') == (False, 0, False)
        with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
SELECT state.failure_count,
       (SELECT count(*) FROM public.auth_login_attempt_reservations AS reservation
        WHERE reservation.attempt_id = %s)
FROM public.auth_login_throttle_state AS state
WHERE state.account_id = %s
""",
                    (attempt_id, account_id),
                )
                assert cursor.fetchone() == (0, 0)
    finally:
        delete_account(account_id)


def test_cooling_down_one_account_does_not_block_an_unrelated_account() -> None:
    targeted_account_id = account()
    unrelated_account_id = account()
    try:
        for attempt_number in range(5):
            allowed, _, _, attempt_id = begin(
                targeted_account_id,
                verified=attempt_number >= 3,
            )
            assert allowed and attempt_id
            completed, failure_count, cooldown = complete(
                targeted_account_id,
                attempt_id,
                'failure',
            )
            assert completed and failure_count == attempt_number + 1
            assert cooldown is (attempt_number == 4)

        allowed, reason, failure_count, attempt_id = begin(unrelated_account_id)
        assert allowed and reason is None and failure_count == 0 and attempt_id
        assert complete(unrelated_account_id, attempt_id, 'abandoned') == (
            True,
            0,
            False,
        )
    finally:
        delete_account(targeted_account_id)
        delete_account(unrelated_account_id)


def test_throttle_tables_and_rpcs_are_not_available_to_public_roles() -> None:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
SELECT c.relrowsecurity,
       has_table_privilege('anon', 'public.auth_login_throttle_state', 'SELECT'),
       has_table_privilege('authenticated', 'public.auth_login_throttle_state', 'SELECT'),
       has_function_privilege('anon', 'public.begin_auth_login_attempt_v1(uuid,uuid,boolean,boolean,integer,integer,integer,integer)', 'EXECUTE'),
       has_function_privilege('authenticated', 'public.complete_auth_login_attempt_v1(uuid,uuid,text,integer,integer,integer)', 'EXECUTE'),
       has_function_privilege('service_role', 'public.begin_auth_login_attempt_v1(uuid,uuid,boolean,boolean,integer,integer,integer,integer)', 'EXECUTE')
FROM pg_class AS c
WHERE c.oid = 'public.auth_login_throttle_state'::regclass
"""
            )
            row = cursor.fetchone()
    assert row == (True, False, False, False, False, True)
