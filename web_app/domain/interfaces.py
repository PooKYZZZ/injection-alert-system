"""
web_app/domain/interfaces.py

Domain-layer abstractions (repository interfaces).

Architectural role:
  - Defines the contract for persistence operations
  - Inner layer — no dependencies on frameworks, ORM, or infrastructure
  - Application use cases depend on these interfaces
  - Infrastructure repositories implement them

Dependency rule:
  - Imports from NOTHING inside this project (pure abstractions)
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TrafficLogEntity:
    """Domain entity representing a traffic log record.

    This is a framework-agnostic domain object. It does NOT correspond
    1:1 to an ORM model — the repository is responsible for mapping.
    """

    id: Optional[int] = None
    timestamp: Optional[datetime] = None
    source_ip: Optional[str] = None
    http_request: str = ""
    prediction: str = ""
    confidence: float = 0.0
    confidence_level: str = "LOW"
    model_version: Optional[str] = None
    action_taken: Optional[str] = None
    analyst_label: Optional[str] = None
    labeled_at: Optional[datetime] = None
    labeled_by: Optional[str] = None


class ITrafficLogRepository(ABC):
    """Repository interface for traffic log persistence.

    Concrete implementations live in infrastructure/repositories/.
    Application use cases depend on this interface only.
    """

    @abstractmethod
    async def save(self, entity: TrafficLogEntity) -> TrafficLogEntity:
        """Persist a traffic log entity and return it with its assigned ID."""
        ...

    @abstractmethod
    async def get_by_id(self, traffic_id: int) -> Optional[TrafficLogEntity]:
        """Retrieve a single traffic log by its ID."""
        ...

    @abstractmethod
    async def list_recent(self, skip: int = 0, limit: int = 100) -> List[TrafficLogEntity]:
        """Retrieve recent traffic logs ordered by timestamp descending."""
        ...

    @abstractmethod
    async def update_feedback(
        self,
        traffic_id: int,
        analyst_label: str,
        analyst_email: str,
        labeled_at: datetime,
    ) -> Optional[TrafficLogEntity]:
        """Update analyst feedback on a traffic log. Returns None if not found."""
        ...
