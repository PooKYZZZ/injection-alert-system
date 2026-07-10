import importlib.util
from pathlib import Path

import pytest


MIGRATION = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260324_000007_add_waf_query_string.py"
)


def load_migration():
    spec = importlib.util.spec_from_file_location(
        "waf_query_string_migration",
        MIGRATION,
    )
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_upgrade_fails_loudly_when_traffic_logs_is_missing(monkeypatch):
    migration = load_migration()
    monkeypatch.setattr(migration, "_column_names", lambda table: None)

    with pytest.raises(
        RuntimeError,
        match="traffic_logs must exist before applying revision 20260324_000007",
    ):
        migration.upgrade()


def test_upgrade_remains_idempotent_when_query_string_exists(monkeypatch):
    migration = load_migration()
    monkeypatch.setattr(
        migration,
        "_column_names",
        lambda table: {"id", "query_string"},
    )
    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda *args, **kwargs: pytest.fail("query_string must not be added twice"),
    )

    migration.upgrade()


def test_upgrade_adds_query_string_when_table_exists(monkeypatch):
    migration = load_migration()
    calls = []
    monkeypatch.setattr(migration, "_column_names", lambda table: {"id"})
    monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda table, column: calls.append((table, column.name, column.nullable)),
    )

    migration.upgrade()

    assert calls == [("traffic_logs", "query_string", True)]


def test_downgrade_drops_query_string_only_when_present(monkeypatch):
    migration = load_migration()
    calls = []
    monkeypatch.setattr(
        migration.op,
        "drop_column",
        lambda table, column: calls.append((table, column)),
    )

    monkeypatch.setattr(migration, "_column_names", lambda table: {"id"})
    migration.downgrade()
    monkeypatch.setattr(
        migration,
        "_column_names",
        lambda table: {"id", "query_string"},
    )
    migration.downgrade()

    assert calls == [("traffic_logs", "query_string")]
