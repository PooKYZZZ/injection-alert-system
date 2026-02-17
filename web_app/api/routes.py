from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from web_app.database import get_db, TrafficLog
from web_app.schemas import (
    PredictionRequest,
    PredictionResponse,
    FeedbackRequest,
    AlertResponse
)
from ml_model.models.mock_model import MockInjectionClassifier

router = APIRouter()
model = MockInjectionClassifier()


@router.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest, db: Session = Depends(get_db)):
    """Classify an HTTP request as normal or injection attack."""
    # Get prediction from model
    result = model.predict(request.http_request)

    # Determine action based on confidence level
    if result["confidence_level"] == "HIGH" and result["class"] != "Normal":
        action_taken = "BLOCKED"
    elif result["confidence_level"] == "MEDIUM":
        action_taken = "THROTTLED"
    else:
        action_taken = "ALLOWED"

    # Store in database
    traffic_log = TrafficLog(
        http_request=request.http_request,
        prediction=result["class"],
        confidence=result["confidence"],
        confidence_level=result["confidence_level"],
        action_taken=action_taken
    )
    db.add(traffic_log)
    db.commit()
    db.refresh(traffic_log)

    return PredictionResponse(
        class_label=result["class"],
        confidence=result["confidence"],
        confidence_level=result["confidence_level"]
    )


@router.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "database": "connected"}


@router.get("/alerts", response_model=List[AlertResponse])
def get_alerts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get list of traffic alerts with pagination."""
    alerts = db.query(TrafficLog).order_by(
        TrafficLog.timestamp.desc()
    ).offset(skip).limit(limit).all()
    return alerts


@router.post("/feedback")
def submit_feedback(feedback: FeedbackRequest, db: Session = Depends(get_db)):
    """Store analyst feedback/correction for a prediction."""
    traffic_log = db.query(TrafficLog).filter(
        TrafficLog.id == feedback.traffic_id
    ).first()

    if not traffic_log:
        raise HTTPException(status_code=404, detail="Traffic log not found")

    traffic_log.analyst_label = feedback.correct_label
    traffic_log.labeled_by = feedback.analyst_email
    traffic_log.labeled_at = datetime.now(timezone.utc)
    db.commit()

    return {"message": "Feedback recorded successfully", "traffic_id": feedback.traffic_id}
