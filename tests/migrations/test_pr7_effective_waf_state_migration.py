from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Column, Integer, MetaData, create_engine, inspect, text

ROOT = Path(__file__).parents[2]
REVISION = "20260728_000025"
CURRENT_HEAD = "20260803_000028"


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def test_pr7_migration_is_the_single_new_head() -> None:
    assert ScriptDirectory.from_config(_config()).get_heads() == [CURRENT_HEAD]


def test_pr7_migration_declares_additive_effective_state() -> None:
    migration = (
        ROOT / "migrations" / "versions" / f"{REVISION}_add_pr7_effective_waf_state.py"
    )
    source = migration.read_text(encoding="utf-8")
    assert 'down_revision = "20260721_000024"' in source
    assert '"waf_enforcement_state"' in source
    assert '"waf_effective_state"' in source
    assert "recommendation_id" in source
    assert "status = 'ACTIVE'" in source
    assert "protected_path = '/records/search'" in source
    assert "activated_at IS NOT NULL" in source


def test_pr7_sqlite_upgrade_downgrade_and_reupgrade(
    tmp_path: Path, monkeypatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'pr7.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = _config()
    config.set_main_option("sqlalchemy.url", database_url)
    metadata = MetaData()
    from sqlalchemy import Table

    Table(
        "enforcement_recommendations", metadata, Column("id", Integer, primary_key=True)
    )
    engine = create_engine(database_url)
    metadata.create_all(engine)
    engine.dispose()
    command.stamp(config, "20260721_000024", sql=False)
    command.upgrade(config, REVISION)
    engine = create_engine(database_url)
    assert {"waf_enforcement_state", "waf_effective_state"} <= set(
        inspect(engine).get_table_names()
    )
    assert (
        engine.connect()
        .execute(text("SELECT revision FROM waf_enforcement_state WHERE id = 1"))
        .scalar_one()
        == 0
    )
    engine.dispose()
    command.downgrade(config, "20260721_000024")
    engine = create_engine(database_url)
    assert "waf_effective_state" not in inspect(engine).get_table_names()
    engine.dispose()
    command.upgrade(config, REVISION)
