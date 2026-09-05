"""Application service for authenticated, append-only verified label reviews."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from web_app.domain.authorization import Permission, role_has_permission
from web_app.domain.interfaces import ITrafficLabelReviewRepository, TrafficLabelReview

CANONICAL_LABELS = frozenset(
    {"Normal", "SQL Injection", "Code Injection", "Other Attacks"}
)
REVIEW_ACTION_STATES = frozenset({"approved_for_training", "excluded_from_training"})
@dataclass(frozen=True)
class ReviewerContext:
    reviewer_id: str
    reviewer_role: str


@dataclass(frozen=True)
class LabelReviewResult:
    review: TrafficLabelReview


class InvalidLabelReviewError(ValueError):
    """Raised when a label review violates its application contract."""


class UnauthorizedLabelReviewerError(InvalidLabelReviewError, PermissionError):
    """Raised when the authenticated reviewer cannot submit reviews."""


class LabelReviewUseCase:
    def __init__(self, repository: ITrafficLabelReviewRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        *,
        alert_id: int,
        verified_label: str,
        approval_state: str,
        reviewer: ReviewerContext,
        review_note: str | None = None,
    ) -> LabelReviewResult | None:
        if verified_label not in CANONICAL_LABELS:
            raise InvalidLabelReviewError("verified_label is not canonical")
        if approval_state not in REVIEW_ACTION_STATES:
            raise InvalidLabelReviewError("approval_state is not a review action")
        if not reviewer.reviewer_id or len(reviewer.reviewer_id) > 128:
            raise InvalidLabelReviewError("reviewer identity is invalid")
        if not role_has_permission(reviewer.reviewer_role, Permission.ALERTS_TRIAGE):
            raise UnauthorizedLabelReviewerError("reviewer role is not authorized")
        if review_note is not None and len(review_note) > 1000:
            raise InvalidLabelReviewError("review note is too long")

        review = await self._repository.create_review_revision(
            traffic_log_id=alert_id,
            verified_label=verified_label,
            approval_state=approval_state,
            reviewer_id=reviewer.reviewer_id,
            reviewer_role=reviewer.reviewer_role,
            reviewed_at=datetime.now(timezone.utc),
            review_note=review_note,
        )
        return None if review is None else LabelReviewResult(review=review)
