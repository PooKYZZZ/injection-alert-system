from __future__ import annotations

import ipaddress
import os
import sys
from collections.abc import Callable

from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

_LOCAL_DATABASE_HOSTS = frozenset({"localhost", "postgres", "host.docker.internal"})


class UnsafeDatabaseTarget(RuntimeError):
    """Raised before Alembic when normal local startup targets a remote database."""


def _is_loopback_host(host: str) -> bool:
    if host.lower() in _LOCAL_DATABASE_HOSTS:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def require_local_database(database_url: str) -> None:
    if not database_url.strip():
        raise UnsafeDatabaseTarget(
            "DATABASE_URL must identify a local database before migrations can run."
        )
    try:
        url = make_url(database_url)
        backend = url.get_backend_name()
    except (ArgumentError, ValueError) as exc:
        raise UnsafeDatabaseTarget(
            "DATABASE_URL must identify a local database before migrations can run."
        ) from exc

    if backend == "sqlite":
        return
    if backend == "postgresql" and url.host and _is_loopback_host(url.host):
        query_hosts = url.normalized_query.get("host", ())
        if all(_is_loopback_host(host) for host in query_hosts):
            return
    raise UnsafeDatabaseTarget(
        "Normal Compose startup permits migrations only against a local database. "
        "Run hosted database migrations through an explicit operator workflow."
    )


def run_local_migrations(
    *,
    database_url: str | None = None,
    upgrade: Callable[[Config, str], None] = command.upgrade,
) -> None:
    target = os.getenv("DATABASE_URL", "") if database_url is None else database_url
    require_local_database(target)
    upgrade(Config("alembic.ini"), "head")


def main() -> int:
    try:
        run_local_migrations()
    except UnsafeDatabaseTarget as exc:
        print(f"Migration safety check failed: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
