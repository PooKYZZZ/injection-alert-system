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

from web_app.domain.source_address import (
    SourceProvenance,
    SourceVerificationStatus,
)


@dataclass
class DriftMetrics:
    """Domain object representing ML model drift detection metrics.

    drift_score is None when drift cannot be computed (insufficient data).
    drift_detected is False when drift_score is None.
    """

    drift_score: float | None  # 0.0-1.0 indicating severity, None if unavailable
    drift_detected: (
        bool  # True if drift exceeds threshold, False if not or if unavailable
    )
    recent_mean_confidence: (
        float | None
    )  # Mean confidence of recent window, None if unavailable
    baseline_mean_confidence: float  # Mean confidence of baseline
    recent_sample_size: int  # Number of records in recent window
    baseline_sample_size: int  # Number of records in baseline


@dataclass
class ActivityBucket:
    """Domain object representing activity count in a time bucket."""

    bucket_index: int  # 0-23 for 24-hour period
    total_count: int  # Total requests in this bucket
    blocked_count: int  # Blocked requests in this bucket
    allowed_count: int  # Allowed requests in this bucket
    throttled_count: int  # Throttled requests in this bucket
    timestamp_start: datetime  # Start of this bucket's time window
    timestamp_end: Optional[datetime] = None  # End of this bucket's time window
    bucket_width_seconds: Optional[int] = None  # Width of bucket in seconds


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
    # Backward-compatible conservative defaults for domain callers that omit
    # source metadata; they never imply verified trust. The ORM/database still
    # require non-null persisted values.
    source_provenance: SourceProvenance = SourceProvenance.DIRECT_REMOTE_ADDR
    source_verification_status: SourceVerificationStatus = (
        SourceVerificationStatus.UNVERIFIED
    )
    ingest_fingerprint_sha256: Optional[str] = None
    model_input_hash: Optional[str] = None
    model_input_text: Optional[str] = None
    preprocessing_version: Optional[str] = None
    request_path: Optional[str] = None
    query_string: Optional[str] = None
    request_method: Optional[str] = None
    http_request: str = ""
    crs_score: Optional[int] = None
    crs_rule_ids: Optional[list[str]] = None
    ingest_source: Optional[str] = None
    matched_rule_messages: Optional[list[str]] = None
    matched_rule_tags: Optional[list[str]] = None
    prediction: Optional[str] = None
    confidence: Optional[float] = None
    confidence_level: Optional[str] = None
    inference_latency_ms: Optional[float] = None
    model_version: Optional[str] = None
    status: Optional[str] = None
    lease_expires_at: Optional[datetime] = None
    processing_owner_token: Optional[str] = None
    processing_attempt: Optional[int] = None
    action_taken: Optional[str] = None
    analyst_label: Optional[str] = None
    labeled_at: Optional[datetime] = None
    labeled_by: Optional[str] = None
    triage_status: Optional[str] = None
    label_review: Optional["TrafficLabelReview"] = None

    @property
    def payload_snippet(self) -> str:
        if not self.http_request:
            return ""
        return self.http_request[:250]


@dataclass
class SourceIPSummary:
    """Domain object representing a source IP with request count and most recent action."""

    ip: str
    count: int
    action: Optional[str] = None


@dataclass
class TargetPathSummary:
    """Domain object representing a targeted path with hit count."""

    path: str
    hits: int


@dataclass
class TrafficStatsSummary:
    total_requests: int = 0
    counts_by_label: dict[str, int] = field(default_factory=dict)
    counts_by_confidence_tier: dict[str, int] = field(default_factory=dict)
    non_normal_counts_by_confidence_tier: dict[str, int] = field(default_factory=dict)
    avg_inference_latency_ms: float = 0.0
    blocked_count: int = 0
    allowed_count: int = 0
    throttled_count: int = 0
    avg_confidence: Optional[float] = None
    false_positive_rate: float = 0.0
    false_positive_count: int = 0
    high_alert_count: int = 0
    prev_high_alert_count: Optional[int] = None
    prev_total_requests: Optional[int] = None
    prev_blocked_count: Optional[int] = None
    prev_allowed_count: Optional[int] = None
    prev_throttled_count: Optional[int] = None
    attack_distribution: dict[str, int] = field(default_factory=dict)
    top_source_ips: List[SourceIPSummary] = field(default_factory=list)
    top_targeted_paths: List[TargetPathSummary] = field(default_factory=list)


@dataclass
class TrafficLogPage:
    items: List[TrafficLogEntity] = field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20


@dataclass
class TrafficLabelReview:
    id: Optional[int]
    traffic_log_id: int
    revision: int
    predicted_label: Optional[str]
    verified_label: str
    approval_state: str
    reviewer_id: str
    reviewer_role: str
    reviewed_at: datetime
    model_version: Optional[str]
    prediction_confidence: Optional[float] = None
    prediction_confidence_level: Optional[str] = None
    model_input_hash: Optional[str] = None
    model_input_text: Optional[str] = None
    preprocessing_version: Optional[str] = None
    ingest_event_hash: Optional[str] = None
    source_verification_status: Optional[str] = None
    source_provenance: Optional[str] = None
    input_hash: Optional[str] = None
    review_note: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass(frozen=True)
