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

from datetime import datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.domain.interfaces import (
    ITrafficLogRepository,
    TrafficLogEntity,
    TrafficLogPage,
    TrafficStatsSummary,
)
from web_app.infrastructure.database.database import TrafficLog

CANONICAL_PREDICTION_LABELS = (
    "SQL Injection",
    "Code Injection",
    "Other Attacks",
    "Normal",
)

TIME_RANGE_DELTAS = {
    "1h": timedelta(hours=1),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
}


class TrafficLogRepository(ITrafficLogRepository):
    """SQLAlchemy-backed repository for traffic log persistence."""

    def __init__(self, session: AsyncSession):
        self._session = session

    @staticmethod
    def _completed_or_legacy_clause():
        return or_(TrafficLog.status == "COMPLETED", TrafficLog.status.is_(None))

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _entity_to_orm(entity: TrafficLogEntity) -> TrafficLog:
        """Convert a domain entity to an ORM model instance."""
        return TrafficLog(
            transaction_id=entity.transaction_id,
            created_at=entity.created_at,
            timestamp=entity.timestamp,
            source_ip=entity.source_ip,
            request_path=entity.request_path,
            request_method=entity.request_method,
            http_request=entity.http_request,
            crs_score=entity.crs_score,
            crs_rule_ids=entity.crs_rule_ids,
            prediction=entity.prediction,
            confidence=entity.confidence,
            confidence_level=entity.confidence_level,
            inference_latency_ms=entity.inference_latency_ms,
            status=entity.status,
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
            transaction_id=orm_obj.transaction_id,
            created_at=orm_obj.created_at,
            timestamp=orm_obj.timestamp,
            source_ip=orm_obj.source_ip,
            request_path=orm_obj.request_path,
            request_method=orm_obj.request_method,
            http_request=orm_obj.http_request,
            crs_score=orm_obj.crs_score,
            crs_rule_ids=orm_obj.crs_rule_ids,
            prediction=orm_obj.prediction,
            confidence=orm_obj.confidence,
            confidence_level=orm_obj.confidence_level,
            inference_latency_ms=orm_obj.inference_latency_ms,
            status=orm_obj.status,
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

    async def save_if_absent(
        self,
        entity: TrafficLogEntity,
    ) -> tuple[TrafficLogEntity, bool]:
        """Insert once by transaction_id, returning the existing row on conflict."""
        if not entity.transaction_id:
            return await self.save(entity), True

        values = {
            "transaction_id": entity.transaction_id,
            "timestamp": entity.timestamp,
            "source_ip": entity.source_ip,
            "request_path": entity.request_path,
            "request_method": entity.request_method,
            "http_request": entity.http_request,
            "crs_score": entity.crs_score,
            "crs_rule_ids": entity.crs_rule_ids,
            "prediction": entity.prediction,
            "confidence": entity.confidence,
            "confidence_level": entity.confidence_level,
            "inference_latency_ms": entity.inference_latency_ms,
            "model_version": entity.model_version,
            "action_taken": entity.action_taken,
            "analyst_label": entity.analyst_label,
            "labeled_at": entity.labeled_at,
            "labeled_by": entity.labeled_by,
        }

        dialect_name = self._session.bind.dialect.name if self._session.bind else ""
        if dialect_name == "postgresql":
            insert_stmt = postgresql_insert(TrafficLog).values(**values)
        else:
            insert_stmt = sqlite_insert(TrafficLog).values(**values)

        result = await self._session.execute(
            insert_stmt.on_conflict_do_nothing(
                index_elements=[TrafficLog.transaction_id]
            ).returning(TrafficLog.id)
        )
        inserted_id = result.scalar_one_or_none()
        await self._session.commit()

        if inserted_id is None:
            existing = await self.get_by_transaction_id(entity.transaction_id)
            if existing is None:
                raise RuntimeError(
                    "Traffic log insert conflicted on transaction_id but no existing row was found"
                )
            return existing, False

        created = await self.get_by_id(inserted_id)
        if created is None:
            raise RuntimeError("Inserted traffic log could not be reloaded")
        return created, True

    async def claim_processing(self, entity: TrafficLogEntity) -> bool:
        """Reserve a transaction_id with a PROCESSING placeholder row."""
        if not entity.transaction_id:
            raise ValueError("transaction_id is required to claim processing")

        values = {
            "transaction_id": entity.transaction_id,
            "timestamp": entity.timestamp,
            "source_ip": entity.source_ip,
            "request_path": entity.request_path,
            "request_method": entity.request_method,
            "http_request": entity.http_request,
            "crs_score": entity.crs_score,
            "crs_rule_ids": entity.crs_rule_ids,
            "status": "PROCESSING",
        }

        dialect_name = self._session.bind.dialect.name if self._session.bind else ""
        if dialect_name == "postgresql":
            insert_stmt = postgresql_insert(TrafficLog).values(**values)
        else:
            insert_stmt = sqlite_insert(TrafficLog).values(**values)

        result = await self._session.execute(
            insert_stmt.on_conflict_do_nothing(
                index_elements=[TrafficLog.transaction_id]
            )
        )
        await self._session.commit()
        return (result.rowcount or 0) > 0

    async def complete_processing(
        self,
        transaction_id: str,
        *,
        prediction: str,
        confidence: float,
        confidence_level: str,
        inference_latency_ms: Optional[float],
        model_version: Optional[str],
        action_taken: str,
    ) -> TrafficLogEntity:
        """Complete a previously claimed PROCESSING row."""
        await self._session.execute(
            update(TrafficLog)
            .where(TrafficLog.transaction_id == transaction_id)
            .values(
                prediction=prediction,
                confidence=confidence,
                confidence_level=confidence_level,
                inference_latency_ms=inference_latency_ms,
                model_version=model_version,
                action_taken=action_taken,
                status="COMPLETED",
            )
        )
        await self._session.commit()
        completed = await self.get_by_transaction_id(transaction_id)
        if completed is None:
            raise RuntimeError("Completed traffic log could not be reloaded")
        return completed

    async def get_by_id(self, traffic_id: int) -> Optional[TrafficLogEntity]:
        """Retrieve a single traffic log by its ID."""
        result = await self._session.execute(
            select(TrafficLog).filter(
                TrafficLog.id == traffic_id,
                self._completed_or_legacy_clause(),
            )
        )
        orm_obj = result.scalars().first()
        if orm_obj is None:
            return None
        return self._orm_to_entity(orm_obj)

    async def get_by_transaction_id(
        self,
        transaction_id: str,
    ) -> Optional[TrafficLogEntity]:
        """Retrieve a single traffic log by its transaction ID."""
        result = await self._session.execute(
            select(TrafficLog).filter(TrafficLog.transaction_id == transaction_id)
        )
        orm_obj = result.scalars().first()
        if orm_obj is None:
            return None
        return self._orm_to_entity(orm_obj)

    async def get_stats_summary(self) -> TrafficStatsSummary:
        """Return aggregate traffic stats with zero-safe defaults."""
        counts_by_label = {label: 0 for label in CANONICAL_PREDICTION_LABELS}

        summary_result = await self._session.execute(
            select(
                func.count(TrafficLog.id).label("total_requests"),
                func.coalesce(func.avg(TrafficLog.inference_latency_ms), 0.0).label(
                    "avg_inference_latency_ms"
                ),
            )
            .where(self._completed_or_legacy_clause())
        )
        summary_row = summary_result.one()

        counts_result = await self._session.execute(
            select(
                TrafficLog.prediction,
                func.count(TrafficLog.id).label("prediction_count"),
            )
            .where(self._completed_or_legacy_clause())
            .group_by(TrafficLog.prediction)
        )
        for prediction, count in counts_result.all():
            if prediction is None:
                continue
            counts_by_label[prediction] = int(count)

        return TrafficStatsSummary(
            total_requests=int(summary_row.total_requests or 0),
            counts_by_label=counts_by_label,
            avg_inference_latency_ms=round(
                float(summary_row.avg_inference_latency_ms or 0.0),
                3,
            ),
        )

    async def get_alert_list(
        self,
        page: int,
        page_size: int,
        severity: Optional[str] = None,
        time_range: Optional[str] = None,
        search: Optional[str] = None,
    ) -> TrafficLogPage:
        """Return a filtered, paginated alert list with deterministic ordering."""
        page = max(page, 1)
        page_size = max(1, min(page_size, 100))
        offset = (page - 1) * page_size

        stmt = select(TrafficLog).where(self._completed_or_legacy_clause())

        # PD1 semantics: the "severity" filter currently maps directly to the
        # persisted confidence tier. If policy/action severity diverges later,
        # update the API contract and repository filter together rather than
        # silently reinterpreting this parameter.
        if severity and severity != "ALL":
            stmt = stmt.where(TrafficLog.confidence_level == severity)

        if time_range in TIME_RANGE_DELTAS:
            cutoff = datetime.now(timezone.utc) - TIME_RANGE_DELTAS[time_range]
            stmt = stmt.where(TrafficLog.timestamp >= cutoff)

        if search:
            search_value = f"%{search.strip()}%"
            if search_value != "%%":
                stmt = stmt.where(
                    or_(
                        TrafficLog.source_ip.ilike(search_value),
                        TrafficLog.request_path.ilike(search_value),
                        TrafficLog.request_method.ilike(search_value),
                        TrafficLog.http_request.ilike(search_value),
                        TrafficLog.prediction.ilike(search_value),
                    )
                )

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self._session.execute(total_stmt)
        total = int(total_result.scalar_one() or 0)

        stmt = (
            stmt.order_by(TrafficLog.timestamp.desc(), TrafficLog.id.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await self._session.execute(stmt)
        rows = result.scalars().all()
        items = [self._orm_to_entity(row) for row in rows]
        return TrafficLogPage(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def list_recent(self, skip: int = 0, limit: int = 100) -> List[TrafficLogEntity]:
        """Retrieve recent traffic logs ordered by timestamp descending."""
        result = await self._session.execute(
            select(TrafficLog)
            .where(self._completed_or_legacy_clause())
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
