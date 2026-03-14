from typing import Literal, Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    """Request schema for prediction endpoint."""
    http_request: str = Field(..., description="HTTP request string to classify")


class PredictionResponse(BaseModel):
    """Response schema for prediction endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "class_label": "SQL Injection",
                "confidence": 0.92,
                "confidence_level": "HIGH",
                "action_taken": "BLOCKED"
            }
        }
    )
    class_label: str = Field(..., description="Predicted class label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    confidence_level: str = Field(..., description="Confidence level (LOW, MEDIUM, HIGH)")
    action_taken: str = Field(..., description="Action taken in response to the prediction")


class FeedbackRequest(BaseModel):
    """Request schema for feedback endpoint."""
    traffic_id: int = Field(..., description="ID of the traffic log to provide feedback for")
    correct_label: str = Field(..., description="The correct classification label")
    analyst_email: str = Field(..., description="Email of the analyst providing feedback")


class AlertResponse(BaseModel):
    """Response schema for alerts endpoint."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: datetime
    source_ip: Optional[str] = None
    http_request: str
    prediction: str
    confidence: float
    confidence_level: str
    action_taken: Optional[str] = None
    analyst_label: Optional[str] = None
    labeled_at: Optional[datetime] = None
    labeled_by: Optional[str] = None


class StatsResponse(BaseModel):
    total_requests: int = Field(default=0, ge=0)
    counts_by_label: dict[str, int] = Field(default_factory=dict)
    avg_inference_latency_ms: float = Field(default=0.0, ge=0.0)


class MLHealthResponse(BaseModel):
    model_version: str
    loaded: bool
    status: Literal["healthy", "degraded"]
    avg_inference_latency_ms: float = Field(default=0.0, ge=0.0)
    total_processed: int = Field(default=0, ge=0)
    drift_detected: bool = False
    confidence_thresholds: dict[str, float] = Field(default_factory=dict)


class AlertDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    source_ip: Optional[str] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    payload_snippet: str
    prediction: str
    confidence: float
    confidence_level: str
    action_taken: Optional[str] = None
    crs_score: Optional[int] = None


class AlertListResponse(BaseModel):
    items: list[AlertDetailResponse] = Field(default_factory=list)
    total: int = Field(default=0, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class HealthResponse(BaseModel):
    """Response schema for health check endpoint."""
    status: str
    database: str
