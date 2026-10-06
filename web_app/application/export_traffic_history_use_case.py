"""Bounded, spreadsheet-focused Traffic History CSV export use case."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from io import StringIO
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from web_app.domain.interfaces import (
    ITrafficLogRepository,
    TrafficHistoryExportFilters,
)

MAX_EXPORT_RANGE_DAYS = 31
MAX_EXPORT_ROWS = 20_000
MAX_EXPORT_BYTES = 5 * 1024 * 1024
MAX_EXPORT_CELL_CHARACTERS = 4_096

CSV_EXPORT_COLUMNS = (
    "traffic_log_id",
    "timestamp_utc",
    "request_method",
    "classification",
    "model_confidence_score",
    "model_confidence_tier",
    "recorded_action_label",
    "triage_status",
)

_FORMULA_AFTER_PREFIX = re.compile(r"^[\x00-\x20\u00a0\u200b\ufeff]*[=+\-@＝＋－＠]")


class InvalidTrafficHistoryExportRange(ValueError):
    """The inclusive calendar-date range or timezone is not supported."""


class TrafficHistoryExportTooLarge(ValueError):
    def __init__(self, *, reason: str, observed_count: int) -> None:
        super().__init__(reason)
        self.reason = reason
        self.observed_count = observed_count
        self.count_is_lower_bound = reason == "row_limit"


@dataclass(frozen=True)
class TrafficHistoryCsvExport:
    content: bytes
    row_count: int
    start_time: datetime
    end_time: datetime
    timezone_name: str


def inclusive_dates_to_utc_bounds(
    start_date: date,
    end_date: date,
    timezone_name: str,
) -> tuple[datetime, datetime]:
    if end_date < start_date:
        raise InvalidTrafficHistoryExportRange("reversed_range")
    if (end_date - start_date).days + 1 > MAX_EXPORT_RANGE_DAYS:
        raise InvalidTrafficHistoryExportRange("range_limit")
    try:
        selected_zone = ZoneInfo(timezone_name)
        exclusive_end_date = end_date + timedelta(days=1)
    except (ZoneInfoNotFoundError, OverflowError, ValueError) as exc:
        raise InvalidTrafficHistoryExportRange("invalid_timezone_or_date") from exc

    start_local = datetime.combine(start_date, time.min, tzinfo=selected_zone)
    end_local = datetime.combine(exclusive_end_date, time.min, tzinfo=selected_zone)
    return (
        start_local.astimezone(timezone.utc),
        end_local.astimezone(timezone.utc),
    )


def _spreadsheet_text(value: str | None) -> str:
    text = value or ""
    if len(text) > MAX_EXPORT_CELL_CHARACTERS:
        raise TrafficHistoryExportTooLarge(
            reason="cell_limit",
            observed_count=1,
        )
    if _FORMULA_AFTER_PREFIX.match(text):
        # Excel-oriented mitigation. The retained leading tab changes the
        # underlying field value and is not universal across spreadsheet apps.
        return f"\t{text}"
    return text


def _format_utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


class ExportTrafficHistoryUseCase:
    def __init__(self, repository: ITrafficLogRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        start_date: date,
        end_date: date,
        timezone_name: str,
        include_normal: bool = False,
        confidence_tier: str | None = None,
        severity: str | None = None,
        search: str | None = None,
        action: str | None = None,
        triage_status: str | None = None,
        confidence_levels: tuple[str, ...] = (),
        prediction: str | None = None,
        source_ip: str | None = None,
    ) -> TrafficHistoryCsvExport:
        start_time, end_time = inclusive_dates_to_utc_bounds(
            start_date,
            end_date,
            timezone_name,
        )
        if confidence_tier and severity and confidence_tier != severity:
            raise InvalidTrafficHistoryExportRange("conflicting_confidence_tiers")

        filters = TrafficHistoryExportFilters(
            start_time=start_time,
            end_time=end_time,
            include_normal=include_normal,
            confidence_tier=confidence_tier or severity,
            search=search,
            action=action,
            triage_status=triage_status,
            confidence_levels=confidence_levels,
            prediction=prediction,
            source_ip=source_ip,
        )
        rows = await self._repository.list_traffic_history_export_rows(
            filters,
            limit=MAX_EXPORT_ROWS + 1,
        )
        if len(rows) > MAX_EXPORT_ROWS:
            raise TrafficHistoryExportTooLarge(
                reason="row_limit",
                observed_count=MAX_EXPORT_ROWS + 1,
            )

        buffer = StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(CSV_EXPORT_COLUMNS)
        chunks = [buffer.getvalue().encode("utf-8")]
        encoded_size = len(chunks[0])
        buffer.seek(0)
        buffer.truncate(0)
        for row_number, row in enumerate(rows, start=1):
            writer.writerow(
                (
                    row.traffic_log_id,
                    _format_utc_timestamp(row.timestamp),
                    _spreadsheet_text(row.request_method),
                    _spreadsheet_text(row.prediction),
                    "" if row.confidence is None else str(row.confidence),
                    _spreadsheet_text(row.confidence_level),
                    _spreadsheet_text(row.action_taken),
                    _spreadsheet_text(row.triage_status),
                )
            )
            row_bytes = buffer.getvalue().encode("utf-8")
            if encoded_size + len(row_bytes) > MAX_EXPORT_BYTES:
                raise TrafficHistoryExportTooLarge(
                    reason="byte_limit",
                    observed_count=row_number,
                )
            chunks.append(row_bytes)
            encoded_size += len(row_bytes)
            buffer.seek(0)
            buffer.truncate(0)
        content = b"".join(chunks)
        return TrafficHistoryCsvExport(
            content=content,
            row_count=len(rows),
            start_time=start_time,
            end_time=end_time,
            timezone_name=timezone_name,
        )
