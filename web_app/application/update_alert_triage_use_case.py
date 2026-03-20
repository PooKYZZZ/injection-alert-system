"""
web_app/application/update_alert_triage_use_case.py

Application-layer use case for updating alert triage status.

Architectural role:
  - Validates triage status values
  - Coordinates with repository to persist triage updates
  - Depends on domain interfaces only

Dependency rule:
  - Imports from domain/ (interfaces)
  - Does NOT import from infrastructure/ or presentation/
"""

from dataclasses import dataclass
from typing import Literal, Optional

from web_app.domain.interfaces import ITrafficLogRepository, TrafficLogEntity

TriageStatus = Literal[
    'new',
    'in_review',
    'escalated',
    'resolved',
    'false_positive',
]

VALID_TRIAGE_STATUSES = {'new', 'in_review', 'escalated', 'resolved', 'false_positive'}


@dataclass(frozen=True)
class UpdateAlertTriageResult:
    """Value object returned by the update triage use case."""

    success: bool
    alert: Optional[TrafficLogEntity] = None
    message: str = ""


class InvalidTriageStatusError(ValueError):
    """Raised when an invalid triage status is provided."""

    pass


class UpdateAlertTriageUseCase:
    """Coordinates validation and persistence of alert triage status updates."""

    def __init__(self, repository: ITrafficLogRepository):
        self._repository = repository

    async def execute(
        self,
        alert_id: int,
        triage_status: str,
    ) -> UpdateAlertTriageResult:
        """Update the triage status of an alert.

        Args:
            alert_id: The ID of the alert to update
            triage_status: The new triage status value

        Returns:
            UpdateAlertTriageResult indicating success/failure and updated alert

        Raises:
            InvalidTriageStatusError: If the triage status is not valid
        """
        # Validate triage status at application layer
        if triage_status not in VALID_TRIAGE_STATUSES:
            raise InvalidTriageStatusError(
                f"Invalid triage_status: {triage_status}. "
                f"Must be one of: {', '.join(sorted(VALID_TRIAGE_STATUSES))}"
            )

        # Update via repository
        updated = await self._repository.update_triage_status(
            traffic_id=alert_id,
            triage_status=triage_status,
        )

        if updated is None:
            return UpdateAlertTriageResult(
                success=False,
                message=f"Alert with ID {alert_id} not found",
            )

        return UpdateAlertTriageResult(
            success=True,
            alert=updated,
            message="Triage status updated successfully",
        )
