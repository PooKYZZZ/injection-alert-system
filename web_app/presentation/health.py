import logging

from fastapi import Depends, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.config import get_settings
from web_app.infrastructure.database import TrafficLog, get_db
from web_app.observability.structured_logging import log_event
from web_app.presentation.schemas import HealthResponse

logger = logging.getLogger(__name__)


async def health_check(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """Return readiness plus safe component detail for both health routes."""
    settings = get_settings()
    if settings.notification_worker_enabled:
        worker = getattr(request.app.state, "notification_worker", None)
        if worker is None:
            worker_status = "unavailable"
        elif worker.last_error_class is not None:
            worker_status = "unhealthy"
        elif worker.running and worker.last_poll_at is not None:
            worker_status = "healthy"
        else:
            worker_status = "starting"
    else:
        worker_status = "disabled"

    database_status = "connected"
    try:
        result = await db.execute(select(TrafficLog.id).limit(1))
        result.first()
    except Exception as exc:
        database_status = "disconnected"
        log_event(
            logger,
            "health.database_unavailable",
            "Health database probe failed",
            level="WARNING",
            error_class=type(exc).__name__,
        )

    required_worker_unready = (
        settings.notification_worker_enabled
        and settings.notification_worker_required
        and worker_status != "healthy"
    )
    ready = database_status == "connected" and not required_worker_unready
    response.status_code = (
        status.HTTP_200_OK if ready else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return HealthResponse(
        status="healthy" if ready else "unhealthy",
        database=database_status,
        notification_worker=worker_status,
    )
