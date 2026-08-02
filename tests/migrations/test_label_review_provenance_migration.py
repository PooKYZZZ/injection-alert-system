from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine, inspect

ROOT = Path(__file__).parents[2]
PARENT = "20260802_000026"
REVISION = "20260802_000027"


def _config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _create_parent_schema(database_url: str) -> None:
    engine = create_engine(database_url)
    metadata = MetaData()
    traffic_logs = Table(
        "traffic_logs",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("http_request", Text, nullable=False),
    )
    Table(
        "traffic_label_reviews",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("traffic_log_id", Integer, nullable=False),
        Column("model_version", String(100), nullable=True),
        Column("input_hash", String(64), nullable=True),
    )
    metadata.create_all(engine)
    engine.dispose()


def test_provenance_migration_preserves_nullable_legacy_columns(tmp_path: Path, monkeypatch):
    database_url = f"sqlite:///{(tmp_path / 'provenance.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    _create_parent_schema(database_url)
    config = _config(database_url)
    command.stamp(config, PARENT, sql=False)
    command.upgrade(config, REVISION)

    engine = create_engine(database_url)
    traffic_columns = {column["name"] for column in inspect(engine).get_columns("traffic_logs")}
    review_columns = {column["name"] for column in inspect(engine).get_columns("traffic_label_reviews")}
    assert {"model_input_hash", "preprocessing_version"}.issubset(traffic_columns)
    assert {
        "prediction_confidence",
        "prediction_confidence_level",
        "model_input_hash",
        "preprocessing_version",
        "ingest_event_hash",
        "source_verification_status",
        "source_provenance",
    }.issubset(review_columns)
    engine.dispose()

    command.downgrade(config, PARENT)
    command.upgrade(config, REVISION)
