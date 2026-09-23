from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    inspect,
    text,
)

ROOT = Path(__file__).parents[2]
REVISION = "20260924_000030"
PARENT_REVISION = "20260905_000029"
MIGRATION = (
    ROOT
    / "migrations"
    / "versions"
    / f"{REVISION}_route_aware_enforcement_contract.py"
)
SCOPES = (
    "'RECORD_SEARCH', 'RECORD_DETAIL', 'TRACK_STATUS', "
    "'SUPPORT_SUBMIT', 'APPOINTMENT_SUBMIT', 'COMMENTS_SUBMIT', "
    "'LOGIN_SUBMIT', 'REQUEST_COPY_SUBMIT'"
)


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


def _create_parent_schema(database_url: str) -> None:
    engine = create_engine(database_url)
    metadata = MetaData()
    Table("traffic_logs", metadata, Column("id", Integer, primary_key=True))
    Table(
        "enforcement_recommendations",
        metadata,
        Column("id", Integer, primary_key=True),
        Column(
            "trigger_traffic_log_id",
            Integer,
            ForeignKey("traffic_logs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        Column("scope", String(32), nullable=False),
        Column("enforcement_tier", String(10), nullable=False),
        Column("recommended_action", String(32), nullable=False),
        Column("enforcement_mode", String(16), nullable=False),
        Column("policy_version", String(64), nullable=False),
        Column("created_at", DateTime, nullable=False),
        Column("expires_at", DateTime, nullable=False),
        UniqueConstraint(
            "trigger_traffic_log_id",
            name="uq_enforcement_recommendations_trigger_traffic_log_id",
        ),
        CheckConstraint(
            "scope = 'RECORD_SEARCH'",
            name="enforcement_recommendations_scope_allowed",
        ),
        CheckConstraint(
            "enforcement_tier IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="enforcement_recommendations_tier_allowed",
        ),
        CheckConstraint(
            "recommended_action IN ("
            "'MONITOR', 'THROTTLE', 'APPLICATION_BLOCK', 'WAF_BLOCK'"
            ")",
            name="enforcement_recommendations_action_allowed",
        ),
        CheckConstraint(
            "enforcement_mode IN ('SHADOW', 'ENFORCE')",
            name="enforcement_recommendations_mode_allowed",
        ),
        Index(
            "ix_enforcement_recommendations_scope_expires_at",
            "scope",
            "expires_at",
        ),
    )
    Table(
        "enforcement_request_windows",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("source_ip", String(45), nullable=False),
        Column("scope", String(32), nullable=False),
        Column("counter_kind", String(32), nullable=False),
        Column("policy_version", String(64), nullable=False),
        Column("window_start", DateTime, nullable=False),
        Column("window_end", DateTime, nullable=False),
        Column("request_count", Integer, nullable=False),
        Column("created_at", DateTime, nullable=False),
        Column("updated_at", DateTime, nullable=False),
        UniqueConstraint(
            "source_ip",
            "scope",
            "counter_kind",
            "policy_version",
            "window_start",
            name="uq_enforcement_request_window_key",
        ),
        CheckConstraint(
            "scope = 'RECORD_SEARCH'",
            name="enforcement_request_windows_scope_allowed",
        ),
    )
    Table(
        "enforcement_challenge_grants",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("source_ip", String(45), nullable=False),
        Column("scope", String(32), nullable=False),
        Column("enforcement_tier", String(10), nullable=False),
        Column("policy_version", String(64), nullable=False),
        Column("verified_at", DateTime, nullable=False),
        Column("expires_at", DateTime, nullable=False),
        Column("created_at", DateTime, nullable=False),
        Column("updated_at", DateTime, nullable=False),
        UniqueConstraint(
            "source_ip",
            "scope",
            "enforcement_tier",
            "policy_version",
            name="uq_enforcement_challenge_grant_key",
        ),
        CheckConstraint(
            "scope = 'RECORD_SEARCH'",
            name="enforcement_challenge_grants_scope_allowed",
        ),
    )
    metadata.create_all(engine)
    engine.dispose()


def test_route_aware_migration_declares_additive_contract() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert f'down_revision = "{PARENT_REVISION}"' in source
    assert "decision_reason" in source
    assert "evidence_context" in source
    assert "REQUEST_COPY_SUBMIT" in source
    assert "ROW LEVEL SECURITY" in source.upper()


def test_sqlite_upgrade_allows_public_scopes_and_preserves_legacy_rows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'route-aware.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = _config()
    config.set_main_option("sqlalchemy.url", database_url)
    _create_parent_schema(database_url)
    command.stamp(config, PARENT_REVISION, sql=False)
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO traffic_logs (id) VALUES (1)"))
        connection.execute(
            text(
                "INSERT INTO enforcement_recommendations "
                "(trigger_traffic_log_id, scope, enforcement_tier, "
                "recommended_action, enforcement_mode, policy_version, "
                "created_at, expires_at) VALUES "
                "(1, 'SUPPORT_SUBMIT', 'MEDIUM', 'THROTTLE', 'ENFORCE', "
                "'confidence-enforcement-v2', '2026-09-24 00:00:00', "
                "'2026-09-24 00:15:00')"
            )
        )
        recommendation = connection.execute(
            text(
                "SELECT decision_reason, evidence_context FROM "
                "enforcement_recommendations WHERE id = 1"
            )
        ).one()
        assert recommendation.decision_reason == "LEGACY_POLICY"
        assert recommendation.evidence_context is None
        sql = connection.execute(
            text(
                "SELECT sql FROM sqlite_master "
                "WHERE name = 'enforcement_recommendations'"
            )
        ).scalar_one()
        assert all(scope in sql for scope in SCOPES.split(", "))
    columns = {
        item["name"]
        for item in inspect(engine).get_columns("enforcement_recommendations")
    }
    assert {"decision_reason", "evidence_context"} <= columns
    engine.dispose()
