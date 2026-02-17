from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime


class PredictionRequest(BaseModel):
    """Request schema for prediction endpoint."""
    http_request: str = Field(..., max_length=10000, description="HTTP request string to classify")
    source_ip: Optional[str] = Field(None, description="Source IP address of the request")


class PredictionResponse(BaseModel):
    """Response schema for prediction endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "class_label": "SQL Injection",
                "confidence": 0.92,
                "confidence_level": "HIGH"
            }
        }
    )
    class_label: str = Field(..., description="Predicted class label")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    confidence_level: str = Field(..., description="Confidence level (LOW, MEDIUM, HIGH)")


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


class HealthResponse(BaseModel):
    """Response schema for health check endpoint."""
    status: str
    database: str


class StatsResponse(BaseModel):
    """Response schema for statistics endpoint."""
    total_requests: int = Field(..., description="Total number of requests processed")
    attacks_detected: int = Field(..., description="Number of injection attacks detected")
    normal_requests: int = Field(..., description="Number of normal requests")
    accuracy_metrics: dict = Field(..., description="Accuracy and performance metrics")


class BatchPredictionRequest(BaseModel):
    """Request schema for batch prediction endpoint."""
    requests: List[str] = Field(..., max_length=50, description="Max 50 requests per batch")

    @field_validator('requests')
    @classmethod
    def validate_items(cls, v):
        if any(len(r) > 10000 for r in v):
            raise ValueError('Each request must be max 10000 characters')
        return v


class BatchPredictionResponse(BaseModel):
    """Response schema for batch prediction endpoint."""
    predictions: List[PredictionResponse] = Field(..., description="List of predictions")
