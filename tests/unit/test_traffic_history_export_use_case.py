import csv
from datetime import date, datetime, timedelta, timezone
from io import StringIO
from unittest.mock import AsyncMock

import pytest

from web_app.application.export_traffic_history_use_case import (
    CSV_EXPORT_COLUMNS,
    MAX_EXPORT_ROWS,
    ExportTrafficHistoryUseCase,
    InvalidTrafficHistoryExportRange,
    TrafficHistoryExportTooLarge,
    _spreadsheet_text,
    inclusive_dates_to_utc_bounds,
)
from web_app.domain.interfaces import TrafficHistoryExportRecord


def test_inclusive_date_bounds_cover_a_leap_day_and_exact_midnight_boundary() -> None:
    start, end = inclusive_dates_to_utc_bounds(
        date(2024, 2, 29), date(2024, 2, 29), "UTC"
    )

    assert start == datetime(2024, 2, 29, tzinfo=timezone.utc)
    assert end == datetime(2024, 3, 1, tzinfo=timezone.utc)
    assert start <= datetime(2024, 2, 29, 23, 59, 59, tzinfo=timezone.utc) < end
    assert not (start <= end < end)


@pytest.mark.parametrize(
    ("day", "expected_hours"),
    [(date(2026, 3, 8), 23), (date(2026, 11, 1), 25)],
)
def test_date_bounds_follow_dst_calendar_midnights(
    day: date, expected_hours: int
) -> None:
    start, end = inclusive_dates_to_utc_bounds(day, day, "America/New_York")

    assert (end - start) == timedelta(hours=expected_hours)


@pytest.mark.parametrize(
    ("start", "end", "timezone_name"),
    [
        (date(2026, 1, 2), date(2026, 1, 1), "UTC"),
        (date(2026, 1, 1), date(2026, 2, 1), "UTC"),
        (date(2026, 1, 1), date(2026, 1, 1), "Not/A_Timezone"),
    ],
)
def test_invalid_date_ranges_are_rejected(
    start: date, end: date, timezone_name: str
) -> None:
    with pytest.raises(InvalidTrafficHistoryExportRange):
        inclusive_dates_to_utc_bounds(start, end, timezone_name)


@pytest.mark.parametrize(
    "value",
    [
        "=1+1",
        "+SUM(A1:A2)",
        "-1+2",
        "@SUM(A1:A2)",
        "  =1+1",
        "\r\n+1+1",
        "\t@SUM(A1:A2)",
        "＝1+1",
        "＋1+1",
        "－1+2",
        "＠SUM(A1:A2)",
    ],
)
def test_spreadsheet_formula_like_prefixes_are_tab_prefixed(value: str) -> None:
    assert _spreadsheet_text(value) == f"\t{value}"


def test_spreadsheet_mitigation_leaves_ordinary_text_unchanged() -> None:
    assert _spreadsheet_text("normal unicode: café") == "normal unicode: café"


@pytest.mark.asyncio
async def test_csv_is_allowlisted_quoted_unicode_and_excel_prefix_aware() -> None:
    repository = type("Repository", (), {})()
    repository.list_traffic_history_export_rows = AsyncMock(
        return_value=[
            TrafficHistoryExportRecord(
                traffic_log_id=8,
                timestamp=datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc),
                request_method='POST, "PATCH"\r\nGET',
                prediction="東京",
                confidence=0.91,
                confidence_level="HIGH",
                action_taken="BLOCKED",
                triage_status="in_review",
            ),
            TrafficHistoryExportRecord(
                traffic_log_id=9,
                timestamp=datetime(2026, 10, 1, 0, 1, tzinfo=timezone.utc),
                request_method="GET",
                prediction="=1+1",
                confidence=0.2,
                confidence_level="LOW",
                action_taken="ALLOWED",
                triage_status=None,
            ),
            TrafficHistoryExportRecord(
                traffic_log_id=10,
                timestamp=datetime(2026, 10, 1, 0, 2, tzinfo=timezone.utc),
                request_method="GET",
                prediction="\t@SUM(A1:A2)",
                confidence=None,
                confidence_level=None,
                action_taken=None,
                triage_status=None,
            ),
        ]
    )

    result = await ExportTrafficHistoryUseCase(repository).execute(
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 1),
        timezone_name="UTC",
    )
    parsed = list(csv.reader(StringIO(result.content.decode("utf-8"))))

    assert tuple(parsed[0]) == CSV_EXPORT_COLUMNS
    assert parsed[1][2] == 'POST, "PATCH"\r\nGET'
    assert parsed[1][3] == "東京"
    assert parsed[2][3] == "\t=1+1"
    assert parsed[3][3] == "\t\t@SUM(A1:A2)"
    assert "source_ip" not in parsed[0]
    assert "request_path" not in parsed[0]
    assert "query_string" not in parsed[0]
    assert "model_input_text" not in parsed[0]
    assert "2026-10-01T00:00:00Z" in result.content.decode("utf-8")


