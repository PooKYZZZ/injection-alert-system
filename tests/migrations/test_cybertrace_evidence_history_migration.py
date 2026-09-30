from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    inspect,
    text,
)

ROOT = Path(__file__).parents[2]
REVISION = "20260930_000031"
PARENT_REVISION = "20260924_000030"
MIGRATION = (
    ROOT
    / "migrations"
    / "versions"
    / f"{REVISION}_cybertrace_evidence_history.py"
)


def _alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def _create_parent_traffic_logs(database_url: str) -> None:
    engine = create_engine(database_url)
    metadata = MetaData()
    traffic_logs = Table(
        "traffic_logs",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("confidence_level", String(10), nullable=True),
    )
    traffic_label_reviews = Table(
        "traffic_label_reviews",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("prediction_confidence_level", String(10), nullable=True),
    )
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            traffic_logs.insert().values(id=1, confidence_level="HIGH")
        )
        connection.execute(
            traffic_label_reviews.insert().values(
                id=1, prediction_confidence_level="LOW"
            )
        )
    engine.dispose()


def test_migration_is_linked_to_current_head_and_keeps_unknowns_nullable() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert f'revision = "{REVISION}"' in source
    assert f'down_revision = "{PARENT_REVISION}"' in source
    assert '"request_correlation_id"' in source
    assert '"observed_http_status"' in source
    assert '"traffic_log_action_history"' in source
    assert "ENABLE ROW LEVEL SECURITY" in source


def test_sqlite_upgrade_downgrade_reupgrade_preserves_existing_rows(
    tmp_path: Path, monkeypatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'cybertrace-evidence.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = _alembic_config()
    _create_parent_traffic_logs(database_url)
    command.stamp(config, PARENT_REVISION)

    command.upgrade(config, REVISION)
    engine = create_engine(database_url)
    inspector = inspect(engine)
    columns = {column["name"]: column for column in inspector.get_columns("traffic_logs")}
    assert set(
        {
            "request_correlation_id",
            "observed_http_status",
        }
    ).issubset(columns)
    assert columns["request_correlation_id"]["nullable"] is True
    assert columns["observed_http_status"]["nullable"] is True
    assert columns["confidence_level"]["type"].length == 13
    review_columns = {
        column["name"]: column
        for column in inspector.get_columns("traffic_label_reviews")
    }
    assert review_columns["prediction_confidence_level"]["type"].length == 13
    assert "traffic_log_action_history" in set(inspector.get_table_names())
    with engine.connect() as connection:
        old_row = connection.execute(
            text(
                "SELECT request_correlation_id, observed_http_status, confidence_level "
                "FROM traffic_logs WHERE id = 1"
            )
        ).one()
        old_review_tier = connection.execute(
            text(
                "SELECT prediction_confidence_level FROM traffic_label_reviews "
                "WHERE id = 1"
            )
        ).scalar_one()
    assert tuple(old_row) == (None, None, "HIGH")
    assert old_review_tier == "LOW"
    engine.dispose()

    command.downgrade(config, PARENT_REVISION)
    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert "traffic_log_action_history" not in set(inspector.get_table_names())
    remaining_columns = {
        column["name"] for column in inspector.get_columns("traffic_logs")
    }
    assert "request_correlation_id" not in remaining_columns
    downgraded_traffic_columns = {
        column["name"]: column for column in inspect(engine).get_columns("traffic_logs")
    }
    downgraded_review_columns = {
        column["name"]: column
        for column in inspect(engine).get_columns("traffic_label_reviews")
    }
    assert downgraded_traffic_columns["confidence_level"]["type"].length == 10
    assert downgraded_review_columns["prediction_confidence_level"]["type"].length == 10
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT id FROM traffic_logs WHERE id = 1")
        ).scalar_one() == 1
    engine.dispose()

    command.upgrade(config, REVISION)


def test_downgrade_refuses_to_drop_information_tier_support(
    tmp_path: Path, monkeypatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'cybertrace-info-tier.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = _alembic_config()
    _create_parent_traffic_logs(database_url)
    command.stamp(config, PARENT_REVISION)
    command.upgrade(config, REVISION)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "UPDATE traffic_logs SET confidence_level = 'INFORMATIONAL' "
                "WHERE id = 1"
            )
        )

    with pytest.raises(RuntimeError, match="INFORMATIONAL values are stored"):
        command.downgrade(config, PARENT_REVISION)

    inspector = inspect(engine)
    assert "traffic_log_action_history" in set(inspector.get_table_names())
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT confidence_level FROM traffic_logs WHERE id = 1")
        ).scalar_one() == "INFORMATIONAL"
    engine.dispose()
