"""Authenticated HTTP route for bounded Traffic History CSV exports."""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import SQLAlchemyError

from web_app.application.export_traffic_history_use_case import (
    ExportTrafficHistoryUseCase,
    InvalidTrafficHistoryExportRange,
    TrafficHistoryExportTooLarge,
)
from web_app.application.label_review_use_case import ReviewerContext
from web_app.domain.authorization import Permission, role_has_permission
from web_app.infrastructure.repositories.traffic_log_repository import (
    TrafficLogRepository,
)
from web_app.observability.structured_logging import log_event
from web_app.presentation.api.routes import get_repository
from web_app.presentation.dependencies.auth import verify_internal_token
from web_app.presentation.dependencies.authorization import (
    get_reviewer_context,
)
from web_app.presentation.schemas import TrafficHistoryExportRequest

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(verify_internal_token)])


def _traffic_export_filter_names(query: TrafficHistoryExportRequest) -> list[str]:
    names = []
    if query.include_normal:
        names.append("include_normal")
    if query.confidence_tier:
        names.append("confidence_tier")
    if query.severity:
        names.append("severity")
    if query.search:
        names.append("search")
    if query.action:
        names.append("action")
    if query.triage_status:
        names.append("triage_status")
    if query.confidence_level:
        names.append("confidence_level")
    if query.prediction:
        names.append("prediction")
    if query.source_ip:
        names.append("source_ip")
    return names


def _log_traffic_history_export(
    *,
    actor: ReviewerContext,
    query: TrafficHistoryExportRequest,
    outcome: str,
    row_count: int | None = None,
    count_is_lower_bound: bool = False,
    reason: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> None:
    log_event(
        logger,
        "traffic_history.csv_export",
        "Traffic History CSV export processed",
        component="traffic-history-export",
        actor_id=actor.reviewer_id,
        actor_role=actor.reviewer_role,
        start_date=query.start_date.isoformat(),
        end_date=query.end_date.isoformat(),
        timezone=query.timezone,
        start_time_utc=start_time.isoformat() if start_time else None,
        end_time_utc=end_time.isoformat() if end_time else None,
        filter_names=_traffic_export_filter_names(query),
        row_count=row_count,
        count_is_lower_bound=count_is_lower_bound,
        outcome=outcome,
        reason=reason,
    )


@router.post("/traffic-history/export")
async def export_traffic_history_csv(
    query: TrafficHistoryExportRequest,
    repository: TrafficLogRepository = Depends(get_repository),
    actor: ReviewerContext = Depends(get_reviewer_context),
) -> Response:
    """Return a bounded allowlisted export through the trusted Next.js BFF."""
    if not role_has_permission(actor.reviewer_role, Permission.TRAFFIC_EXPORT):
        _log_traffic_history_export(
            actor=actor,
            query=query,
            outcome="denied",
            reason="permission_denied",
        )
        raise HTTPException(status_code=403, detail="Permission required")

    use_case = ExportTrafficHistoryUseCase(repository)
    try:
        result = await use_case.execute(
            start_date=query.start_date,
            end_date=query.end_date,
            timezone_name=query.timezone,
            include_normal=query.include_normal,
            severity=query.severity,
            confidence_tier=query.confidence_tier,
            search=query.search,
            action=query.action,
            triage_status=query.triage_status,
            confidence_levels=tuple(query.confidence_level or ()),
            prediction=query.prediction,
            source_ip=query.source_ip,
        )
    except InvalidTrafficHistoryExportRange as exc:
        _log_traffic_history_export(
            actor=actor,
            query=query,
            outcome="rejected",
            reason=exc.reason,
        )
        raise HTTPException(
            status_code=422,
            detail=(
                "Export dates must be today or earlier."
                if exc.reason == "future_date"
                else "Date range or filters are invalid."
            ),
        ) from None
    except TrafficHistoryExportTooLarge as exc:
        _log_traffic_history_export(
            actor=actor,
            query=query,
            outcome="rejected",
            reason=exc.reason,
            row_count=exc.observed_count,
            count_is_lower_bound=exc.count_is_lower_bound,
        )
        raise HTTPException(
            status_code=413,
            detail=(
                "Export exceeds the allowed size. Narrow the date range or "
                "filters and retry."
            ),
        ) from None
    except SQLAlchemyError as exc:
        timed_out = getattr(getattr(exc, "orig", None), "sqlstate", None) == "57014"
        _log_traffic_history_export(
            actor=actor,
            query=query,
            outcome="timed_out" if timed_out else "failed",
            reason="query_timeout" if timed_out else "database_unavailable",
        )
        raise HTTPException(
            status_code=504 if timed_out else 503,
            detail="Traffic History export is temporarily unavailable.",
        ) from None
    except Exception as exc:
        _log_traffic_history_export(
            actor=actor,
            query=query,
            outcome="failed",
            reason=type(exc).__name__,
        )
        raise HTTPException(
            status_code=503,
            detail="Traffic History export is temporarily unavailable.",
        ) from None

    _log_traffic_history_export(
        actor=actor,
        query=query,
        outcome="completed",
        row_count=result.row_count,
        start_time=result.start_time,
        end_time=result.end_time,
    )
    filename = (
        f"traffic-history_{query.start_date.isoformat()}_to_"
        f"{query.end_date.isoformat()}.csv"
    )
    return Response(
        content=result.content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
