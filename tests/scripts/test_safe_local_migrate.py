from __future__ import annotations

import importlib
import importlib.util

import pytest


def safe_migrate_module():
    assert importlib.util.find_spec("scripts.safe_local_migrate") is not None
    return importlib.import_module("scripts.safe_local_migrate")


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite+aiosqlite:///./injection_alerts.db",
        "postgresql+asyncpg://cybertrace:local@postgres:5432/cybertrace",
        "postgresql+asyncpg://cybertrace:local@127.0.0.1:5432/cybertrace",
        "postgresql+asyncpg://cybertrace:local@[::1]:5432/cybertrace",
    ],
)
def test_local_database_targets_are_allowed_before_upgrade(database_url: str) -> None:
    module = safe_migrate_module()
    calls: list[tuple[object, str]] = []

    def upgrade(config: object, revision: str) -> None:
        calls.append((config, revision))

    module.run_local_migrations(database_url=database_url, upgrade=upgrade)

    assert len(calls) == 1
    assert calls[0][1] == "head"


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+asyncpg://postgres:secret@db.example.supabase.co:5432/postgres",
        "postgresql://postgres:secret@10.20.30.40:5432/postgres",
        "mysql://user:secret@localhost/example",
        "not-a-database-url",
    ],
)
def test_remote_or_unsupported_targets_fail_before_upgrade(database_url: str) -> None:
    module = safe_migrate_module()
    called = False

    def upgrade(_config: object, _revision: str) -> None:
        nonlocal called
        called = True

    with pytest.raises(module.UnsafeDatabaseTarget, match="local database"):
        module.run_local_migrations(database_url=database_url, upgrade=upgrade)

    assert called is False


def test_missing_database_url_fails_before_upgrade() -> None:
    module = safe_migrate_module()

    def upgrade(_config: object, _revision: str) -> None:
        return None

    with pytest.raises(module.UnsafeDatabaseTarget, match="DATABASE_URL"):
        module.run_local_migrations(database_url="", upgrade=upgrade)
