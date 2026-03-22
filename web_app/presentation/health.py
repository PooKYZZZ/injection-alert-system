from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.infrastructure.database import TrafficLog, get_db
from web_app.presentation.schemas import HealthResponse


async def health_check(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    """Health check endpoint with database connectivity probe."""
    try:
        result = await db.execute(select(TrafficLog.id).limit(1))
        result.first()
        return HealthResponse(status="healthy", database="connected")
    except Exception:
        return HealthResponse(status="unhealthy", database="disconnected")
