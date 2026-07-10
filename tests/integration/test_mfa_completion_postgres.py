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
VALUES ('mfa@example.test', 'MFA User', 'ADMIN', '$argon2id$test', now(), now(), true)
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


def _verify(account_id: str, preauth_hash: str, factor_id: str, step: int, token_hash: str) -> bool:
    try:
        with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
SELECT public.verify_totp_and_issue_completion(
  %s, %s, %s, %s, %s, now() + interval '5 minutes'
)
""",
                    (account_id, preauth_hash, factor_id, step, token_hash),
                )
                return bool(cursor.fetchone()[0])
    except psycopg.Error:
        return False


def _consume(token_hash: str):
    try:
        with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT * FROM public.consume_mfa_completion_token(%s)',
                    (token_hash,),
                )
                return cursor.fetchone()
    except psycopg.Error:
        return None


def _seed_challenge() -> tuple[str, str, str]:
    account_id = _account()
    factor_id = str(uuid4())
    preauth_hash = 'a' * 64
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT public.begin_totp_enrollment(%s, %s, 'encrypted-secret-value', 'nonce-value', 1, now() + interval '10 minutes')",
                (account_id, factor_id),
            )
            cursor.fetchone()
            cursor.execute(
                "SELECT public.activate_totp_factor(%s, %s, 100, '[]'::jsonb)",
                (account_id, factor_id),
            )
            cursor.fetchone()
            cursor.execute(
                "SELECT public.begin_login_mfa_challenge(%s, %s, now() + interval '10 minutes')",
                (account_id, preauth_hash),
            )
            cursor.fetchone()
    return account_id, factor_id, preauth_hash


def test_same_totp_challenge_can_issue_only_one_completion() -> None:
    account_id, factor_id, preauth_hash = _seed_challenge()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda token: _verify(account_id, preauth_hash, factor_id, 101, token),
                ['b' * 64, 'c' * 64],
            )
        )
    assert sorted(results) == [False, True]


def test_completion_token_is_single_use_and_returns_fresh_claim_material() -> None:
    account_id, factor_id, preauth_hash = _seed_challenge()
    assert _verify(account_id, preauth_hash, factor_id, 101, 'b' * 64)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _consume('b' * 64), range(2)))
    assert sum(result is not None for result in results) == 1
    row = next(result for result in results if result is not None)
    assert str(row[0]) == account_id
    assert row[1] == 'ADMIN'
