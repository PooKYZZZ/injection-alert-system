"""
Application-layer use case for updating alert action_taken.

Architectural role:
  - Validates action values
  - Coordinates with repository to persist action updates
  - Depends on domain interfaces only
"""

from dataclasses import dataclass
from typing import Final, Literal, Optional

from web_app.domain.interfaces import ITrafficLogRepository, TrafficLogEntity

ALERT_ACTION_VALUES: Final[tuple[str, str, str]] = (
    "BLOCKED",
    "THROTTLED",
    "ALLOWED",
)

AlertAction = Literal[*ALERT_ACTION_VALUES]

VALID_ALERT_ACTIONS: Final[frozenset[AlertAction]] = frozenset(ALERT_ACTION_VALUES)


@dataclass(frozen=True)
class UpdateAlertActionResult:
    success: bool
    alert: Optional[TrafficLogEntity] = None
    message: str = ""


class InvalidAlertActionError(ValueError):
    pass


class UpdateAlertActionUseCase:
    def __init__(self, repository: ITrafficLogRepository):
        self._repository = repository

    async def execute(self, alert_id: int, action_taken: str) -> UpdateAlertActionResult:
        if action_taken not in VALID_ALERT_ACTIONS:
            raise InvalidAlertActionError(
                f"Invalid action_taken: {action_taken}. Must be one of: {', '.join(sorted(VALID_ALERT_ACTIONS))}"
            )

        updated = await self._repository.update_action_taken(
            traffic_id=alert_id,
            action_taken=action_taken,
        )

        if updated is None:
            return UpdateAlertActionResult(
                success=False,
                message=f"Alert with ID {alert_id} not found",
            )

        return UpdateAlertActionResult(
            success=True,
            alert=updated,
            message="Action updated successfully",
        )
