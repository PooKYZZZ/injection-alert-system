from __future__ import annotations

import os
from datetime import datetime, timezone
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
def clear_state():
    if not POSTGRES_URL:
        yield
        return
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE public.notification_outbox CASCADE")
            cursor.execute("TRUNCATE TABLE public.auth_accounts CASCADE")
    yield


def account(*, role: str = "ADMIN", verified: bool = True) -> str:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (
  email, name, role, password_hash, password_set_at,
  email_verified_at, mfa_required
)
VALUES (%s, %s, %s, '$argon2id$test', now(), %s, true)
RETURNING id
""",
                (
                    f"{uuid4()}@example.test",
                    f"{role} User",
                    role,
                    datetime.now(timezone.utc) if verified else None,
                ),
            )
            return str(cursor.fetchone()[0])


def active_factor(account_id: str) -> str:
    factor_id = str(uuid4())
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
SELECT public.begin_totp_enrollment(
  %s, %s, 'encrypted-secret-value', 'nonce-value', 1,
  now() + interval '10 minutes'
)
""",
                (account_id, factor_id),
            )
            assert str(cursor.fetchone()[0]) == factor_id
            cursor.execute(
                "SELECT public.activate_totp_factor(%s, %s, 100, '[]'::jsonb)",
                (account_id, factor_id),
            )
            assert cursor.fetchone()[0] is True
    return factor_id


def begin(account_id: str, preauth_hash: str = "a" * 64) -> tuple[str, str]:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
SELECT * FROM public.begin_mfa_challenge_v61(
  %s, %s, now() + interval '10 minutes'
)
""",
                (account_id, preauth_hash),
            )
            row = cursor.fetchone()
            return str(row[0]), row[1]


def test_factor_aware_challenge_selection_is_database_authoritative() -> None:
    account_id = account()
    _, purpose = begin(account_id)
    assert purpose == "mfa_enrollment"

    factor_id = active_factor(account_id)
    _, purpose = begin(account_id, "b" * 64)
    assert purpose == "login_mfa"
    assert factor_id


def test_invalid_totp_attempts_commit_and_lock_persistently() -> None:
    account_id = account()
    factor_id = active_factor(account_id)
    begin(account_id)
    outcomes: list[str] = []
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            for _ in range(5):
                cursor.execute(
                    """
SELECT outcome FROM public.record_totp_attempt_v61(
  %s, %s, %s, false, NULL, NULL, NULL
)
""",
                    (account_id, "a" * 64, factor_id),
                )
                outcomes.append(cursor.fetchone()[0])
            cursor.execute(
                "SELECT attempt_count, status FROM public.auth_mfa_challenges WHERE account_id = %s ORDER BY created_at DESC LIMIT 1",
                (account_id,),
            )
            row = cursor.fetchone()
    assert outcomes == ["invalid", "invalid", "invalid", "invalid", "locked"]
    assert row == (5, "locked")


def test_completion_consumers_reject_cross_purpose_tokens_and_return_db_time() -> None:
    account_id = account()
    challenge_id = str(uuid4())
    token_hash = "c" * 64
    verified_at = datetime.now(timezone.utc)
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_mfa_challenges (
  id, account_id, challenge_hash, purpose, status, expires_at,
  verified_method, verified_at, completion_token_hash, completion_expires_at
)
VALUES (%s, %s, %s, 'mfa_recovery', 'verified', now() + interval '5 minutes',
        'backup_code', %s, %s, now() + interval '5 minutes')
""",
                (challenge_id, account_id, "d" * 64, verified_at, token_hash),
            )
            cursor.execute(
                "INSERT INTO public.auth_mfa_completion_tokens (account_id, mfa_challenge_id, token_hash, expires_at) VALUES (%s, %s, %s, now() + interval '5 minutes')",
                (account_id, challenge_id, token_hash),
            )
            with pytest.raises(psycopg.Error):
                cursor.execute(
                    "SELECT * FROM public.consume_mfa_completion_token_v61(%s)",
                    (token_hash,),
                )
            cursor.execute(
                "SELECT * FROM public.consume_mfa_recovery_completion_token_v61(%s)",
                (token_hash,),
            )
            row = cursor.fetchone()
    assert str(row[0]) == account_id
    assert row[5:7] == ("recovery", "backup_code")
    assert row[7].replace(tzinfo=timezone.utc) == verified_at.replace(tzinfo=timezone.utc)


