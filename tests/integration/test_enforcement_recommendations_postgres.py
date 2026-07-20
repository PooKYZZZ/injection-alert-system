from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import psycopg
import pytest

POSTGRES_URL = os.getenv("CYBERTRACE_POSTGRES_TEST_URL")
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL,
    reason="requires an explicit disposable PostgreSQL URL",
)


@pytest.fixture(autouse=True)
def migrated_database(monkeypatch: pytest.MonkeyPatch):
    assert POSTGRES_URL is not None
    monkeypatch.setenv("DATABASE_URL", POSTGRES_URL)
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO traffic_logs (
                    source_ip, source_provenance,
                    source_verification_status, http_request
                ) VALUES (
                    '203.0.113.10', 'DIRECT_REMOTE_ADDR',
                    'UNVERIFIED', 'GET /records/search'
                )
                RETURNING id
                """
            )
            trigger_id = cursor.fetchone()[0]

    yield trigger_id

    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM enforcement_recommendations "
                "WHERE trigger_traffic_log_id = %s",
                (trigger_id,),
            )
            cursor.execute("DELETE FROM traffic_logs WHERE id = %s", (trigger_id,))


def test_concurrent_recommendation_inserts_are_idempotent(
    migrated_database: int,
) -> None:
    assert POSTGRES_URL is not None
    trigger_id = migrated_database
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
                        %s, 'RECORD_SEARCH', 'HIGH', 'APPLICATION_BLOCK',
                        'SHADOW', 'confidence-enforcement-v1', now(),
                        now() + interval '15 minutes'
                    )
                    ON CONFLICT (trigger_traffic_log_id) DO NOTHING
                    RETURNING id
                    """,
                    (trigger_id,),
                )
                row = cursor.fetchone()
            connection.commit()
            return row[0] if row else None

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: insert_recommendation(), range(2)))

    inserted_ids = [value for value in results if value is not None]
    assert len(inserted_ids) == 1
    with psycopg.connect(POSTGRES_URL, autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT count(*) FROM enforcement_recommendations "
                "WHERE trigger_traffic_log_id = %s",
                (trigger_id,),
            )
            assert cursor.fetchone()[0] == 1
