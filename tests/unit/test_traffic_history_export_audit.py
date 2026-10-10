import json
import logging
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from fastapi import HTTPException

from web_app.application.label_review_use_case import ReviewerContext
from web_app.observability.context import reset_request_context, set_request_context
from web_app.presentation.api.traffic_history_export_router import (
    _log_traffic_history_export,
    export_traffic_history_csv,
)
from web_app.presentation.schemas import TrafficHistoryExportRequest


def test_export_audit_logs_correlation_and_metadata_without_filter_values(caplog):
    query = TrafficHistoryExportRequest(
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 7),
        timezone="Asia/Singapore",
        search="sensitive search phrase",
        source_ip="192.0.2.19",
    )
    tokens = set_request_context(
        request_id="export-audit-123",
        trace_id="0123456789abcdef0123456789abcdef",
    )
    try:
        with caplog.at_level(
            logging.INFO,
            logger="web_app.presentation.api.traffic_history_export_router",
        ):
            _log_traffic_history_export(
                actor=ReviewerContext("account-17", "ANALYST"),
                query=query,
                outcome="completed",
                row_count=12,
                start_time=datetime(2026, 9, 30, 16, tzinfo=timezone.utc),
                end_time=datetime(2026, 10, 7, 16, tzinfo=timezone.utc),
            )
    finally:
        reset_request_context(tokens)

    event = next(
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    )
    assert event["event"] == "traffic_history.csv_export"
    assert event["request_id"] == "export-audit-123"
    assert event["actor_id"] == "account-17"
    assert event["actor_role"] == "ANALYST"
    assert event["start_date"] == "2026-10-01"
    assert event["end_date"] == "2026-10-07"
    assert event["timezone"] == "Asia/Singapore"
    assert event["filter_names"] == ["search", "source_ip"]
    assert event["row_count"] == 12
    assert event["outcome"] == "completed"
    assert "sensitive search phrase" not in caplog.text
    assert "192.0.2.19" not in caplog.text
    assert "traffic_log_id" not in caplog.text


@pytest.mark.asyncio
async def test_denied_role_is_audited_without_filter_values(caplog):
    query = TrafficHistoryExportRequest(
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 2),
        timezone="UTC",
        search="private phrase",
        source_ip="192.0.2.22",
    )
    with caplog.at_level(
        logging.INFO,
        logger="web_app.presentation.api.traffic_history_export_router",
    ):
        with pytest.raises(HTTPException) as raised:
            await export_traffic_history_csv(
                query,
                repository=object(),
                actor=ReviewerContext("viewer-5", "VIEWER"),
            )

    assert raised.value.status_code == 403
    event = next(
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    )
    assert event["event"] == "traffic_history.csv_export"
    assert event["actor_id"] == "viewer-5"
    assert event["actor_role"] == "VIEWER"
    assert event["filter_names"] == ["search", "source_ip"]
    assert event["outcome"] == "denied"
    assert event["reason"] == "permission_denied"
    assert "private phrase" not in caplog.text
    assert "192.0.2.22" not in caplog.text


@pytest.mark.asyncio
async def test_future_export_date_returns_specific_validation_error_and_audit_reason(
    caplog,
):
    timezone_name = "Asia/Singapore"
    today = datetime.now(timezone.utc).astimezone(ZoneInfo(timezone_name)).date()
    future_date = today + timedelta(days=2)
    query = TrafficHistoryExportRequest(
        start_date=future_date,
        end_date=future_date,
        timezone=timezone_name,
    )

    with caplog.at_level(
        logging.INFO,
        logger="web_app.presentation.api.traffic_history_export_router",
    ):
        with pytest.raises(HTTPException) as raised:
            await export_traffic_history_csv(
                query,
                repository=object(),
                actor=ReviewerContext("analyst-9", "ANALYST"),
            )

    assert raised.value.status_code == 422
    assert raised.value.detail == "Export dates must be today or earlier."
    event = next(
        json.loads(record.getMessage())
        for record in caplog.records
        if record.getMessage().startswith("{")
    )
    assert event["outcome"] == "rejected"
    assert event["reason"] == "future_date"
