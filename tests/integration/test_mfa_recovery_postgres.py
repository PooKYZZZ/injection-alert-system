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
VALUES ('recovery@example.test', 'Recovery User', 'ADMIN', '$argon2id$test', now(), now(), true)
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


def _seed_factor_and_code(account_id: str) -> tuple[str, str]:
    factor_id = str(uuid4())
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT public.begin_totp_enrollment(%s, %s, 'encrypted-secret-value', 'nonce-value', 1, now() + interval '10 minutes')",
                (account_id, factor_id),
            )
            cursor.fetchone()
            cursor.execute(
                "SELECT public.activate_totp_factor(%s, %s, 100, %s::jsonb)",
                (account_id, factor_id, '[{"lookup_prefix":"ABCD","code_hash":"hash-one"}]'),
            )
            cursor.fetchone()
            cursor.execute('SELECT id FROM public.auth_backup_codes WHERE account_id = %s', (account_id,))
            return factor_id, str(cursor.fetchone()[0])


def _consume_backup(account_id: str, code_id: str, token_hash: str) -> bool:
    try:
        with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT public.consume_backup_code_for_recovery(%s, %s, %s, now() + interval '5 minutes')",
                    (account_id, code_id, token_hash),
                )
                return bool(cursor.fetchone()[0])
    except psycopg.Error:
        return False


def test_backup_recovery_is_single_use_and_revokes_old_mfa_material() -> None:
    account_id = _account()
    factor_id, code_id = _seed_factor_and_code(account_id)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda token: _consume_backup(account_id, code_id, token), ['a' * 64, 'b' * 64]))
    assert sorted(results) == [False, True]
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT status FROM public.auth_mfa_factors WHERE id = %s', (factor_id,))
            assert cursor.fetchone()[0] == 'revoked'
            cursor.execute('SELECT used_at IS NOT NULL OR revoked_at IS NOT NULL FROM public.auth_backup_codes WHERE id = %s', (code_id,))
            assert cursor.fetchone()[0] is True
            cursor.execute('SELECT authz_version FROM public.auth_accounts WHERE id = %s', (account_id,))
            assert cursor.fetchone()[0] == 3


def test_email_otp_recovery_is_single_use_and_completion_is_recovery_level() -> None:
    account_id = _account()
    factor_id, _ = _seed_factor_and_code(account_id)
    completion_hash = 'c' * 64
    otp_digest = 'd' * 64
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT public.begin_email_recovery_challenge(%s, %s, %s, now() + interval '5 minutes')",
                (account_id, otp_digest, completion_hash),
            )
            cursor.fetchone()
            cursor.execute('SELECT public.consume_email_otp_for_recovery(%s, %s)', (account_id, otp_digest))
            assert cursor.fetchone()[0] is True
            cursor.execute('SELECT * FROM public.consume_mfa_recovery_completion_token(%s)', (completion_hash,))
            row = cursor.fetchone()
            assert str(row[0]) == account_id
            assert row[1] == 'ADMIN'
            assert row[3] == 'email_otp'
            cursor.execute('SELECT status FROM public.auth_mfa_factors WHERE id = %s', (factor_id,))
            assert cursor.fetchone()[0] == 'revoked'
