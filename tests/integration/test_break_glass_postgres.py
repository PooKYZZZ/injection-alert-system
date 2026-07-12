from __future__ import annotations

import os
from datetime import datetime
from uuid import UUID

import psycopg
import pytest

from scripts.operator_reset_admin_mfa import (
    BreakGlassRequest,
    run_restricted_reset,
)

POSTGRES_URL = os.getenv("CYBERTRACE_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires an explicit disposable PostgreSQL URL",
)


@pytest.fixture(autouse=True)
def clear_auth_state():
    if not POSTGRES_URL:
        yield
        return
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE public.auth_accounts CASCADE")
    yield


def test_break_glass_role_has_only_the_recovery_function() -> None:
    signature = (
        "public.operator_reset_admin_mfa_restricted_v61(uuid,text,text,text)"
    )
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
SELECT
  has_function_privilege('cybertrace_break_glass', %s, 'EXECUTE'),
  has_function_privilege('service_role', %s, 'EXECUTE'),
  has_function_privilege(
    'service_role',
    'public.operator_reset_admin_mfa(uuid,text,text)',
    'EXECUTE'
  ),
  has_table_privilege('cybertrace_break_glass', 'public.auth_accounts', 'SELECT'),
  has_table_privilege('cybertrace_break_glass', 'public.auth_mfa_factors', 'UPDATE')
""",
                (signature, signature),
            )
            assert cursor.fetchone() == (True, False, False, False, False)


def test_restricted_recovery_revokes_mfa_and_records_operator_result() -> None:
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
INSERT INTO public.auth_accounts (
  email, name, role, password_hash, password_set_at,
  email_verified_at, mfa_required
)
VALUES (
  'break-glass-admin@example.test', 'Break Glass Admin', 'ADMIN',
  '$argon2id$test', now(), now(), true
)
RETURNING id, authz_version
"""
            )
            account_id, initial_version = cursor.fetchone()
            cursor.execute(
                """
INSERT INTO public.auth_mfa_factors (
  account_id, factor_type, status, secret_ciphertext,
  secret_nonce, secret_key_version, activated_at
)
VALUES (%s, 'totp', 'active', 'ciphertext', 'nonce', 1, now())
RETURNING id
""",
                (account_id,),
            )
            factor_id = cursor.fetchone()[0]

            cursor.execute("SET ROLE service_role")
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                cursor.execute(
                    """
SELECT * FROM public.operator_reset_admin_mfa_restricted_v61(
  %s, 'soc-oncall@example.test', 'lost authenticator',
  'CYBERTRACE_BREAK_GLASS'
)
""",
                    (account_id,),
                )
            cursor.execute("RESET ROLE")

            cursor.execute("SET ROLE cybertrace_break_glass")
            reset_result = run_restricted_reset(
                connection,
                BreakGlassRequest(
                    account_id=account_id,
                    operator_identity="soc-oncall@example.test",
                    reason="lost authenticator",
                    confirmation="CYBERTRACE_BREAK_GLASS",
                ),
            )
            cursor.execute("RESET ROLE")

            assert reset_result["status"] == "reset"
            event_id = UUID(reset_result["event_id"])
            performed_at = datetime.fromisoformat(reset_result["performed_at"])
            cursor.execute(
                "SELECT status FROM public.auth_mfa_factors WHERE id = %s",
                (factor_id,),
            )
            assert cursor.fetchone()[0] == "revoked"
            cursor.execute(
                "SELECT authz_version FROM public.auth_accounts WHERE id = %s",
                (account_id,),
            )
            assert cursor.fetchone()[0] == initial_version + 1
            cursor.execute(
                """
SELECT event_type, severity, outcome, safe_summary_json, created_at
FROM public.security_events
WHERE id = %s
""",
                (event_id,),
            )
            event_type, severity, outcome, summary, created_at = cursor.fetchone()

    assert (event_type, severity, outcome) == (
        "auth.operator_admin_recovery",
        "critical",
        "success",
    )
    summary_performed_at = datetime.fromisoformat(summary.pop("performed_at"))
    assert summary_performed_at == performed_at
    assert summary == {
        "operator_identity": "soc-oncall@example.test",
        "database_session_user": "postgres",
        "reason": "lost authenticator",
        "result": "reset",
    }
    assert created_at == performed_at
