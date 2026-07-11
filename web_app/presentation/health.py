import logging

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.config import get_settings
from web_app.infrastructure.database import TrafficLog, get_db
from web_app.presentation.schemas import HealthResponse

logger = logging.getLogger(__name__)


async def health_check(
    request: Request, db: AsyncSession = Depends(get_db)
) -> HealthResponse:
    """Health check endpoint with database connectivity probe."""
    settings = get_settings()
    worker_status: str | None = None
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
    try:
        result = await db.execute(select(TrafficLog.id).limit(1))
        result.first()
        return HealthResponse(
            status="healthy",
            database="connected",
            notification_worker=worker_status,
        )
    except Exception:
        logger.warning("Health check database probe failed", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            database="disconnected",
            notification_worker=worker_status,
        )
