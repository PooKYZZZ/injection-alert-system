"""
web_app/infrastructure/repositories/traffic_log_repository.py

Concrete implementation of ITrafficLogRepository using SQLAlchemy async sessions.

Architectural role:
  - Infrastructure layer — implements domain repository interface
  - Maps between domain TrafficLogEntity and ORM TrafficLog model
  - All ORM-specific code is isolated here

Dependency rule:
  - Imports from domain/ (the interface it implements)
  - Imports from infrastructure/database (ORM models, session)
  - Does NOT import from presentation/ or application/
"""

from datetime import datetime
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.domain.interfaces import ITrafficLogRepository, TrafficLogEntity
from web_app.infrastructure.database.database import TrafficLog


class TrafficLogRepository(ITrafficLogRepository):
    """SQLAlchemy-backed repository for traffic log persistence."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _entity_to_orm(entity: TrafficLogEntity) -> TrafficLog:
        """Convert a domain entity to an ORM model instance."""
        return TrafficLog(
            source_ip=entity.source_ip,
            http_request=entity.http_request,
            prediction=entity.prediction,
            confidence=entity.confidence,
            confidence_level=entity.confidence_level,
            model_version=entity.model_version,
            action_taken=entity.action_taken,
            analyst_label=entity.analyst_label,
            labeled_at=entity.labeled_at,
            labeled_by=entity.labeled_by,
        )

    @staticmethod
    def _orm_to_entity(orm_obj: TrafficLog) -> TrafficLogEntity:
        """Convert an ORM model instance to a domain entity."""
        return TrafficLogEntity(
            id=orm_obj.id,
            timestamp=orm_obj.timestamp,
            source_ip=orm_obj.source_ip,
            http_request=orm_obj.http_request,
            prediction=orm_obj.prediction,
            confidence=orm_obj.confidence,
            confidence_level=orm_obj.confidence_level,
            model_version=orm_obj.model_version,
            action_taken=orm_obj.action_taken,
            analyst_label=orm_obj.analyst_label,
            labeled_at=orm_obj.labeled_at,
            labeled_by=orm_obj.labeled_by,
        )

    # ------------------------------------------------------------------
    # Interface implementation
    # ------------------------------------------------------------------

    async def save(self, entity: TrafficLogEntity) -> TrafficLogEntity:
        """Persist a traffic log entity and return it with its assigned ID."""
        orm_obj = self._entity_to_orm(entity)
        self._session.add(orm_obj)
        await self._session.commit()
        await self._session.refresh(orm_obj)
        return self._orm_to_entity(orm_obj)

    async def get_by_id(self, traffic_id: int) -> Optional[TrafficLogEntity]:
        """Retrieve a single traffic log by its ID."""
        result = await self._session.execute(
            select(TrafficLog).filter(TrafficLog.id == traffic_id)
        )
        orm_obj = result.scalars().first()
        if orm_obj is None:
            return None
        return self._orm_to_entity(orm_obj)

    async def list_recent(self, skip: int = 0, limit: int = 100) -> List[TrafficLogEntity]:
        """Retrieve recent traffic logs ordered by timestamp descending."""
        result = await self._session.execute(
            select(TrafficLog)
            .order_by(TrafficLog.timestamp.desc())
            .offset(skip)
            .limit(limit)
        )
        return [self._orm_to_entity(row) for row in result.scalars().all()]

    async def update_feedback(
        self,
        traffic_id: int,
        analyst_label: str,
        analyst_email: str,
        labeled_at: datetime,
    ) -> Optional[TrafficLogEntity]:
        """Update analyst feedback on a traffic log. Returns None if not found."""
        result = await self._session.execute(
            select(TrafficLog).filter(TrafficLog.id == traffic_id)
        )
        orm_obj = result.scalars().first()
        if orm_obj is None:
            return None

        orm_obj.analyst_label = analyst_label
        orm_obj.labeled_by = analyst_email
        orm_obj.labeled_at = labeled_at
        await self._session.commit()
        await self._session.refresh(orm_obj)
        return self._orm_to_entity(orm_obj)