@pytest.mark.asyncio
async def test_export_rejects_more_than_row_cap_without_partial_csv() -> None:
    row = TrafficHistoryExportRecord(
        traffic_log_id=1,
        timestamp=datetime(2026, 10, 1, tzinfo=timezone.utc),
        request_method="GET",
        prediction="Normal",
        confidence=0.4,
        confidence_level="LOW",
        action_taken="ALLOWED",
        triage_status=None,
    )
    repository = type("Repository", (), {})()
    repository.list_traffic_history_export_rows = AsyncMock(
        return_value=[row] * (MAX_EXPORT_ROWS + 1)
    )

    with pytest.raises(TrafficHistoryExportTooLarge) as raised:
        await ExportTrafficHistoryUseCase(repository).execute(
            start_date=date(2026, 10, 1),
            end_date=date(2026, 10, 1),
            timezone_name="UTC",
        )

    assert raised.value.reason == "row_limit"
    repository.list_traffic_history_export_rows.assert_awaited_once()
    assert repository.list_traffic_history_export_rows.await_args.kwargs["limit"] == (
        MAX_EXPORT_ROWS + 1
    )


@pytest.mark.asyncio
async def test_export_rejects_oversized_cells_and_total_bytes_without_partial_file(
) -> None:
    oversized_cell = TrafficHistoryExportRecord(
        traffic_log_id=1,
        timestamp=datetime(2026, 10, 1, tzinfo=timezone.utc),
        request_method="G" * 4_097,
        prediction="SQL Injection",
        confidence=0.4,
        confidence_level="LOW",
        action_taken="ALLOWED",
        triage_status=None,
    )
    repository = type("Repository", (), {})()
    repository.list_traffic_history_export_rows = AsyncMock(
        return_value=[oversized_cell]
    )
    use_case = ExportTrafficHistoryUseCase(repository)
    request = {
        "start_date": date(2026, 10, 1),
        "end_date": date(2026, 10, 1),
        "timezone_name": "UTC",
    }

    with pytest.raises(TrafficHistoryExportTooLarge) as cell_error:
        await use_case.execute(**request)
    assert cell_error.value.reason == "cell_limit"

    large_row = TrafficHistoryExportRecord(
        traffic_log_id=2,
        timestamp=datetime(2026, 10, 1, tzinfo=timezone.utc),
        request_method="G" * 4_000,
        prediction="SQL Injection",
        confidence=0.4,
        confidence_level="LOW",
        action_taken="ALLOWED",
        triage_status=None,
    )
    repository.list_traffic_history_export_rows = AsyncMock(
        return_value=[large_row] * 1_500
    )
    with pytest.raises(TrafficHistoryExportTooLarge) as size_error:
        await use_case.execute(**request)
    assert size_error.value.reason == "byte_limit"


@pytest.mark.asyncio
async def test_export_passes_half_open_bounds_and_canonical_filters_to_repository(
) -> None:
    repository = type("Repository", (), {})()
    repository.list_traffic_history_export_rows = AsyncMock(return_value=[])

    await ExportTrafficHistoryUseCase(repository).execute(
        start_date=date(2026, 3, 8),
        end_date=date(2026, 3, 8),
        timezone_name="America/New_York",
        include_normal=True,
        severity="HIGH",
        search="safe example",
        confidence_levels=("HIGH",),
    )

    requested_filters = repository.list_traffic_history_export_rows.await_args.args[0]
    assert requested_filters.start_time == datetime(2026, 3, 8, 5, tzinfo=timezone.utc)
    assert requested_filters.end_time == datetime(2026, 3, 9, 4, tzinfo=timezone.utc)
    assert requested_filters.include_normal is True
    assert requested_filters.confidence_tier == "HIGH"
    assert requested_filters.search == "safe example"
    assert requested_filters.confidence_levels == ("HIGH",)
