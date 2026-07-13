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


def _account() -> str:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (
  email, name, role, password_hash, password_set_at,
  email_verified_at, mfa_required
)
VALUES ('totp@example.test', 'TOTP User', 'ANALYST', '$argon2id$test', now(), now(), true)
RETURNING id
"""
            )
            return str(cursor.fetchone()[0])


@pytest.fixture(autouse=True)
def clear_state():
    if not POSTGRES_URL:
        yield
        return
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE TABLE public.auth_accounts CASCADE')
    yield


def _consume_step(account_id: str, factor_id: str, step: int) -> bool:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT public.consume_totp_step(%s, %s, %s)',
                (account_id, factor_id, step),
            )
            return bool(cursor.fetchone()[0])


def _consume_backup(account_id: str, code_id: str) -> bool:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT public.consume_backup_code(%s, %s)',
                (account_id, code_id),
            )
            return bool(cursor.fetchone()[0])


def test_totp_activation_and_replay_are_atomic() -> None:
    account_id = _account()
    factor_id = str(uuid4())
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT public.begin_totp_enrollment(%s, %s, %s, %s, %s, now() + interval \'10 minutes\')',
                (account_id, factor_id, 'encrypted-secret', 'nonce-value', 1),
            )
            assert str(cursor.fetchone()[0]) == factor_id
            cursor.execute(
                """
SELECT public.activate_totp_factor(%s, %s, %s, %s::jsonb)
""",
                (
                    account_id,
                    factor_id,
                    100,
                    '[{"lookup_prefix":"ABCD","code_hash":"hash-one"}]',
                ),
            )
            assert cursor.fetchone()[0] is True

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _consume_step(account_id, factor_id, 101), range(2)))
    assert sorted(results) == [False, True]


def test_backup_code_consumption_is_single_use_and_not_retrievable_afterwards() -> None:
    account_id = _account()
    factor_id = str(uuid4())
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT public.begin_totp_enrollment(%s, %s, %s, %s, %s, now() + interval \'10 minutes\')',
                (account_id, factor_id, 'encrypted-secret', 'nonce-value', 1),
            )
            cursor.fetchone()
            cursor.execute(
                "SELECT public.activate_totp_factor(%s, %s, 200, %s::jsonb)",
                (account_id, factor_id, '[{"lookup_prefix":"ABCD","code_hash":"hash-one"}]'),
            )
            cursor.fetchone()
            cursor.execute(
                "SELECT id FROM public.auth_backup_codes WHERE account_id = %s",
                (account_id,),
            )
            code_id = str(cursor.fetchone()[0])

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _consume_backup(account_id, code_id), range(2)))
    assert sorted(results) == [False, True]
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT id FROM public.auth_backup_codes WHERE account_id = %s AND used_at IS NULL AND revoked_at IS NULL',
                (account_id,),
            )
            assert cursor.fetchone() is None
