from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


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
