from typing import Literal, Optional
from datetime import datetime, timezone
from typing import List

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer

from web_app.application.update_alert_action_use_case import AlertAction

PredictionLabel = Literal[
    "SQL Injection",
    "Code Injection",
    "Other Attacks",
    "Normal",
]
ConfidenceLevel = Literal["LOW", "MEDIUM", "HIGH"]
ActionTaken = AlertAction
TriageStatus = Literal["new", "in_review", "escalated", "resolved", "false_positive"]


class PredictionRequest(BaseModel):
    """Request schema for prediction endpoint."""

    http_request: str = Field(
        ...,
        min_length=1,
        max_length=65536,
        description="HTTP request string to classify",
    )


class PredictionResponse(BaseModel):
    """Response schema for prediction endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "class_label": "SQL Injection",
                "confidence": 0.92,
                "confidence_level": "HIGH",
                "action_taken": "BLOCKED",
            }
        }
    )
    class_label: PredictionLabel = Field(..., description="Predicted class label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    confidence_level: ConfidenceLevel = Field(
        ..., description="Confidence level (LOW, MEDIUM, HIGH)"
    )
    action_taken: ActionTaken = Field(
        ..., description="Action taken in response to the prediction"
    )


class TriageIngestRequest(BaseModel):
    transaction_id: str = Field(..., min_length=1)
    timestamp: datetime
    source_ip: str = Field(..., min_length=1)
    request_method: str = Field(..., min_length=1)
    request_uri: str = Field(..., min_length=1)
    request_headers: dict[str, str]
    request_body: str
    http_request: str = Field(..., min_length=1)
    crs_score: int
    crs_rule_ids: list[str]


class TriageIngestResponse(BaseModel):
    alert_id: int = Field(..., ge=1)
    prediction: PredictionLabel
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_level: ConfidenceLevel
    action_taken: ActionTaken
    model_version: str | None = None


class FeedbackRequest(BaseModel):
    """Request schema for feedback endpoint."""

    traffic_id: int = Field(
        ..., description="ID of the traffic log to provide feedback for"
    )
    correct_label: str = Field(
        ..., max_length=100, description="The correct classification label"
    )
    analyst_email: EmailStr = Field(
        ..., description="Email of the analyst providing feedback"
    )


class AlertResponse(BaseModel):
    """Response schema for alerts endpoint."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: datetime
    source_ip: Optional[str] = None
    http_request: str
    prediction: PredictionLabel
    confidence: float
    confidence_level: ConfidenceLevel
    action_taken: Optional[ActionTaken] = None
    analyst_label: Optional[str] = None
    labeled_at: Optional[datetime] = None
    labeled_by: Optional[str] = None


class ActivityBucketSchema(BaseModel):
    """Schema for activity bucket data in stats response."""

    bucket_index: int = Field(
        default=0, ge=0, description="Bucket index (0-23 for 24-hour period)"
    )
    total_count: int = Field(
        default=0, ge=0, description="Total requests in this bucket"
    )
    blocked_count: int = Field(
        default=0, ge=0, description="Blocked requests in this bucket"
    )
    allowed_count: int = Field(
        default=0, ge=0, description="Allowed requests in this bucket"
    )
    throttled_count: int = Field(
        default=0, ge=0, description="Throttled requests in this bucket"
    )
    timestamp_start: datetime = Field(description="Start of this bucket's time window")
    timestamp_end: Optional[datetime] = Field(
        default=None, description="End of this bucket's time window"
    )
    bucket_width_seconds: Optional[int] = Field(
        default=None, ge=1, description="Bucket width in seconds"
    )


class StatsQueryParameters(BaseModel):
    """Query parameters for stats endpoints."""

    window: Optional[Literal["1h", "6h", "24h", "7d"]] = Field(
        default=None, description="Time window for stats"
    )
    timezone: Optional[str] = Field(
        default=None, description="IANA timezone used for bucket boundaries"
    )


class SourceIPSummarySchema(BaseModel):
    """Schema for source IP summary in stats response."""

    ip: str
    count: int = Field(default=0, ge=0)
    action: Optional[str] = Field(
        default=None, description="Most recent action taken for this IP"
    )


class TargetPathSummarySchema(BaseModel):
    """Schema for targeted path summary in stats response."""

    path: str
    hits: int = Field(default=0, ge=0)


class StatsResponse(BaseModel):
    total_requests: int = Field(default=0, ge=0)
    counts_by_label: dict[str, int] = Field(default_factory=dict)
    avg_inference_latency_ms: float = Field(default=0.0, ge=0.0)
    blocked_count: int = Field(default=0, ge=0)
    allowed_count: int = Field(default=0, ge=0)
    throttled_count: int = Field(default=0, ge=0)
    avg_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    false_positive_rate: float = Field(default=0.0, ge=0.0)
    false_positive_count: int = Field(default=0, ge=0)
    high_alert_count: int = Field(default=0, ge=0)
    prev_high_alert_count: Optional[int] = Field(default=None, ge=0)
    prev_total_requests: Optional[int] = Field(default=None, ge=0)
    prev_blocked_count: Optional[int] = Field(default=None, ge=0)
    prev_allowed_count: Optional[int] = Field(default=None, ge=0)
    prev_throttled_count: Optional[int] = Field(default=None, ge=0)
    activity_buckets: List[ActivityBucketSchema] = Field(
        default_factory=list,
        description="Bucketed activity counts for hero activity strip",
    )
    attack_distribution: dict[str, int] = Field(
        default_factory=dict, description="Distribution of attacks by type"
    )
    top_source_ips: List[SourceIPSummarySchema] = Field(
        default_factory=list, description="Top source IPs by request count"
    )
    top_targeted_paths: List[TargetPathSummarySchema] = Field(
        default_factory=list, description="Top targeted paths by hit count"
    )


