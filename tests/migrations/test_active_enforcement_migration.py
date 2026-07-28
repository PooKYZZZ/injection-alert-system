from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import (
    CheckConstraint,
    Column,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    inspect,
    text,
)

ROOT = Path(__file__).parents[2]
REVISION = "20260721_000024"
CURRENT_HEAD = "20260728_000025"
PARENT_REVISION = "20260720_000023"
MIGRATION = ROOT / "migrations" / "versions" / f"{REVISION}_add_active_enforcement_state.py"


def _alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def _create_parent_schema(database_url: str) -> None:
    engine = create_engine(database_url)
    metadata = MetaData()
    Table(
        "traffic_logs",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("source_ip", String(45), nullable=True),
        Column("http_request", Text, nullable=False),
    )
    Table(
        "enforcement_recommendations",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("trigger_traffic_log_id", Integer, nullable=False, unique=True),
        Column("scope", String(32), nullable=False),
        Column("enforcement_tier", String(10), nullable=False),
        Column("recommended_action", String(32), nullable=False),
        Column("enforcement_mode", String(16), nullable=False, server_default="SHADOW"),
        Column("policy_version", String(64), nullable=False),
        Column("created_at", String, nullable=False),
        Column("expires_at", String, nullable=False),
        CheckConstraint("scope = 'RECORD_SEARCH'", name="enforcement_recommendations_scope_allowed"),
        CheckConstraint(
            "enforcement_tier IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="enforcement_recommendations_tier_allowed",
        ),
        CheckConstraint(
            "recommended_action IN ('MONITOR', 'THROTTLE', 'APPLICATION_BLOCK', 'WAF_BLOCK')",
            name="enforcement_recommendations_action_allowed",
        ),
        CheckConstraint(
            "enforcement_mode = 'SHADOW'",
            name="enforcement_recommendations_mode_allowed",
        ),
    )
    metadata.create_all(engine)
    engine.dispose()


def test_active_enforcement_migration_is_the_new_single_head() -> None:
    config = _alembic_config()
    assert ScriptDirectory.from_config(config).get_heads() == [CURRENT_HEAD]
    source = MIGRATION.read_text(encoding="utf-8")
    assert 'down_revision = "20260720_000023"' in source
    assert '"enforcement_request_windows"' in source
    assert '"enforcement_challenge_grants"' in source
    assert "ON CONFLICT" not in source.upper()
    assert "ROW LEVEL SECURITY" in source.upper()


def test_sqlite_upgrade_downgrade_and_reupgrade_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'active-enforcement.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = _alembic_config()
    config.set_main_option("sqlalchemy.url", database_url)
    _create_parent_schema(database_url)
    command.stamp(config, PARENT_REVISION, sql=False)
    command.upgrade(config, REVISION)
    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert {"enforcement_recommendations", "enforcement_request_windows", "enforcement_challenge_grants"} <= tables
    with engine.connect() as connection:
        checks = connection.execute(
            text("SELECT sql FROM sqlite_master WHERE name='enforcement_recommendations'")
        ).scalar_one()
        assert "ENFORCE" in checks
    engine.dispose()

    command.downgrade(config, PARENT_REVISION)
    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert "enforcement_request_windows" not in tables
    assert "enforcement_challenge_grants" not in tables
    assert "enforcement_recommendations" in tables
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    assert {
        "enforcement_request_windows",
        "enforcement_challenge_grants",
    } <= set(inspect(engine).get_table_names())
    engine.dispose()
