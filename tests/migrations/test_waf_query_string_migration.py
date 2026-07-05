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
    add_column = monkeypatch.setattr(
        migration.op,
        "add_column",
        lambda *args, **kwargs: pytest.fail("query_string must not be added twice"),
    )

    migration.upgrade()

    assert add_column is None
