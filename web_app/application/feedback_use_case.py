"""
web_app/application/feedback_use_case.py

Application-layer use case for recording analyst feedback.

Architectural role:
  - Orchestrates the feedback recording workflow
  - Depends on domain interfaces (ITrafficLogRepository) only

Dependency rule:
  - Imports from domain/ (entities, interfaces)
  - Does NOT import from infrastructure/ or presentation/
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from web_app.domain.interfaces import ITrafficLogRepository


@dataclass
class FeedbackResult:
    """Value object returned after feedback is recorded."""

    success: bool
    traffic_id: int
    message: str


class FeedbackUseCase:
    """Records analyst corrections on traffic log predictions.

    This use case ensures that feedback is persisted through the
    repository interface without leaking ORM details to the caller.
    """

    def __init__(self, repository: ITrafficLogRepository):
        self._repository = repository

    async def execute(
        self,
        traffic_id: int,
        correct_label: str,
        analyst_email: str,
    ) -> FeedbackResult:
        """Record analyst feedback for a traffic log entry."""
        updated = await self._repository.update_feedback(
            traffic_id=traffic_id,
            analyst_label=correct_label,
            analyst_email=analyst_email,
            labeled_at=datetime.now(timezone.utc),
        )

        if updated is None:
            return FeedbackResult(
                success=False,
                traffic_id=traffic_id,
                message="Traffic log not found",
            )

        return FeedbackResult(
            success=True,
            traffic_id=traffic_id,
            message="Feedback recorded successfully",
        )
