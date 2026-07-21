from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine, inspect, text


ROOT = Path(__file__).parents[2]
REVISION = "20260720_000023"
CURRENT_HEAD = "20260721_000024"
PARENT_REVISION = "20260720_000022"
MIGRATION = ROOT / "migrations" / "versions" / f"{REVISION}_add_shadow_enforcement_recommendations.py"


def _alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def _create_parent_traffic_logs(database_url: str) -> None:
    engine = create_engine(database_url)
    metadata = MetaData()
    Table(
        "traffic_logs",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("source_ip", String(45), nullable=True),
        Column("http_request", Text, nullable=False),
    )
    metadata.create_all(engine)
    engine.dispose()


def test_shadow_enforcement_migration_is_the_single_new_head() -> None:
    config = _alembic_config()
    assert ScriptDirectory.from_config(config).get_heads() == [CURRENT_HEAD]
    source = MIGRATION.read_text(encoding="utf-8")
    assert 'down_revision = "20260720_000022"' in source
    assert '"enforcement_recommendations"' in source
    assert "trigger_traffic_log_id" in source
    assert 'ondelete="RESTRICT"' in source
    assert "RECORD_SEARCH" in source
    assert "APPLICATION_BLOCK" in source
    assert "WAF_BLOCK" in source
    assert "ROW LEVEL SECURITY" in source.upper()


def test_sqlite_upgrade_downgrade_and_reupgrade_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'shadow-enforcement.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = _alembic_config()
    _create_parent_traffic_logs(database_url)
    command.stamp(config, PARENT_REVISION)

    command.upgrade(config, REVISION)
    engine = create_engine(database_url)
    table_names = set(inspect(engine).get_table_names())
    assert "enforcement_recommendations" in table_names
    columns = {column["name"] for column in inspect(engine).get_columns("enforcement_recommendations")}
    assert {
        "id",
        "trigger_traffic_log_id",
        "scope",
        "enforcement_tier",
        "recommended_action",
        "enforcement_mode",
        "policy_version",
        "created_at",
        "expires_at",
    } <= columns
    engine.dispose()

    command.downgrade(config, PARENT_REVISION)
    engine = create_engine(database_url)
    assert "enforcement_recommendations" not in inspect(engine).get_table_names()
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    assert "enforcement_recommendations" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == CURRENT_HEAD
    engine.dispose()