class CalibrationBin(BaseModel):
    """Schema for calibration bin data in ML health response."""

    bin_idx: int = Field(description="Bin index")
    bin_center: float = Field(description="Mean confidence (bin center)")
    accuracy: float = Field(description="Empirical accuracy")
    confidence: float = Field(description="Average confidence in this bin")
    count: int = Field(description="Number of samples in this bin")


class MLHealthResponse(BaseModel):
    model_version: str
    loaded: bool
    status: Literal["healthy", "degraded"]
    avg_inference_latency_ms: float = Field(default=0.0, ge=0.0)
    total_processed: int = Field(default=0, ge=0)
    drift_detected: bool = False
    drift_score: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Drift score 0-1 indicating severity"
    )
    confidence_thresholds: dict[str, float] = Field(default_factory=dict)
    # Optional eval metadata fields - populated when eval artifacts exist
    macro_f1: Optional[float] = Field(
        default=None, description="Macro F1 score from eval"
    )
    ece: Optional[float] = Field(default=None, description="Expected Calibration Error")
    per_class_f1: dict[str, float] = Field(
        default_factory=dict, description="Per-class F1 scores"
    )
    calibration_bins: List[CalibrationBin] = Field(
        default_factory=list, description="Calibration bins for reliability diagram"
    )
    prediction_distribution: dict[str, int] = Field(
        default_factory=dict, description="Prediction distribution from eval"
    )


class AlertDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    source_ip: Optional[str] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    payload_snippet: str
    prediction: PredictionLabel
    confidence: float
    confidence_level: ConfidenceLevel
    action_taken: Optional[ActionTaken] = None
    crs_score: Optional[int] = None
    crs_rule_ids: Optional[list[str]] = None
    analyst_label: Optional[str] = None
    labeled_at: Optional[datetime] = None
    labeled_by: Optional[str] = None
    triage_status: Optional[TriageStatus] = None

    @field_serializer("labeled_at", when_used="json")
    def serialize_labeled_at(self, value: Optional[datetime]) -> Optional[str]:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        else:
            value = value.astimezone(timezone.utc)
        return value.isoformat().replace("+00:00", "Z")


class AlertListResponse(BaseModel):
    items: list[AlertDetailResponse] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class TriageUpdateRequest(BaseModel):
    """Request schema for updating alert triage status."""

    triage_status: Literal[
        "new",
        "in_review",
        "escalated",
        "resolved",
        "false_positive",
    ] = Field(..., description="Triage status to set on the alert")


class ActionUpdateRequest(BaseModel):
    """Request schema for updating alert action_taken."""

    action_taken: ActionTaken = Field(..., description="Action to set on the alert")


class WafIngestLookupResponse(BaseModel):
    found: bool
    transaction_id: str
    alert_id: int | None = None
    status: str | None = None
    prediction: str | None = None
    confidence: float | None = None
    confidence_level: ConfidenceLevel | None = None
    action_taken: ActionTaken | None = None
    ingest_source: str | None = None
    crs_score: int | None = None
    crs_rule_ids: list[str] | None = None
    matched_rule_messages: list[str] | None = None
    matched_rule_tags: list[str] | None = None
    timestamp: datetime | None = None


class HealthResponse(BaseModel):
    """Response schema for health check endpoint."""

    status: str
    database: str


class AlertQueryParams(BaseModel):
    """Query parameters for GET /alerts endpoint.

    Uses extra="forbid" to reject unknown query parameters.
    """

    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    severity: Optional[Literal["ALL", "LOW", "MEDIUM", "HIGH"]] = Field(
        default=None, description="Filter by confidence level severity"
    )
    time_range: Optional[Literal["1h", "6h", "24h", "7d"]] = Field(
        default=None, description="Time window filter"
    )
    search: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Search in source IP, path, method, payload",
    )
    action: Optional[ActionTaken] = Field(
        default=None, description="Filter by action taken (BLOCKED, THROTTLED, ALLOWED)"
    )
    triage_status: Optional[TriageStatus] = Field(
        default=None,
        description="Filter by triage status; 'new' maps to untriaged rows (NULL in DB)",
    )
    confidence_level: Optional[List[ConfidenceLevel]] = Field(
        default=None,
        description="Filter by confidence levels (multiple values supported)",
    )
    prediction: Optional[PredictionLabel] = Field(
        default=None, description="Filter by prediction label"
    )
    source_ip: Optional[str] = Field(
        default=None, description="Filter by exact source IP"
    )
    sort_by: Optional[Literal["timestamp", "confidence", "severity", "action"]] = Field(
        default="timestamp", description="Sort field"
    )
    sort_dir: Optional[Literal["asc", "desc"]] = Field(
        default="desc", description="Sort direction"
    )
