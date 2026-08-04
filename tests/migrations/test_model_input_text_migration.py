from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Column, Integer, MetaData, Table, Text, create_engine, inspect

ROOT = Path(__file__).parents[2]
PARENT = "20260802_000027"
REVISION = "20260803_000028"


def _config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_model_input_text_migration_is_additive_and_reversible(tmp_path: Path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'model-input.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    engine = create_engine(database_url)
    metadata = MetaData()
    Table("traffic_logs", metadata, Column("id", Integer, primary_key=True))
    Table(
        "traffic_label_reviews",
        metadata,
        Column("id", Integer, primary_key=True),
    )
    metadata.create_all(engine)
    engine.dispose()

    config = _config(database_url)
    command.stamp(config, PARENT, sql=False)
    command.upgrade(config, REVISION)
    engine = create_engine(database_url)
    assert "model_input_text" in {
        column["name"] for column in inspect(engine).get_columns("traffic_logs")
    }
    assert "model_input_text" in {
        column["name"]
        for column in inspect(engine).get_columns("traffic_label_reviews")
    }
    engine.dispose()

    command.downgrade(config, PARENT)
