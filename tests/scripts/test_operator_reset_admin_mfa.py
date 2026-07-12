from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from scripts.operator_reset_admin_mfa import (
    BreakGlassRequest,
    parse_request,
    run_restricted_reset,
)

ACCOUNT_ID = "7a7bb9de-1dff-44b7-9a44-12efe8a6716f"


class CursorStub:
    def __init__(self, *, broad_runtime_role: bool = False) -> None:
        self.executed: list[tuple[str, tuple[object, ...] | None]] = []
        self.broad_runtime_role = broad_runtime_role

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(
        self, query: str, params: tuple[object, ...] | None = None
    ) -> None:
        self.executed.append((query, params))

    def fetchone(self):
        if len(self.executed) == 1:
            return (
                "service_role" if self.broad_runtime_role else "operator_login",
                True,
                self.broad_runtime_role,
                self.broad_runtime_role,
            )
        return (
            "reset",
            UUID("37c42c6f-15a3-4a95-89c1-70e2f0ec59ef"),
            datetime(2026, 7, 12, tzinfo=timezone.utc),
        )


class ConnectionStub:
    def __init__(self, *, broad_runtime_role: bool = False) -> None:
        self.cursor_stub = CursorStub(broad_runtime_role=broad_runtime_role)

    def cursor(self) -> CursorStub:
        return self.cursor_stub


def test_parse_request_requires_bounded_operator_reason_and_confirmation() -> None:
    request = parse_request(
        [
            "--id",
            ACCOUNT_ID,
            "--operator",
            "soc-oncall@example.test",
            "--reason",
            "lost authenticator",
        ],
        {"CYBERTRACE_BREAK_GLASS_CONFIRMATION": "CYBERTRACE_BREAK_GLASS"},
    )

    assert request == BreakGlassRequest(
        account_id=UUID(ACCOUNT_ID),
        operator_identity="soc-oncall@example.test",
        reason="lost authenticator",
        confirmation="CYBERTRACE_BREAK_GLASS",
    )
    with pytest.raises(ValueError, match="confirmation"):
        parse_request(
            [
                "--id",
                ACCOUNT_ID,
                "--operator",
                "soc-oncall@example.test",
                "--reason",
                "lost authenticator",
            ],
            {},
        )


def test_run_reset_calls_only_the_restricted_function_and_returns_safe_fields() -> None:
    connection = ConnectionStub()
    request = BreakGlassRequest(
        account_id=UUID(ACCOUNT_ID),
        operator_identity="soc-oncall@example.test",
        reason="lost authenticator",
        confirmation="CYBERTRACE_BREAK_GLASS",
    )

    result = run_restricted_reset(connection, request)

    assert len(connection.cursor_stub.executed) == 2
    preflight_query, _ = connection.cursor_stub.executed[0]
    query, params = connection.cursor_stub.executed[1]
    assert "has_function_privilege" in preflight_query
    assert "has_table_privilege" in preflight_query
    assert "operator_reset_admin_mfa_restricted_v61" in query
    assert "operator_reset_admin_mfa(" not in query
    assert params == (
        request.account_id,
        request.operator_identity,
        request.reason,
        request.confirmation,
    )
    assert result == {
        "status": "reset",
        "event_id": "37c42c6f-15a3-4a95-89c1-70e2f0ec59ef",
        "performed_at": "2026-07-12T00:00:00+00:00",
    }


def test_run_reset_rejects_a_broad_runtime_database_role() -> None:
    connection = ConnectionStub(broad_runtime_role=True)
    request = BreakGlassRequest(
        account_id=UUID(ACCOUNT_ID),
        operator_identity="soc-oncall@example.test",
        reason="lost authenticator",
        confirmation="CYBERTRACE_BREAK_GLASS",
    )

    with pytest.raises(RuntimeError, match="least privilege"):
        run_restricted_reset(connection, request)

    assert len(connection.cursor_stub.executed) == 1