def test_normal_completion_is_retryable_once_with_same_purpose() -> None:
    account_id = account()
    factor_id = active_factor(account_id)
    begin(account_id)
    token_hash = "e" * 64
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT outcome FROM public.record_totp_attempt_v61(%s, %s, %s, true, 101, %s, now() + interval '2 minutes')",
                (account_id, "a" * 64, factor_id, token_hash),
            )
            assert cursor.fetchone()[0] == "verified"
            cursor.execute(
                "SELECT * FROM public.consume_mfa_completion_token_v61(%s)",
                (token_hash,),
            )
            first = cursor.fetchone()
            cursor.execute(
                "SELECT * FROM public.consume_mfa_completion_token_v61(%s)",
                (token_hash,),
            )
            second = cursor.fetchone()
            with pytest.raises(psycopg.Error):
                cursor.execute(
                    "SELECT * FROM public.consume_mfa_completion_token_v61(%s)",
                    (token_hash,),
                )
    assert first[5:9] == second[5:9]
    assert first[5:7] == ("mfa", "totp")
    assert first[8] == "login_mfa"


def test_email_otp_invalid_attempts_commit_without_outbox_split() -> None:
    account_id = account()
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT email FROM public.auth_accounts WHERE id = %s",
                (account_id,),
            )
            recipient = cursor.fetchone()[0]
            cursor.execute(
                """
SELECT status FROM public.begin_email_recovery_challenge_protected_v61(
  %s, %s, %s, %s, now() + interval '5 minutes', %s, %s, %s
)
""",
                (
                    account_id,
                    recipient,
                    "f" * 64,
                    "1" * 64,
                    Jsonb(
                        {
                            "ciphertext": "integration-test",
                            "nonce": "test-nonce",
                            "key_version": 1,
                        }
                    ),
                    f"email/{uuid4()}",
                    f"provider/{uuid4()}",
                ),
            )
            assert cursor.fetchone()[0] == "sent"
            outcomes = []
            for _ in range(5):
                cursor.execute(
                    "SELECT outcome FROM public.consume_email_otp_for_recovery_v61(%s, %s)",
                    (account_id, "0" * 64),
                )
                outcomes.append(cursor.fetchone()[0])
            cursor.execute(
                "SELECT attempt_count, status FROM public.auth_email_otp_challenges WHERE account_id = %s",
                (account_id,),
            )
            row = cursor.fetchone()
            cursor.execute(
                "SELECT count(*) FROM public.notification_outbox WHERE recipient = (SELECT email FROM public.auth_accounts WHERE id = %s)",
                (account_id,),
            )
            outbox_count = cursor.fetchone()[0]
    assert outcomes == ["invalid", "invalid", "invalid", "invalid", "locked"]
    assert row == (5, "locked")
    assert outbox_count == 1


def test_password_token_preflight_is_cheap_and_purpose_bound() -> None:
    account_id = account()
    token_hash = "1" * 64
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO public.auth_reset_tokens (account_id, purpose, token_hash, expires_at) VALUES (%s, 'password_reset', %s, now() + interval '5 minutes')",
                (account_id, token_hash),
            )
            cursor.execute(
                "SELECT public.preflight_password_token_v61(%s, 'password_reset')",
                (token_hash,),
            )
            assert cursor.fetchone()[0] is True
            cursor.execute(
                "SELECT public.preflight_password_token_v61(%s, 'password_setup')",
                (token_hash,),
            )
            assert cursor.fetchone()[0] is False
