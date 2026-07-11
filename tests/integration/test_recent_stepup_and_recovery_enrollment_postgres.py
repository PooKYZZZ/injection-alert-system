from __future__ import annotations

import os
from uuid import uuid4

import psycopg
import pytest


POSTGRES_URL = os.getenv("CYBERTRACE_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires an explicit disposable PostgreSQL URL",
)


@pytest.fixture(autouse=True)
def clear_state():
    if not POSTGRES_URL:
        yield
        return
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE public.auth_accounts CASCADE")
    yield


def _account(email: str = "admin@example.test") -> str:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (
  email, name, role, password_hash, password_set_at, email_verified_at, mfa_required
)
VALUES (%s, 'Admin User', 'ADMIN', '$argon2id$test', now(), now(), true)
RETURNING id
""",
                (email,),
            )
            return str(cursor.fetchone()[0])


def _active_factor(account_id: str) -> str:
    factor_id = str(uuid4())
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_mfa_factors (
  id, account_id, factor_type, status, secret_ciphertext, secret_nonce,
  secret_key_version, activated_at
)
VALUES (%s, %s, 'totp', 'active', 'encrypted-secret-value', 'nonce-value', 1, now())
""",
                (factor_id, account_id),
            )
    return factor_id


def test_recent_totp_step_up_is_purpose_bound_and_consumable() -> None:
    account_id = _account()
    factor_id = _active_factor(account_id)
    preauth_hash = "a" * 64
    completion_hash = "b" * 64
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM public.begin_recent_totp_challenge_v61(%s, %s, now() + interval '5 minutes')",
                (account_id, preauth_hash),
            )
            row = cursor.fetchone()
            assert row[1:] == ("recent_reauthentication", row[2])
            cursor.execute(
                "SELECT * FROM public.record_recent_totp_attempt_v61(%s, %s, %s, true, 100, %s, now() + interval '2 minutes')",
                (account_id, preauth_hash, factor_id, completion_hash),
            )
            assert cursor.fetchone()[0] == "verified"
            cursor.execute(
                "SELECT completion_purpose FROM public.consume_mfa_completion_token_v61(%s)",
                (completion_hash,),
            )
            assert cursor.fetchone()[0] == "recent_reauthentication"


def test_recovery_session_can_start_a_fresh_enrollment_challenge() -> None:
    account_id = _account("recovery-enrollment@example.test")
    old_factor_id = _active_factor(account_id)
    code_id = str(uuid4())
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_backup_codes (id, account_id, lookup_prefix, code_hash)
VALUES (%s, %s, 'ABCD', '$argon2id$backup-code')
""",
                (code_id, account_id),
            )
            recovery_token = "c" * 64
            cursor.execute(
                "SELECT public.consume_backup_code_for_recovery_v61(%s, %s, %s, now() + interval '5 minutes')",
                (account_id, code_id, recovery_token),
            )
            assert cursor.fetchone()[0] is True
            cursor.execute(
                "SELECT * FROM public.consume_mfa_recovery_completion_token_v61(%s)",
                (recovery_token,),
            )
            assert str(cursor.fetchone()[0]) == account_id
            new_factor_id = str(uuid4())
            preauth_hash = "d" * 64
            cursor.execute(
                "SELECT public.begin_recovery_totp_enrollment_v61(%s, %s, 'encrypted-new-secret', 'nonce-value', 1, now() + interval '10 minutes', %s)",
                (account_id, new_factor_id, preauth_hash),
            )
            assert str(cursor.fetchone()[0]) == new_factor_id
            cursor.execute(
                "SELECT status FROM public.auth_mfa_factors WHERE id = %s",
                (old_factor_id,),
            )
            assert cursor.fetchone()[0] == "revoked"
