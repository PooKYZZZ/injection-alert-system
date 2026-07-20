from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import (
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
from sqlalchemy.exc import IntegrityError


ROOT = Path(__file__).parents[2]
PARENT_REVISION = "20260712_000020"
HEAD_REVISION = "20260720_000023"


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
        Column("transaction_id", String(128), unique=True),
        Column("source_ip", String(45), nullable=True),
        Column("http_request", Text, nullable=False),
    )
    metadata.create_all(engine)
    engine.dispose()


def test_sqlite_upgrade_downgrade_and_reupgrade_cycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "source-metadata-cycle.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = _alembic_config()
    _create_parent_traffic_logs(database_url)
    command.stamp(config, PARENT_REVISION)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO traffic_logs
                    (transaction_id, source_ip, http_request)
                VALUES
                    ('historical-source', '203.0.113.10', 'GET /source'),
                    ('historical-null', NULL, 'GET /null')
                """
            )
        )
    engine.dispose()

    command.upgrade(config, HEAD_REVISION)

    engine = create_engine(database_url)
    columns = {
        column["name"]: column
        for column in inspect(engine).get_columns("traffic_logs")
    }
    assert columns["source_provenance"]["nullable"] is False
    assert columns["source_verification_status"]["nullable"] is False
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT transaction_id, source_provenance,
                       source_verification_status, ingest_fingerprint_sha256
                FROM traffic_logs
                ORDER BY transaction_id
                """
            )
        ).mappings().all()
    assert rows == [
        {
            "transaction_id": "historical-null",
            "source_provenance": "LEGACY_UNKNOWN",
            "source_verification_status": "LEGACY_UNKNOWN",
            "ingest_fingerprint_sha256": None,
        },
        {
            "transaction_id": "historical-source",
            "source_provenance": "LEGACY_UNKNOWN",
            "source_verification_status": "LEGACY_UNKNOWN",
            "ingest_fingerprint_sha256": None,
        },
    ]
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO traffic_logs
                    (transaction_id, source_ip, http_request,
                     source_provenance, source_verification_status)
                VALUES
                    ('valid-cloudflare-verified', '203.0.113.20', 'GET /valid',
                     'CLOUDFLARE_CONNECTING_IP', 'VERIFIED'),
                    ('valid-cloudflare-unverified', '203.0.113.21', 'GET /valid',
                     'CLOUDFLARE_CONNECTING_IP', 'UNVERIFIED'),
                    ('valid-direct-unverified', '203.0.113.22', 'GET /valid',
                     'DIRECT_REMOTE_ADDR', 'UNVERIFIED'),
                    ('valid-direct-invalid', NULL, 'GET /valid',
                     'DIRECT_REMOTE_ADDR', 'INVALID'),
                    ('valid-legacy', NULL, 'GET /valid',
                     'LEGACY_UNKNOWN', 'LEGACY_UNKNOWN')
                """
            )
        )
    # This is an isolated executable proof of this revision's add/backfill/
    # constraint/downgrade behavior against a minimal parent-shaped table. The
    # disposable PostgreSQL chain tests the complete historical schema,
    # relationships, indexes, and PostgreSQL-specific behavior.
    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO traffic_logs
                        (transaction_id, source_ip, http_request,
                         source_provenance, source_verification_status)
                    VALUES
                        ('invalid-combination', NULL, 'GET /invalid',
                         'DIRECT_REMOTE_ADDR', 'VERIFIED')
                    """
                )
            )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO traffic_logs
                        (transaction_id, source_ip, http_request,
                         source_provenance, source_verification_status)
                    VALUES
                        ('invalid-null-verified', NULL, 'GET /invalid-null',
                         'CLOUDFLARE_CONNECTING_IP', 'VERIFIED')
                    """
                )
            )
    engine.dispose()

    command.downgrade(config, PARENT_REVISION)
    engine = create_engine(database_url)
    downgraded_columns = {
        column["name"] for column in inspect(engine).get_columns("traffic_logs")
    }
    assert "source_provenance" not in downgraded_columns
    assert "source_verification_status" not in downgraded_columns
    assert "ingest_fingerprint_sha256" not in downgraded_columns
    engine.dispose()

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    upgraded_columns = {
        column["name"] for column in inspect(engine).get_columns("traffic_logs")
    }
    assert {
        "source_provenance",
        "source_verification_status",
        "ingest_fingerprint_sha256",
    } <= upgraded_columns
    engine.dispose()


def test_migration_remains_the_single_expected_head() -> None:
    config = _alembic_config()
    assert ScriptDirectory.from_config(config).get_heads() == [HEAD_REVISION]
