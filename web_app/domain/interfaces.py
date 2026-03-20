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
class DriftMetrics:
    """Domain object representing ML model drift detection metrics.
    
    drift_score is None when drift cannot be computed (insufficient data).
    drift_detected is False when drift_score is None.
    """

    drift_score: float | None  # 0.0-1.0 indicating severity, None if unavailable
    drift_detected: bool  # True if drift exceeds threshold, False if not or if unavailable
    recent_mean_confidence: float | None  # Mean confidence of recent window, None if unavailable
    baseline_mean_confidence: float  # Mean confidence of baseline
    recent_sample_size: int  # Number of records in recent window
    baseline_sample_size: int  # Number of records in baseline


@dataclass
class ActivityBucket:
    """Domain object representing activity count in a time bucket."""

    bucket_index: int  # 0-23 for 24-hour period
    total_count: int  # Total requests in this bucket
    blocked_count: int  # Blocked requests in this bucket
    timestamp_start: datetime  # Start of this bucket's time window


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
    triage_status: Optional[str] = None

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
    blocked_count: int = 0
    allowed_count: int = 0
    avg_confidence: Optional[float] = None


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
    async def get_drift_metrics(self, recent_window: int = 100) -> "DriftMetrics":
        """Compute drift metrics by comparing recent confidence to baseline.

        Args:
            recent_window: Number of recent records to compare (default 100)

        Returns:
            DriftMetrics with drift_score, drift_detected, and confidence values.
        """
        ...

    @abstractmethod
    async def get_activity_buckets(
        self, hours: int = 24, buckets: int = 24
    ) -> List["ActivityBucket"]:
        """Get bucketed activity counts for the hero activity strip.

        Args:
            hours: Number of hours to look back (default 24)
            buckets: Number of buckets to divide the time into (default 24)

        Returns:
            List of ActivityBucket with bucket_index, total_count, and blocked_count.
        """
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

    @abstractmethod
    async def update_triage_status(
        self,
        traffic_id: int,
        triage_status: str,
    ) -> Optional[TrafficLogEntity]:
        """Update triage status on a traffic log. Returns None if not found."""
        ...
