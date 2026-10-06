"""Measure the proposed export bounds only in the managed disposable PG run."""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from time import perf_counter
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from web_app.application.export_traffic_history_use_case import (
    MAX_EXPORT_BYTES,
    MAX_EXPORT_ROWS,
    ExportTrafficHistoryUseCase,
    TrafficHistoryExportTooLarge,
)
from web_app.infrastructure.repositories.traffic_log_repository import (
    TrafficLogRepository,
)

POSTGRES_URL = os.getenv("CYBERTRACE_POSTGRES_TEST_URL")
SQLALCHEMY_POSTGRES_URL = os.getenv("CYBERTRACE_SQLALCHEMY_TEST_URL")
IS_MANAGED_DISPOSABLE_RUN = (
    os.getenv("CYBERTRACE_EXPORT_BENCHMARK_DISPOSABLE") == "true"
)
pytestmark = pytest.mark.skipif(
    not POSTGRES_URL or not SQLALCHEMY_POSTGRES_URL or not IS_MANAGED_DISPOSABLE_RUN,
    reason="runs only inside the managed tmpfs PostgreSQL E2E environment",
)


def _assert_disposable_loopback_database(database_url: str) -> str:
    parsed = urlparse(database_url.replace("postgresql+psycopg:", "postgresql:", 1))
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise AssertionError("benchmark requires the managed loopback PostgreSQL")
    if parsed.path != "/cybertrace":
        raise AssertionError("benchmark database name is not the managed test database")
    return database_url.replace("postgresql+psycopg:", "postgresql:", 1)


def _relation_sizes(cursor: psycopg.Cursor) -> tuple[int, int, int]:
    cursor.execute(
        """
SELECT pg_relation_size('public.traffic_logs'),
       pg_indexes_size('public.traffic_logs'),
       pg_total_relation_size('public.traffic_logs')
"""
    )
    return tuple(int(value) for value in cursor.fetchone())


def _plan_summary(plan: dict[str, object]) -> tuple[list[str], int, int]:
    nodes: list[str] = []
    shared_hit = 0
    shared_read = 0
    pending = [plan["Plan"]]
    while pending:
        node = pending.pop()
        assert isinstance(node, dict)
        node_type = str(node.get("Node Type", "unknown"))
        index_name = node.get("Index Name")
        nodes.append(f"{node_type}:{index_name}" if index_name else node_type)
        shared_hit += int(node.get("Shared Hit Blocks", 0))
        shared_read += int(node.get("Shared Read Blocks", 0))
        pending.extend(node.get("Plans", []))
    return nodes, shared_hit, shared_read


