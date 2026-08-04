from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine, inspect

ROOT = Path(__file__).parents[2]
REVISION = "20260802_000026"
PARENT_REVISION = "20260728_000025"
MIGRATION = ROOT / "migrations" / "versions" / f"{REVISION}_add_traffic_label_reviews.py"


def _config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _create_parent_schema(database_url: str) -> None:
    engine = create_engine(database_url)
    metadata = MetaData()
    Table("traffic_logs", metadata, Column("id", Integer, primary_key=True), Column("http_request", Text, nullable=False))
    metadata.create_all(engine)
    engine.dispose()


def test_migration_is_chained_from_current_head():
    source = MIGRATION.read_text(encoding="utf-8")
    assert f'down_revision = "{PARENT_REVISION}"' in source
    assert "traffic_label_reviews" in source
    assert "traffic_logs.id" in source


def test_sqlite_upgrade_downgrade_and_reupgrade_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    database_url = f"sqlite:///{(tmp_path / 'label-reviews.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    _create_parent_schema(database_url)
    config = _config(database_url)
    command.stamp(config, PARENT_REVISION, sql=False)
    command.upgrade(config, REVISION)
    engine = create_engine(database_url)
    assert "traffic_label_reviews" in inspect(engine).get_table_names()
    engine.dispose()

    command.downgrade(config, PARENT_REVISION)
    engine = create_engine(database_url)
    assert "traffic_label_reviews" not in inspect(engine).get_table_names()
    engine.dispose()

    command.upgrade(config, REVISION)
    engine = create_engine(database_url)
    assert "traffic_label_reviews" in inspect(engine).get_table_names()
    engine.dispose()
