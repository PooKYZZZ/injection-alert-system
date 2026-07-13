"""Invoke the restricted PostgreSQL break-glass ADMIN MFA recovery function."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

import psycopg

CONFIRMATION = "CYBERTRACE_BREAK_GLASS"
DATABASE_URL_ENV = "CYBERTRACE_BREAK_GLASS_DATABASE_URL"


@dataclass(frozen=True)
class BreakGlassRequest:
    account_id: UUID
    operator_identity: str
    reason: str
    confirmation: str


def _bounded_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not 3 <= len(normalized) <= 128 or not normalized.isprintable():
        raise ValueError(f"{field} must contain 3 to 128 printable characters.")
    return normalized


def parse_request(
    argv: Sequence[str], environ: Mapping[str, str] = os.environ
) -> BreakGlassRequest:
    parser = argparse.ArgumentParser(
        description=(
            "Reset one ADMIN account's MFA through the restricted database role."
        )
    )
    parser.add_argument("--id", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--reason", required=True)
    values = parser.parse_args(argv)
    confirmation = environ.get("CYBERTRACE_BREAK_GLASS_CONFIRMATION", "")
    if confirmation != CONFIRMATION:
        raise ValueError("Explicit break-glass confirmation is required.")
    try:
        account_id = UUID(values.id)
    except (TypeError, ValueError) as exc:
        raise ValueError("A valid target account id is required.") from exc
    return BreakGlassRequest(
        account_id=account_id,
        operator_identity=_bounded_text(values.operator, "Operator identity"),
        reason=_bounded_text(values.reason, "Reason"),
        confirmation=confirmation,
    )


def run_restricted_reset(
    connection: Any, request: BreakGlassRequest
) -> dict[str, str]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
SELECT
  current_user::text,
  has_function_privilege(
    current_user,
    'public.operator_reset_admin_mfa_restricted_v61(uuid,text,text,text)',
    'EXECUTE'
  ),
  has_table_privilege(current_user, 'public.auth_accounts', 'UPDATE'),
  has_table_privilege(current_user, 'public.auth_mfa_factors', 'UPDATE')
"""
        )
        privilege_row = cursor.fetchone()
        if (
            privilege_row is None
            or privilege_row[0] == "service_role"
            or privilege_row[1] is not True
            or privilege_row[2] is not False
            or privilege_row[3] is not False
        ):
            raise RuntimeError(
                "Break-glass database role does not satisfy least privilege."
            )
        cursor.execute(
            """
SELECT result, event_id, performed_at
FROM public.operator_reset_admin_mfa_restricted_v61(%s, %s, %s, %s)
""",
            (
                request.account_id,
                request.operator_identity,
                request.reason,
                request.confirmation,
            ),
        )
        row = cursor.fetchone()
    if (
        row is None
        or row[0] != "reset"
        or not isinstance(row[1], UUID)
        or not isinstance(row[2], datetime)
    ):
        raise RuntimeError("Restricted ADMIN recovery returned an invalid result.")
    return {
        "status": row[0],
        "event_id": str(row[1]),
        "performed_at": row[2].isoformat(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    try:
        request = parse_request(sys.argv[1:] if argv is None else argv)
        database_url = os.environ.get(DATABASE_URL_ENV, "").strip()
        if not database_url:
            raise ValueError("Restricted database configuration is required.")
        with psycopg.connect(database_url) as connection:
            result = run_restricted_reset(connection, request)
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except Exception:
        print("Restricted ADMIN recovery failed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
