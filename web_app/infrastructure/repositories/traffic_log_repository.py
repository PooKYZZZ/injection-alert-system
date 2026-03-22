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

from dataclasses import dataclass
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from typing import Optional, List

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.domain.interfaces import (
    ITrafficLogRepository,
    TrafficLogEntity,
    TrafficLogPage,
    TrafficStatsSummary,
    DriftMetrics,
    ActivityBucket,
    SourceIPSummary,
    TargetPathSummary,
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

    @staticmethod
    def _normalize_reference_time(reference_time: Optional[datetime]) -> datetime:
        if reference_time is None:
            return datetime.now(timezone.utc)
        if reference_time.tzinfo is None:
            return reference_time.replace(tzinfo=timezone.utc)
        return reference_time.astimezone(timezone.utc)

    @staticmethod
    def _resolve_window_delta(window: Optional[str]) -> timedelta:
        return TIME_RANGE_DELTAS.get(window or "24h", TIME_RANGE_DELTAS["24h"])

    @staticmethod
    def _resolve_timezone(timezone_name: Optional[str]) -> ZoneInfo:
        if not timezone_name:
            return ZoneInfo("UTC")
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            return ZoneInfo("UTC")

    def _resolve_window_bounds(
        self,
        window: Optional[str],
        reference_time: Optional[datetime],
    ) -> tuple[datetime, datetime, timedelta]:
        window_end = self._normalize_reference_time(reference_time)
        delta = self._resolve_window_delta(window)
        window_start = window_end - delta
        return window_start, window_end, delta

    async def _get_counts_for_range(
        self,
        start: Optional[datetime],
        end: Optional[datetime],
    ) -> dict[str, int]:
        filters = [self._completed_or_legacy_clause()]
        if start is not None:
            filters.append(TrafficLog.timestamp >= start)
        if end is not None:
            filters.append(TrafficLog.timestamp < end)

        result = await self._session.execute(
            select(
                func.count(TrafficLog.id).label("total_requests"),
                func.count().filter(TrafficLog.action_taken == "BLOCKED").label(
                    "blocked_count"
                ),
                func.count().filter(TrafficLog.action_taken == "ALLOWED").label(
                    "allowed_count"
                ),
                func.count().filter(TrafficLog.action_taken == "THROTTLED").label(
                    "throttled_count"
                ),
            ).where(*filters)
        )
        row = result.one()
        return {
            "total_requests": int(row.total_requests or 0),
            "blocked_count": int(row.blocked_count or 0),
            "allowed_count": int(row.allowed_count or 0),
            "throttled_count": int(row.throttled_count or 0),
        }

    async def _get_label_counts_for_range(
        self,
        start: Optional[datetime],
        end: Optional[datetime],
    ) -> dict[str, int]:
        filters = [self._completed_or_legacy_clause()]
        if start is not None:
            filters.append(TrafficLog.timestamp >= start)
        if end is not None:
            filters.append(TrafficLog.timestamp < end)

        counts_by_label = {label: 0 for label in CANONICAL_PREDICTION_LABELS}
        result = await self._session.execute(
            select(
                TrafficLog.prediction,
                func.count(TrafficLog.id).label("prediction_count"),
            ).where(*filters).group_by(TrafficLog.prediction)
        )
        for prediction, count in result.all():
            if prediction is None:
                continue
            counts_by_label[prediction] = int(count)
        return counts_by_label

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _entity_to_orm(entity: TrafficLogEntity) -> TrafficLog:
        """Convert a domain entity to an ORM model instance."""
        kwargs = {
            "transaction_id": entity.transaction_id,
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
            "lease_expires_at": entity.lease_expires_at,
            "processing_owner_token": entity.processing_owner_token,
            "processing_attempt": entity.processing_attempt,
            "action_taken": entity.action_taken,
            "analyst_label": entity.analyst_label,
            "labeled_at": entity.labeled_at,
            "labeled_by": entity.labeled_by,
            "triage_status": entity.triage_status,
        }

        if entity.created_at is not None:
            kwargs["created_at"] = entity.created_at
        if entity.timestamp is not None:
            kwargs["timestamp"] = entity.timestamp
        if entity.status is not None:
            kwargs["status"] = entity.status

        return TrafficLog(**kwargs)

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
            lease_expires_at=orm_obj.lease_expires_at,
            processing_owner_token=orm_obj.processing_owner_token,
            processing_attempt=orm_obj.processing_attempt,
            action_taken=orm_obj.action_taken,
            analyst_label=orm_obj.analyst_label,
            labeled_at=orm_obj.labeled_at,
            labeled_by=orm_obj.labeled_by,
            triage_status=orm_obj.triage_status,
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

    async def claim_or_reclaim_processing(
        self,
        entity: TrafficLogEntity,
        *,
        owner_token: str,
        lease_expires_at: datetime,
        now: datetime,
    ) -> TrafficLogEntity | None:
        """Claim a fresh PROCESSING row or reclaim a stale one atomically."""
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
            "lease_expires_at": lease_expires_at,
            "processing_owner_token": owner_token,
            "processing_attempt": 1,
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

        existing = await self.get_by_transaction_id(entity.transaction_id)
        if (
            existing is not None
            and existing.status == "PROCESSING"
            and existing.processing_owner_token == owner_token
        ):
            return existing

        update_stmt = (
            update(TrafficLog)
            .where(TrafficLog.transaction_id == entity.transaction_id)
            .where(
                and_(
                    TrafficLog.status == "PROCESSING",
                    TrafficLog.lease_expires_at.isnot(None),
                    TrafficLog.lease_expires_at < now,
                )
            )
            .values(
                timestamp=entity.timestamp,
                source_ip=entity.source_ip,
                request_path=entity.request_path,
                request_method=entity.request_method,
                http_request=entity.http_request,
                crs_score=entity.crs_score,
                crs_rule_ids=entity.crs_rule_ids,
                status="PROCESSING",
                lease_expires_at=lease_expires_at,
                processing_owner_token=owner_token,
                processing_attempt=TrafficLog.processing_attempt + 1,
            )
        )
        result = await self._session.execute(update_stmt)
        await self._session.commit()

        existing = await self.get_by_transaction_id(entity.transaction_id)
        if (
            existing is not None
            and existing.status == "PROCESSING"
            and existing.processing_owner_token == owner_token
        ):
            return existing
        if existing is not None and existing.status == "COMPLETED":
            return existing
        return None

    async def complete_processing(
        self,
        transaction_id: str,
        *,
        owner_token: str,
        prediction: str,
        confidence: float,
        confidence_level: str,
        inference_latency_ms: Optional[float],
        model_version: Optional[str],
        action_taken: str,
    ) -> TrafficLogEntity:
        """Complete a previously claimed PROCESSING row."""
        result = await self._session.execute(
            update(TrafficLog)
            .where(
                TrafficLog.transaction_id == transaction_id,
                TrafficLog.status == "PROCESSING",
                TrafficLog.processing_owner_token == owner_token,
            )
            .values(
                prediction=prediction,
                confidence=confidence,
                confidence_level=confidence_level,
                inference_latency_ms=inference_latency_ms,
                model_version=model_version,
                action_taken=action_taken,
                status="COMPLETED",
                lease_expires_at=None,
                processing_owner_token=None,
            )
        )
        await self._session.commit()
        if (result.rowcount or 0) == 0:
            existing = await self.get_by_transaction_id(transaction_id)
            if existing is None:
                raise RuntimeError("Completed traffic log could not be reloaded")
            return existing
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

    async def get_stats_summary(
        self,
        window: Optional[str] = None,
        reference_time: Optional[datetime] = None,
    ) -> TrafficStatsSummary:
        """Return aggregate traffic stats with zero-safe defaults.

        Args:
            window: Optional time window filter (1h, 6h, 24h, 7d). If None, returns all-time stats.
        """
        counts_by_label = {label: 0 for label in CANONICAL_PREDICTION_LABELS}

        window_start = None
        window_end = None
        previous_window_start = None
        if window:
            window_start, window_end, delta = self._resolve_window_bounds(
                window,
                reference_time,
            )
            previous_window_start = window_start - delta

        summary_where = [self._completed_or_legacy_clause()]
        if window_start is not None:
            summary_where.append(TrafficLog.timestamp >= window_start)
        if window_end is not None:
            summary_where.append(TrafficLog.timestamp < window_end)
        summary_result = await self._session.execute(
            select(
                func.count(TrafficLog.id).label("total_requests"),
                func.coalesce(func.avg(TrafficLog.inference_latency_ms), 0.0).label(
                    "avg_inference_latency_ms"
                ),
            ).where(*summary_where)
        )
        summary_row = summary_result.one()

        previous_counts = None
        previous_label_counts = None
        if (
            window_start is not None
            and previous_window_start is not None
            and window_end is not None
        ):
            current_counts, previous_counts, previous_label_counts = await asyncio.gather(
                self._get_counts_for_range(window_start, window_end),
                self._get_counts_for_range(previous_window_start, window_start),
                self._get_label_counts_for_range(previous_window_start, window_start),
            )
        else:
            current_counts = await self._get_counts_for_range(None, None)

        # Get avg_confidence honestly - only from non-null confidence values
        confidence_query = (
            select(
                func.avg(TrafficLog.confidence).label("avg_confidence"),
                func.count(TrafficLog.confidence).label("confidence_count"),
            )
            .where(self._completed_or_legacy_clause())
            .where(TrafficLog.confidence.isnot(None))
        )
        if window_start is not None:
            confidence_query = confidence_query.where(
                TrafficLog.timestamp >= window_start
            )
        if window_end is not None:
            confidence_query = confidence_query.where(
                TrafficLog.timestamp < window_end
            )

        confidence_result = await self._session.execute(confidence_query)
        confidence_row = confidence_result.one()

        # Return None if no non-null confidence values exist
        avg_confidence = None
        if confidence_row.confidence_count and confidence_row.confidence_count > 0:
            avg_confidence = round(float(confidence_row.avg_confidence), 3)

        # Get prediction counts (for counts_by_label and attack_distribution)
        counts_query = (
            select(
                TrafficLog.prediction,
                func.count(TrafficLog.id).label("prediction_count"),
            )
            .where(self._completed_or_legacy_clause())
            .group_by(TrafficLog.prediction)
        )
        if window_start is not None:
            counts_query = counts_query.where(TrafficLog.timestamp >= window_start)
        if window_end is not None:
            counts_query = counts_query.where(TrafficLog.timestamp < window_end)

        counts_result = await self._session.execute(counts_query)
        for prediction, count in counts_result.all():
            if prediction is None:
                continue
            counts_by_label[prediction] = int(count)

        # Get counts by action_taken from the same bounded window.
        blocked_count = current_counts["blocked_count"]
        allowed_count = current_counts["allowed_count"]
        throttled_count = current_counts["throttled_count"]

        # Get top source IPs with most recent action
        top_source_ips: List[SourceIPSummary] = []

        # Subquery to get most recent action per IP
        latest_action_subquery = (
            select(
                TrafficLog.source_ip,
                TrafficLog.action_taken,
                func.row_number()
                .over(
                    partition_by=TrafficLog.source_ip,
                    order_by=TrafficLog.timestamp.desc(),
                )
                .label("rn"),
            )
            .where(self._completed_or_legacy_clause())
            .where(TrafficLog.source_ip.isnot(None))
        )
        if window_start is not None:
            latest_action_subquery = latest_action_subquery.where(
                TrafficLog.timestamp >= window_start
            )
        if window_end is not None:
            latest_action_subquery = latest_action_subquery.where(
                TrafficLog.timestamp < window_end
            )
        latest_action_subquery = latest_action_subquery.subquery()

        # Get top IPs by count with their most recent action
        top_ips_query = (
            select(
                TrafficLog.source_ip,
                func.count(TrafficLog.id).label("request_count"),
                latest_action_subquery.c.action_taken.label("latest_action"),
            )
            .join(
                latest_action_subquery,
                (TrafficLog.source_ip == latest_action_subquery.c.source_ip)
                & (latest_action_subquery.c.rn == 1),
            )
            .where(self._completed_or_legacy_clause())
            .where(TrafficLog.source_ip.isnot(None))
            .group_by(TrafficLog.source_ip, latest_action_subquery.c.action_taken)
            .order_by(func.count(TrafficLog.id).desc())
            .limit(5)
        )
        if window_start is not None:
            top_ips_query = top_ips_query.where(TrafficLog.timestamp >= window_start)
        if window_end is not None:
            top_ips_query = top_ips_query.where(TrafficLog.timestamp < window_end)

        top_ips_result = await self._session.execute(top_ips_query)
        for row in top_ips_result.all():
            top_source_ips.append(
                SourceIPSummary(
                    ip=row.source_ip,
                    count=int(row.request_count),
                    action=row.latest_action,
                )
            )

        # Get top targeted paths
        top_targeted_paths: List[TargetPathSummary] = []

        paths_query = (
            select(
                TrafficLog.request_path,
                func.count(TrafficLog.id).label("hit_count"),
            )
            .where(self._completed_or_legacy_clause())
            .where(TrafficLog.request_path.isnot(None))
            .group_by(TrafficLog.request_path)
            .order_by(func.count(TrafficLog.id).desc())
            .limit(5)
        )
        if window_start is not None:
            paths_query = paths_query.where(TrafficLog.timestamp >= window_start)
        if window_end is not None:
            paths_query = paths_query.where(TrafficLog.timestamp < window_end)

        paths_result = await self._session.execute(paths_query)
        for row in paths_result.all():
            top_targeted_paths.append(
                TargetPathSummary(path=row.request_path, hits=int(row.hit_count))
            )

        false_positive_query = (
            select(func.count(TrafficLog.id).label("false_positive_count"))
            .where(
                self._completed_or_legacy_clause(),
                TrafficLog.action_taken == "ALLOWED",
                TrafficLog.prediction != "Normal",
            )
        )
        if window_start is not None:
            false_positive_query = false_positive_query.where(
                TrafficLog.timestamp >= window_start
            )
        if window_end is not None:
            false_positive_query = false_positive_query.where(
                TrafficLog.timestamp < window_end
            )
        false_positive_result = await self._session.execute(false_positive_query)
        false_positive_count = int(false_positive_result.scalar_one() or 0)
        total_requests = int(current_counts["total_requests"])
        false_positive_rate = (
            round((false_positive_count / total_requests) * 100, 2)
            if total_requests > 0
            else 0.0
        )

        # Attack distribution is counts_by_label filtered to attack types only
        attack_distribution = {
            k: v
            for k, v in counts_by_label.items()
            if k in ("SQL Injection", "Code Injection", "Other Attacks")
        }

        high_alert_count = sum(
            count for label, count in counts_by_label.items() if label != "Normal"
        )
        prev_high_alert_count = (
            sum(count for label, count in previous_label_counts.items() if label != "Normal")
            if previous_label_counts
            else None
        )

        return TrafficStatsSummary(
            total_requests=total_requests,
            counts_by_label=counts_by_label,
            avg_inference_latency_ms=round(
                float(summary_row.avg_inference_latency_ms or 0.0),
                3,
            ),
            blocked_count=blocked_count,
            allowed_count=allowed_count,
            throttled_count=throttled_count,
            avg_confidence=avg_confidence,
            false_positive_rate=false_positive_rate,
            false_positive_count=false_positive_count,
            high_alert_count=high_alert_count,
            prev_high_alert_count=prev_high_alert_count,
            prev_total_requests=previous_counts["total_requests"]
            if previous_counts
            else None,
            prev_blocked_count=previous_counts["blocked_count"]
            if previous_counts
            else None,
            prev_allowed_count=previous_counts["allowed_count"]
            if previous_counts
            else None,
            prev_throttled_count=previous_counts["throttled_count"]
            if previous_counts
            else None,
            attack_distribution=attack_distribution,
            top_source_ips=top_source_ips,
            top_targeted_paths=top_targeted_paths,
        )

    async def get_drift_metrics(self, recent_window: int = 100) -> DriftMetrics:
        """Compute drift metrics by comparing recent confidence to baseline.

        A simple drift signal: compare average confidence in recent N records
        vs. all-time average. If recent confidence is significantly lower,
        it may indicate model drift.

        Drift is computed only from rows with non-null confidence values.
        Returns unavailable state if insufficient usable data exists.

        Returns:
            DriftMetrics with drift_score (0-1, clamped), drift_detected, and confidence values.
            Returns None for unavailable fields when data is insufficient.
        """
        # Get baseline (all-time average confidence) from non-null confidence rows
        baseline_result = await self._session.execute(
            select(
                func.avg(TrafficLog.confidence).label("baseline_avg"),
                func.count(TrafficLog.confidence).label("confidence_count"),
            ).where(
                self._completed_or_legacy_clause(),
                TrafficLog.confidence.isnot(None),
            )
        )
        baseline_row = baseline_result.one()

        baseline_avg = (
            float(baseline_row.baseline_avg)
            if baseline_row.baseline_avg is not None
            else 0.0
        )
        baseline_count = int(baseline_row.confidence_count or 0)

        if baseline_count < recent_window:
            # Not enough baseline data for drift detection
            return DriftMetrics(
                drift_score=None,
                drift_detected=False,
                recent_mean_confidence=None,
                baseline_mean_confidence=round(baseline_avg, 4)
                if baseline_avg > 0
                else 0.0,
                recent_sample_size=0,
                baseline_sample_size=baseline_count,
            )

        # Get recent average confidence using correct subquery approach:
        # First select the N most recent rows with non-null confidence, then average them
        # This uses a subquery to ensure the N selection happens before the average
        recent_subquery = (
            select(TrafficLog.confidence)
            .where(
                self._completed_or_legacy_clause(),
                TrafficLog.confidence.isnot(None),
            )
            .order_by(TrafficLog.timestamp.desc())
            .limit(recent_window)
            .subquery()
        )

        recent_result = await self._session.execute(
            select(
                func.avg(recent_subquery.c.confidence).label("recent_avg"),
                func.count(recent_subquery.c.confidence).label("recent_count"),
            )
        )
        recent_row = recent_result.one()

        recent_avg = (
            float(recent_row.recent_avg) if recent_row.recent_avg is not None else 0.0
        )
        recent_count = int(recent_row.recent_count or 0)

        if recent_count < recent_window:
            # Not enough recent data for drift detection
            return DriftMetrics(
                drift_score=None,
                drift_detected=False,
                recent_mean_confidence=round(recent_avg, 4) if recent_avg > 0 else 0.0,
                baseline_mean_confidence=round(baseline_avg, 4),
                recent_sample_size=recent_count,
                baseline_sample_size=baseline_count,
            )

        if baseline_avg == 0:
            return DriftMetrics(
                drift_score=None,
                drift_detected=False,
                recent_mean_confidence=round(recent_avg, 4),
                baseline_mean_confidence=0.0,
                recent_sample_size=recent_count,
                baseline_sample_size=baseline_count,
            )

        # Compute drift score as relative change, clamped to 0-1 per schema
        raw_drift = abs(recent_avg - baseline_avg) / baseline_avg
        drift_score = min(1.0, max(0.0, round(raw_drift, 4)))

        # Consider drift detected if score > 10% (simple threshold)
        drift_detected = drift_score > 0.10

        return DriftMetrics(
            drift_score=drift_score,
            drift_detected=drift_detected,
            recent_mean_confidence=round(recent_avg, 4),
            baseline_mean_confidence=round(baseline_avg, 4),
            recent_sample_size=recent_count,
            baseline_sample_size=baseline_count,
        )

    async def get_activity_buckets(
        self,
        window: Optional[str] = None,
        buckets: int = 24,
        reference_time: Optional[datetime] = None,
        timezone_name: Optional[str] = None,
    ) -> List[ActivityBucket]:
        """Get bucketed activity counts for the hero activity strip.

        Returns a list of buckets representing activity over the specified time period.
        Each bucket contains total_count and blocked_count.

        Args:
            window: Optional time window filter (1h, 6h, 24h, 7d). Defaults to 24h.
            buckets: Number of buckets to divide the time into (default 24)
        """
        if buckets <= 0:
            return []

        window_start, window_end, delta = self._resolve_window_bounds(window, reference_time)
        local_tz = self._resolve_timezone(timezone_name)

        # Get all records in the time window
        result = await self._session.execute(
            select(
                TrafficLog.timestamp,
                TrafficLog.action_taken,
            )
            .where(self._completed_or_legacy_clause())
            .where(TrafficLog.timestamp >= window_start)
            .where(TrafficLog.timestamp < window_end)
        )
        records = result.all()

        # Initialize buckets
        bucket_data = [
            {"total": 0, "blocked": 0, "allowed": 0, "throttled": 0}
            for _ in range(buckets)
        ]

        window_seconds = int(delta.total_seconds())
        seconds_per_bucket = max(1, window_seconds // buckets)
        window_start_local = window_start.astimezone(local_tz)

        for record in records:
            timestamp = record.timestamp
            if timestamp is None:
                continue

            # Handle naive datetimes
            if timestamp.tzinfo is None:
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            local_timestamp = timestamp.astimezone(local_tz)
            # Calculate bucket index
            seconds_since_start = (local_timestamp - window_start_local).total_seconds()
            bucket_idx = int(seconds_since_start // seconds_per_bucket)
            bucket_idx = max(0, min(bucket_idx, buckets - 1))

            bucket_data[bucket_idx]["total"] += 1
            if record.action_taken == "BLOCKED":
                bucket_data[bucket_idx]["blocked"] += 1
            elif record.action_taken == "ALLOWED":
                bucket_data[bucket_idx]["allowed"] += 1
            elif record.action_taken == "THROTTLED":
                bucket_data[bucket_idx]["throttled"] += 1

        return [
            ActivityBucket(
                bucket_index=i,
                total_count=bucket_data[i]["total"],
                blocked_count=bucket_data[i]["blocked"],
                allowed_count=bucket_data[i]["allowed"],
                throttled_count=bucket_data[i]["throttled"],
                timestamp_start=(
                    window_start_local + timedelta(seconds=i * seconds_per_bucket)
                ).astimezone(timezone.utc),
                timestamp_end=(
                    window_start_local + timedelta(seconds=(i + 1) * seconds_per_bucket)
                ).astimezone(timezone.utc),
                bucket_width_seconds=seconds_per_bucket,
            )
            for i in range(buckets)
        ]

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

    async def list_recent(
        self, skip: int = 0, limit: int = 100
    ) -> List[TrafficLogEntity]:
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

    async def update_triage_status(
        self,
        traffic_id: int,
        triage_status: str,
    ) -> Optional[TrafficLogEntity]:
        """Update triage status on a traffic log. Returns None if not found."""
        result = await self._session.execute(
            select(TrafficLog).filter(TrafficLog.id == traffic_id)
        )
        orm_obj = result.scalars().first()
        if orm_obj is None:
            return None

        orm_obj.triage_status = triage_status
        await self._session.commit()
        await self._session.refresh(orm_obj)
        return self._orm_to_entity(orm_obj)
