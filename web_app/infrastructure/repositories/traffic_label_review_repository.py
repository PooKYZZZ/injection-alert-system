"""Async persistence adapter for immutable traffic label review revisions."""

from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.domain.interfaces import (
    ITrafficLabelReviewRepository,
    RetrainingReviewCandidate,
    RetrainingReviewSummary,
    ReviewNotEligibleError,
    TrafficLabelReview,
)
from web_app.infrastructure.database.database import TrafficLabelReview as ReviewRow
from web_app.infrastructure.database.database import TrafficLog


class TrafficLabelReviewRepository(ITrafficLabelReviewRepository):
    """Create and read review revisions without update/delete operations.

    PostgreSQL serializes revision allocation by locking the parent traffic log
    row before reading the current maximum revision. SQLite's test backend does
    not implement row locks; its unique constraint still protects the invariant
    within the single-session harness.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _to_domain(row: ReviewRow) -> TrafficLabelReview:
        return TrafficLabelReview(
            id=row.id,
            traffic_log_id=row.traffic_log_id,
            revision=row.revision,
            predicted_label=row.predicted_label,
            verified_label=row.verified_label,
            approval_state=row.approval_state,
            reviewer_id=row.reviewer_id,
            reviewer_role=row.reviewer_role,
            reviewed_at=row.reviewed_at,
            model_version=row.model_version,
            prediction_confidence=row.prediction_confidence,
            prediction_confidence_level=row.prediction_confidence_level,
            model_input_hash=row.model_input_hash,
            model_input_text=row.model_input_text,
            preprocessing_version=row.preprocessing_version,
            ingest_event_hash=row.ingest_event_hash,
            source_verification_status=row.source_verification_status,
            source_provenance=row.source_provenance,
            input_hash=row.input_hash,
            review_note=row.review_note,
            created_at=row.created_at,
        )

    async def create_review_revision(
        self,
        *,
        traffic_log_id: int,
        verified_label: str,
        approval_state: str,
        reviewer_id: str,
        reviewer_role: str,
        reviewed_at: datetime,
        review_note: str | None = None,
    ) -> TrafficLabelReview | None:
        # Locking the immutable source alert makes MAX(revision)+1 serial under
        # PostgreSQL READ COMMITTED and keeps the review revision deterministic.
        alert = await self._session.scalar(
            select(TrafficLog).where(TrafficLog.id == traffic_log_id).with_for_update()
        )
        if alert is None:
            return None
        if alert.status not in {"COMPLETED", None}:
            raise ReviewNotEligibleError(
                "Alert processing has not completed", processing=True
            )

        if approval_state == "approved_for_training":
            required_fields = {
                "prediction": alert.prediction,
                "confidence": alert.confidence,
                "confidence_level": alert.confidence_level,
                "model_version": alert.model_version,
                "model_input_hash": alert.model_input_hash,
                "model_input_text": alert.model_input_text,
                "preprocessing_version": alert.preprocessing_version,
            }
            missing = [
                name for name, value in required_fields.items() if value in (None, "")
            ]
            if missing:
                raise ReviewNotEligibleError(
                    f"Missing training provenance: {', '.join(missing)}"
                )

            actual_hash = sha256(alert.model_input_text.encode("utf-8")).hexdigest()
            if actual_hash != alert.model_input_hash:
                raise ReviewNotEligibleError(
                    "Model-input hash does not match stored model-input text"
                )

        current_revision = await self._session.scalar(
            select(func.max(ReviewRow.revision)).where(
                ReviewRow.traffic_log_id == traffic_log_id
            )
        )
        row = ReviewRow(
            traffic_log_id=traffic_log_id,
            revision=int(current_revision or 0) + 1,
            predicted_label=alert.prediction,
            verified_label=verified_label,
            approval_state=approval_state,
            reviewer_id=reviewer_id,
            reviewer_role=reviewer_role,
            reviewed_at=reviewed_at,
            model_version=alert.model_version,
            prediction_confidence=alert.confidence,
            prediction_confidence_level=alert.confidence_level,
            model_input_hash=alert.model_input_hash,
            model_input_text=alert.model_input_text,
            preprocessing_version=alert.preprocessing_version,
            ingest_event_hash=alert.ingest_fingerprint_sha256,
            source_verification_status=alert.source_verification_status,
            source_provenance=alert.source_provenance,
            input_hash=alert.ingest_fingerprint_sha256,
            review_note=review_note,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return self._to_domain(row)

    async def get_latest_review(
        self, traffic_log_id: int
    ) -> TrafficLabelReview | None:
        row = await self._session.scalar(
            select(ReviewRow)
            .where(ReviewRow.traffic_log_id == traffic_log_id)
            .order_by(ReviewRow.revision.desc())
            .limit(1)
        )
        return None if row is None else self._to_domain(row)

    @staticmethod
    def _latest_revision_subquery():
        return (
            select(
                ReviewRow.traffic_log_id.label("traffic_log_id"),
                func.max(ReviewRow.revision).label("latest_revision"),
            )
            .group_by(ReviewRow.traffic_log_id)
            .subquery("latest_review_revision")
        )

    @staticmethod
    def _candidate_from_row(
        review: ReviewRow, source_alert_created_at: datetime | None
    ) -> RetrainingReviewCandidate:
        return RetrainingReviewCandidate(
            review_id=review.id,
            traffic_log_id=review.traffic_log_id,
            revision=review.revision,
            predicted_label=review.predicted_label,
            verified_label=review.verified_label,
            approval_state=review.approval_state,
            reviewer_id=review.reviewer_id,
            reviewer_role=review.reviewer_role,
            reviewed_at=review.reviewed_at,
            model_version=review.model_version,
            prediction_confidence=review.prediction_confidence,
            prediction_confidence_level=review.prediction_confidence_level,
            model_input_hash=review.model_input_hash,
            model_input_text=review.model_input_text,
            preprocessing_version=review.preprocessing_version,
            ingest_event_hash=review.ingest_event_hash,
            source_verification_status=review.source_verification_status,
            source_provenance=review.source_provenance,
            source_alert_created_at=source_alert_created_at,
        )

    async def list_latest_retraining_candidates(
        self, *, limit: int
    ) -> list[RetrainingReviewCandidate]:
        if not 1 <= int(limit) <= 10_000:
            raise ValueError("retraining candidate limit must be between 1 and 10000")
        latest = self._latest_revision_subquery()
        result = await self._session.execute(
            select(ReviewRow, TrafficLog.created_at)
            .join(TrafficLog, TrafficLog.id == ReviewRow.traffic_log_id)
            .join(
                latest,
                (latest.c.traffic_log_id == ReviewRow.traffic_log_id)
                & (latest.c.latest_revision == ReviewRow.revision),
            )
            .order_by(ReviewRow.traffic_log_id.asc(), ReviewRow.revision.asc())
            .limit(int(limit))
        )
        return [
            self._candidate_from_row(review, created_at)
            for review, created_at in result.all()
        ]

    async def get_retraining_review_summary(self) -> RetrainingReviewSummary:
        latest = self._latest_revision_subquery()
        completed_alert = (TrafficLog.status == "COMPLETED") | (
            TrafficLog.status.is_(None)
        )
        result = await self._session.execute(
            select(
                func.count(TrafficLog.id)
                .filter(latest.c.traffic_log_id.is_(None))
                .label("unreviewed"),
                func.count(ReviewRow.id)
                .filter(ReviewRow.approval_state == "approved_for_training")
                .label("approved"),
                func.count(ReviewRow.id)
                .filter(ReviewRow.approval_state == "excluded_from_training")
                .label("excluded"),
            )
            .select_from(TrafficLog)
            .outerjoin(latest, latest.c.traffic_log_id == TrafficLog.id)
            .outerjoin(
                ReviewRow,
                (ReviewRow.traffic_log_id == latest.c.traffic_log_id)
                & (ReviewRow.revision == latest.c.latest_revision),
            )
            .where(completed_alert)
        )
        row = result.one()
        return RetrainingReviewSummary(
            approved=int(row.approved or 0),
            excluded=int(row.excluded or 0),
            unreviewed=int(row.unreviewed or 0),
        )