def test_traffic_history_export_caps_and_records_local_database_measurements() -> None:
    assert POSTGRES_URL is not None
    assert SQLALCHEMY_POSTGRES_URL is not None
    connection_url = _assert_disposable_loopback_database(POSTGRES_URL)
    run_key = uuid4().hex
    row_count = MAX_EXPORT_ROWS
    today = datetime.now(timezone.utc).date()
    start_date = today - timedelta(days=30)
    range_start = datetime.combine(start_date, datetime.min.time(), timezone.utc)
    range_end = datetime.combine(
        today + timedelta(days=1), datetime.min.time(), timezone.utc
    )
    interval_seconds = int((range_end - range_start).total_seconds())

    with psycopg.connect(connection_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM public.traffic_logs")
            rows_before = int(cursor.fetchone()[0])
            bytes_before = _relation_sizes(cursor)

            records = [
                (
                    f"csv-export-benchmark-{run_key}-{index}",
                    range_start
                    + timedelta(seconds=(interval_seconds * index) // row_count),
                    f"/csv-export-benchmark/{run_key}",
                    f"POST /csv-export-benchmark/{run_key} benchmark-sentinel",
                )
                for index in range(row_count)
            ]
            cursor.executemany(
                """
INSERT INTO public.traffic_logs (
  transaction_id, timestamp, source_ip, source_provenance,
  source_verification_status, model_input_text, request_path, query_string,
  request_method, http_request, prediction, confidence, confidence_level,
  action_taken, triage_status, status
) VALUES (
  %s, %s, '203.0.113.45', 'DIRECT_REMOTE_ADDR', 'UNVERIFIED',
  'synthetic benchmark model input', %s, 'example=excluded',
  'POST', %s, 'SQL Injection', 0.93, 'HIGH', 'BLOCKED', NULL, 'COMPLETED'
)
""",
                records,
            )

            cursor.execute(
                """
SELECT count(*) FROM public.traffic_logs
WHERE transaction_id LIKE %s
""",
                (f"csv-export-benchmark-{run_key}-%",),
            )
            assert int(cursor.fetchone()[0]) == MAX_EXPORT_ROWS
            bytes_after = _relation_sizes(cursor)

            cursor.execute(
                """
EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)
SELECT id, timestamp, request_method, prediction, confidence,
       confidence_level, action_taken, triage_status
FROM public.traffic_logs
WHERE (status = 'COMPLETED' OR status IS NULL)
  AND prediction IN ('SQL Injection', 'Code Injection', 'Normal')
  AND timestamp >= %s AND timestamp < %s
  AND (source_ip ILIKE %s OR request_path ILIKE %s
       OR request_method ILIKE %s OR http_request ILIKE %s
       OR prediction ILIKE %s)
ORDER BY timestamp ASC, id ASC
LIMIT %s
""",
                (
                    range_start,
                    range_end,
                    f"%{run_key}%",
                    f"%{run_key}%",
                    f"%{run_key}%",
                    f"%{run_key}%",
                    f"%{run_key}%",
                    MAX_EXPORT_ROWS + 1,
                ),
            )
            plan = cursor.fetchone()[0][0]
            plan_nodes, shared_hit, shared_read = _plan_summary(plan)

    async def run_export_and_cap_check():
        engine = create_async_engine(SQLALCHEMY_POSTGRES_URL)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            started = perf_counter()
            async with session_factory() as session:
                exported = await ExportTrafficHistoryUseCase(
                    TrafficLogRepository(session, session_factory=session_factory)
                ).execute(
                    start_date=start_date,
                    end_date=today,
                    timezone_name="UTC",
                    include_normal=True,
                    search=run_key,
                )
            export_duration_ms = (perf_counter() - started) * 1_000
            assert exported.row_count == MAX_EXPORT_ROWS
            assert len(exported.content) <= MAX_EXPORT_BYTES

            with pytest.raises(TrafficHistoryExportTooLarge) as raised:
                async with session_factory() as session:
                    # Add cap + 1 only after verifying the accepted 20,000-row
                    # export, keeping both measurements distinct.
                    await session.execute(
                        text(
                            """
INSERT INTO public.traffic_logs (
  transaction_id, timestamp, source_ip, source_provenance,
  source_verification_status, model_input_text, request_path, query_string,
  request_method, http_request, prediction, confidence, confidence_level,
  action_taken, triage_status, status
) VALUES (
  :transaction_id, :timestamp, '203.0.113.45', 'DIRECT_REMOTE_ADDR',
  'UNVERIFIED', 'synthetic benchmark model input', :request_path,
  'example=excluded', 'POST', :http_request, 'SQL Injection', 0.93,
  'HIGH', 'BLOCKED', NULL, 'COMPLETED'
)
"""
                        ),
                        {
                            "transaction_id": (
                                f"csv-export-benchmark-{run_key}-{row_count}"
                            ),
                            "timestamp": range_start,
                            "request_path": f"/csv-export-benchmark/{run_key}",
                            "http_request": (
                                f"POST /csv-export-benchmark/{run_key} "
                                "benchmark-sentinel"
                            ),
                        },
                    )
                    await session.commit()
                    await ExportTrafficHistoryUseCase(
                        TrafficLogRepository(session, session_factory=session_factory)
                    ).execute(
                        start_date=start_date,
                        end_date=today,
                        timezone_name="UTC",
                        include_normal=True,
                        search=run_key,
                    )
            assert raised.value.reason == "row_limit"
            return exported, export_duration_ms
        finally:
            await engine.dispose()

    exported, export_ms = asyncio.run(
        run_export_and_cap_check(), loop_factory=asyncio.SelectorEventLoop
    )

    with psycopg.connect(connection_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT setting FROM pg_settings WHERE name = 'archive_mode'"
            )
            archive_mode = str(cursor.fetchone()[0])
            cursor.execute("SELECT setting FROM pg_settings WHERE name = 'wal_level'")
            wal_level = str(cursor.fetchone()[0])

    total_growth = bytes_after[2] - bytes_before[2]
    print(
        "TRAFFIC_HISTORY_EXPORT_MEASUREMENT "
        f"rows_before={rows_before} synthetic_rows={row_count} "
        f"heap_bytes_before={bytes_before[0]} index_bytes_before={bytes_before[1]} "
        f"relation_bytes_before={bytes_before[2]} heap_bytes_after={bytes_after[0]} "
        f"index_bytes_after={bytes_after[1]} relation_bytes_after={bytes_after[2]} "
        f"growth_bytes={total_growth} "
        f"growth_bytes_per_row={total_growth / row_count:.2f} "
        f"explain_ms={plan['Execution Time']:.2f} export_20k_ms={export_ms:.2f} "
        f"plan_nodes={','.join(plan_nodes)} shared_hit_blocks={shared_hit} "
        f"shared_read_blocks={shared_read} archive_mode={archive_mode} "
        f"wal_level={wal_level} backup_restore_test=not_run"
    )