class RetrainingReviewCandidate:
    """Snapshot of one latest review and its non-sensitive source metadata.

    The repository deliberately does not select ``TrafficLog.http_request``.
    ``model_input_text`` is the already-redacted model-input contract captured
    by the review revision and is written only to a local run artifact.
    """

    review_id: Optional[int]
    traffic_log_id: int
    revision: int
    predicted_label: Optional[str]
    verified_label: str
    approval_state: str
    reviewer_id: str
    reviewer_role: str
    reviewed_at: datetime
    model_version: Optional[str]
    prediction_confidence: Optional[float]
    prediction_confidence_level: Optional[str]
    model_input_hash: Optional[str]
    model_input_text: Optional[str]
    preprocessing_version: Optional[str]
    ingest_event_hash: Optional[str]
    source_verification_status: Optional[str]
    source_provenance: Optional[str]
    source_alert_created_at: Optional[datetime] = None

    @property
    def sample_id(self) -> str:
        return f"traffic-{self.traffic_log_id}-review-{self.revision}"

    @property
    def source_family(self) -> str:
        return str(self.source_provenance or "UNKNOWN")


@dataclass(frozen=True)
class RetrainingReviewSummary:
    """Bounded review-state counts used to detect query truncation."""

    approved: int = 0
    excluded: int = 0
    unreviewed: int = 0
    invalid: int = 0
    duplicate: int = 0

    @property
    def reviewed(self) -> int:
        return self.approved + self.excluded


class ReviewNotEligibleError(ValueError):
    """Alert cannot receive the requested verified-label review action."""

    def __init__(self, message: str, *, processing: bool = False) -> None:
        super().__init__(message)
        self.processing = processing


class ITrafficLabelReviewRepository(ABC):
    """Persistence contract for append-only verified label reviews."""

    @abstractmethod
    async def create_review_revision(
        self,
        *,
        traffic_log_id: int,
        verified_label: str,
        approval_state: str,
        reviewer_id: str,
        reviewer_role: str,
        reviewed_at: datetime,
        review_note: Optional[str] = None,
    ) -> Optional[TrafficLabelReview]:
        """Create the next revision, or return None when the alert is unknown."""
        ...

    @abstractmethod
    async def get_latest_review(
        self, traffic_log_id: int
    ) -> Optional[TrafficLabelReview]:
        """Return only the highest revision for an alert."""
        ...

    @abstractmethod
    async def list_latest_retraining_candidates(
        self, *, limit: int
    ) -> list[RetrainingReviewCandidate]:
        """Return a bounded, deterministic latest-review export projection."""
        ...

    @abstractmethod
    async def get_retraining_review_summary(self) -> RetrainingReviewSummary:
        """Return review-state counts without selecting raw request payloads."""
        ...


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
    async def claim_or_reclaim_processing(
        self,
        entity: TrafficLogEntity,
        *,
        owner_token: str,
        lease_expires_at: datetime,
        now: datetime,
    ) -> TrafficLogEntity | None:
        """Claim a new PROCESSING row or reclaim a stale one atomically.

        Returns the authoritative row when the claim or reclaim succeeds.
        Returns None when another live owner still holds the reservation.
        """
        ...

    @abstractmethod
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
        action_taken: Optional[str],
    ) -> tuple[TrafficLogEntity, bool]:
        """Return the authoritative row and whether this owner completed it."""
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
    async def get_stats_summary(
        self, window: Optional[str] = None, reference_time: Optional[datetime] = None
    ) -> TrafficStatsSummary:
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
        self,
        window: Optional[str] = None,
        buckets: int = 24,
        reference_time: Optional[datetime] = None,
    ) -> List["ActivityBucket"]:
        """Get bucketed activity counts for the hero activity strip.

        Args:
            window: Optional time window filter (1h, 6h, 24h, 7d). Defaults to 24h.
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
        confidence_tier_filter: Optional[str] = None,
        time_range: Optional[str] = None,
        search: Optional[str] = None,
        action: Optional[str] = None,
        triage_status: Optional[str] = None,
        confidence_levels: Optional[List[str]] = None,
        prediction: Optional[str] = None,
        source_ip: Optional[str] = None,
        sort_by: Optional[str] = "timestamp",
        sort_dir: Optional[str] = "desc",
        reference_time: Optional[datetime] = None,
    ) -> TrafficLogPage:
        """Return a filtered, paginated alert list.

        ``reference_time`` is an optional UTC instant used by deterministic
        callers to evaluate rolling windows. Live callers may omit it.
        """
        ...

    @abstractmethod
    async def list_recent(
        self, skip: int = 0, limit: int = 100
    ) -> List[TrafficLogEntity]:
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

    @abstractmethod
    async def update_action_taken(
        self,
        traffic_id: int,
        action_taken: str,
    ) -> Optional[TrafficLogEntity]:
        """Update action_taken on a traffic log. Returns None if not found."""
        ...
