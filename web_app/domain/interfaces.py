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
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TrafficLogEntity:
    """Domain entity representing a traffic log record.

    This is a framework-agnostic domain object. It does NOT correspond
    1:1 to an ORM model — the repository is responsible for mapping.
    """

    id: Optional[int] = None
    transaction_id: Optional[str] = None
    created_at: Optional[datetime] = None
    timestamp: Optional[datetime] = None
    source_ip: Optional[str] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    http_request: str = ""
    crs_score: Optional[int] = None
    crs_rule_ids: Optional[list[str]] = None
    prediction: Optional[str] = None
    confidence: Optional[float] = None
    confidence_level: Optional[str] = None
    inference_latency_ms: Optional[float] = None
    model_version: Optional[str] = None
    status: Optional[str] = None
    action_taken: Optional[str] = None
    analyst_label: Optional[str] = None
    labeled_at: Optional[datetime] = None
    labeled_by: Optional[str] = None

    @property
    def payload_snippet(self) -> str:
        if not self.http_request:
            return ""
        return self.http_request[:250]


@dataclass
class TrafficStatsSummary:
    total_requests: int = 0
    counts_by_label: dict[str, int] = field(default_factory=dict)
    avg_inference_latency_ms: float = 0.0


@dataclass
class TrafficLogPage:
    items: List[TrafficLogEntity] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


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
    async def save_if_absent(
        self,
        entity: TrafficLogEntity,
    ) -> tuple[TrafficLogEntity, bool]:
        """Insert once by transaction_id or return the existing entity."""
        ...

    @abstractmethod
    async def claim_processing(self, entity: TrafficLogEntity) -> bool:
        """Reserve a transaction_id with a PROCESSING placeholder row."""
        ...

    @abstractmethod
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
        """Complete a claimed placeholder row after inference succeeds."""
        ...

    @abstractmethod
    async def get_by_id(self, traffic_id: int) -> Optional[TrafficLogEntity]:
        """Retrieve a single traffic log by its ID."""
        ...

    @abstractmethod
    async def get_by_transaction_id(
        self,
        transaction_id: str,
    ) -> Optional[TrafficLogEntity]:
        """Retrieve a single traffic log by its transaction ID."""
        ...

    @abstractmethod
    async def get_stats_summary(self) -> TrafficStatsSummary:
        """Return aggregate traffic stats with zero-safe defaults."""
        ...

    @abstractmethod
    async def get_alert_list(
        self,
        page: int,
        page_size: int,
        severity: Optional[str] = None,
        time_range: Optional[str] = None,
        search: Optional[str] = None,
    ) -> TrafficLogPage:
        """Return a filtered, paginated alert list."""
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
