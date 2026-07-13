"""Provision the Supabase runtime roles expected by migration integration tests.

This helper is intentionally CI-only. The stock PostgreSQL service used by
GitHub Actions does not include Supabase's runtime roles, while the hosted
runtime does. Creating the roles before Alembic runs lets migrations and tests
exercise their real grant and revocation behavior.
"""

from __future__ import annotations

import os

import psycopg
from psycopg import sql


ROLE_ATTRIBUTES = {
    "anon": "NOLOGIN",
    "authenticated": "NOLOGIN",
    "service_role": "NOLOGIN BYPASSRLS",
}


def main() -> None:
    if os.environ.get("CI", "").lower() != "true":
        raise RuntimeError("Refusing to provision CI roles outside GitHub Actions.")
    if os.environ.get("APP_ENV") != "testing":
        raise RuntimeError("Refusing to provision CI roles outside APP_ENV=testing.")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required.")

    with psycopg.connect(database_url, autocommit=True) as connection:
        for role, attributes in ROLE_ATTRIBUTES.items():
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,))
                if cursor.fetchone() is None:
                    cursor.execute(
                        sql.SQL("CREATE ROLE {} {}").format(
                            sql.Identifier(role), sql.SQL(attributes)
                        )
                    )


if __name__ == "__main__":
    main()
