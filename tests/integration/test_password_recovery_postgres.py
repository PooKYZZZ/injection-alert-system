from __future__ import annotations

import os
import threading
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest
from psycopg.types.json import Jsonb

POSTGRES_URL = os.getenv('CYBERTRACE_POSTGRES_TEST_URL')
pytestmark = pytest.mark.skipif(not POSTGRES_URL, reason='requires an explicit disposable PostgreSQL URL')


def _account(email: str, role: str) -> str:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (email, name, role, password_hash, password_set_at, email_verified_at, mfa_required)
VALUES (%s, %s, %s, '$argon2id$test', now(), now(), %s)
RETURNING id
""",
                (email, f'{role} User', role, role != 'VIEWER'),
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


def _consume_reset(account_id: str, token_hash: str, password_hash: str) -> bool:
    try:
        with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT public.consume_password_reset_and_change_password(%s, %s)',
                    (token_hash, password_hash),
                )
                return str(cursor.fetchone()[0]) == account_id
    except psycopg.Error:
        return False


def _create_reset_token(account_id: str, token_hash: str, suffix: str) -> None:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT public.create_password_reset_token_protected_v61(%s, %s, now() + interval '30 minutes', %s, %s, %s, 'user_requested')",
                (
                    account_id,
                    token_hash,
                    Jsonb(
                        {
                            'ciphertext': 'integration-test',
                            'nonce': 'test-nonce',
                            'key_version': 1,
                        }
                    ),
                    f'reset-dedupe-{suffix}',
                    f'reset-provider-{suffix}',
                ),
            )
            assert cursor.fetchone()[0] is True


def test_password_reset_is_single_use_and_increments_authz_once() -> None:
    account_id = _account('reset@example.test', 'ANALYST')
    token_hash = 'a' * 64
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT public.create_password_reset_token_protected_v61(%s, %s, now() + interval '30 minutes', %s, 'reset-dedupe', 'reset-provider', 'user_requested')",
                (
                    account_id,
                    token_hash,
                    Jsonb(
                        {
                            'ciphertext': 'integration-test',
                            'nonce': 'test-nonce',
                            'key_version': 1,
                        }
                    ),
                ),
            )
            assert cursor.fetchone()[0] is True
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda value: _consume_reset(account_id, token_hash, value), ['$argon2id$hash-one-long-enough', '$argon2id$hash-two-long-enough']))
    assert sorted(results) == [False, True]
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute('SELECT authz_version FROM public.auth_accounts WHERE id = %s', (account_id,))
            assert cursor.fetchone()[0] == 2


def test_password_reset_reissue_revokes_the_previous_token() -> None:
    account_id = _account('reissue@example.test', 'ANALYST')
    previous_hash = 'b' * 64
    latest_hash = 'c' * 64

    _create_reset_token(account_id, previous_hash, 'first')
    _create_reset_token(account_id, latest_hash, 'second')

    assert not _consume_reset(account_id, previous_hash, '$argon2id$hash-long-enough')
    assert _consume_reset(account_id, latest_hash, '$argon2id$hash-long-enough')
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT token_hash, status FROM public.auth_reset_tokens WHERE account_id = %s ORDER BY created_at',
                (account_id,),
            )
            assert dict(cursor.fetchall()) == {
                previous_hash: 'revoked',
                latest_hash: 'used',
            }


def test_simultaneous_password_reset_requests_leave_only_one_pending_token() -> None:
    account_id = _account('concurrent-reissue@example.test', 'ANALYST')
    hashes = ('e' * 64, 'f' * 64)
    barrier = threading.Barrier(2)

    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
CREATE FUNCTION public.test_delay_password_reset_insert()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  PERFORM pg_sleep(0.75);
  RETURN NEW;
END
$$
"""
            )
            cursor.execute(
                """
CREATE TRIGGER test_delay_password_reset_insert
BEFORE INSERT ON public.auth_reset_tokens
FOR EACH ROW EXECUTE FUNCTION public.test_delay_password_reset_insert()
"""
            )

    def create(token_hash: str, suffix: str) -> None:
        barrier.wait()
        _create_reset_token(account_id, token_hash, suffix)

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(
                pool.map(
                    lambda item: create(*item),
                    [(hashes[0], 'concurrent-first'), (hashes[1], 'concurrent-second')],
                )
            )
    finally:
        with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
DROP TRIGGER IF EXISTS test_delay_password_reset_insert
ON public.auth_reset_tokens
"""
                )
                cursor.execute(
                    'DROP FUNCTION IF EXISTS public.test_delay_password_reset_insert()'
                )

    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FILTER (WHERE status = 'pending'), "
                "count(*) FILTER (WHERE status = 'revoked') "
                "FROM public.auth_reset_tokens WHERE account_id = %s",
                (account_id,),
            )
            assert cursor.fetchone() == (1, 1)


def test_password_reset_rejects_an_expired_token() -> None:
    account_id = _account('expired@example.test', 'ANALYST')
    token_hash = 'd' * 64
    _create_reset_token(account_id, token_hash, 'expired')
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE public.auth_reset_tokens SET expires_at = now() - interval '1 second' WHERE token_hash = %s",
                (token_hash,),
            )

    assert not _consume_reset(account_id, token_hash, '$argon2id$hash-long-enough')
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT reset.status, account.authz_version FROM public.auth_accounts AS account JOIN public.auth_reset_tokens AS reset ON reset.account_id = account.id WHERE account.id = %s',
                (account_id,),
            )
            assert cursor.fetchone() == ('pending', 1)


def test_admin_mfa_reset_revokes_factor_and_invalidates_backup_codes() -> None:
    actor_id = _account('admin@example.test', 'ADMIN')
    target_id = _account('analyst@example.test', 'ANALYST')
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT public.begin_totp_enrollment(%s, gen_random_uuid(), 'encrypted-secret-value', 'nonce-value', 1, now() + interval '10 minutes')", (target_id,))
            factor_id = str(cursor.fetchone()[0])
            cursor.execute("SELECT public.activate_totp_factor(%s, %s, 100, '[{\"lookup_prefix\":\"ABCD\",\"code_hash\":\"hash-one\"}]'::jsonb)", (target_id, factor_id))
            cursor.fetchone()
            cursor.execute("SELECT public.admin_reset_mfa(%s, %s, 'lost authenticator', 'admin-reset-dedupe', 'admin-reset-provider')", (actor_id, target_id))
            assert cursor.fetchone()[0] is True
            cursor.execute('SELECT status FROM public.auth_mfa_factors WHERE id = %s', (factor_id,))
            assert cursor.fetchone()[0] == 'revoked'
            cursor.execute('SELECT revoked_at IS NOT NULL OR used_at IS NOT NULL FROM public.auth_backup_codes WHERE account_id = %s', (target_id,))
            assert cursor.fetchone()[0] is True


def test_operator_recovery_requires_exact_confirmation() -> None:
    admin_id = _account('only-admin@example.test', 'ADMIN')
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            with pytest.raises(psycopg.Error):
                cursor.execute("SELECT public.operator_reset_admin_mfa(%s, 'wrong', 'break glass')", (admin_id,))
