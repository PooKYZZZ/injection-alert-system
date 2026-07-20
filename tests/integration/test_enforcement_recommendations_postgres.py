from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import psycopg
import pytest
from alembic import command
from alembic.config import Config

POSTGRES_URL = os.getenv("CYBERTRACE_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires an explicit disposable PostgreSQL URL",
)

ROOT = Path(__file__).parents[2]
PARENT_REVISION = "20260720_000022"
REVISION = "20260720_000023"


def _alembic_config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(ROOT / "migrations"))
    return config


@pytest.fixture(autouse=True)
def migrated_database(monkeypatch: pytest.MonkeyPatch):
    assert POSTGRES_URL is not None
    monkeypatch.setenv("DATABASE_URL", POSTGRES_URL)
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS enforcement_recommendations CASCADE")
            cursor.execute("DROP TABLE IF EXISTS traffic_logs CASCADE")
            cursor.execute(
                """
                CREATE TABLE traffic_logs (
                    id integer PRIMARY KEY,
                    source_ip varchar(45),
                    source_verification_status varchar(32) NOT NULL
                )
                """
            )

    config = _alembic_config()
    command.stamp(config, PARENT_REVISION)
    command.upgrade(config, REVISION)
    yield

    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS enforcement_recommendations CASCADE")
            cursor.execute("DROP TABLE IF EXISTS traffic_logs CASCADE")


def test_concurrent_recommendation_inserts_are_idempotent() -> None:
    assert POSTGRES_URL is not None
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO traffic_logs (
                    id, source_ip, source_verification_status
                ) VALUES (1, %s, 'UNVERIFIED')
                """,
                ("203.0.113.10",),
            )

    barrier = Barrier(2)

    def insert_recommendation() -> int | None:
        with psycopg.connect(POSTGRES_URL) as connection:
            barrier.wait(timeout=5)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO enforcement_recommendations (
                        trigger_traffic_log_id, scope, enforcement_tier,
                        recommended_action, enforcement_mode, policy_version,
                        created_at, expires_at
                    ) VALUES (
                        1, 'RECORD_SEARCH', 'HIGH', 'APPLICATION_BLOCK',
                        'SHADOW', 'confidence-enforcement-v1', now(),
                        now() + interval '15 minutes'
                    )
                    ON CONFLICT (trigger_traffic_log_id) DO NOTHING
                    RETURNING id
                    """
                )
                row = cursor.fetchone()
            connection.commit()
            return row[0] if row else None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: insert_recommendation(), range(2)))

    assert sorted(value for value in results if value is not None) == [1]
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM enforcement_recommendations")
            assert cursor.fetchone()[0] == 1
