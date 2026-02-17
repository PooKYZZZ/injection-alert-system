from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone

from web_app.database import get_db, TrafficLog
from web_app.schemas import (
    PredictionRequest,
    PredictionResponse,
    FeedbackRequest,
    AlertResponse,
    StatsResponse,
    BatchPredictionRequest,
    BatchPredictionResponse
)
from web_app.app import model

router = APIRouter()


@router.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest, db: Session = Depends(get_db)):
    """Classify an HTTP request as normal or injection attack."""
    try:
        # Get prediction from model
        result = model.predict(request.http_request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        source_ip=request.source_ip,
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


@router.get("/alerts", response_model=List[AlertResponse])
def get_alerts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get list of traffic alerts with pagination."""
    alerts = db.query(TrafficLog).order_by(
        TrafficLog.timestamp.desc()
    ).offset(skip).limit(limit).all()
    return alerts


@router.get("/stats", response_model=StatsResponse)
def get_stats(db: Session = Depends(get_db)):
    """Get statistics about traffic and predictions."""
    total_requests = db.query(TrafficLog).count()
    attacks_detected = db.query(TrafficLog).filter(
        TrafficLog.prediction != "Normal"
    ).count()
    normal_requests = db.query(TrafficLog).filter(
        TrafficLog.prediction == "Normal"
    ).count()

    # Calculate accuracy metrics
    labeled_count = db.query(TrafficLog).filter(
        TrafficLog.analyst_label.isnot(None)
    ).count()
    accurate_predictions = 0
    if labeled_count > 0:
        accurate_predictions = db.query(TrafficLog).filter(
            TrafficLog.analyst_label.isnot(None),
            TrafficLog.prediction == TrafficLog.analyst_label
        ).count()

    accuracy = round(accurate_predictions / labeled_count, 2) if labeled_count > 0 else 0.0

    return StatsResponse(
        total_requests=total_requests,
        attacks_detected=attacks_detected,
        normal_requests=normal_requests,
        accuracy_metrics={
            "labeled_samples": labeled_count,
            "accurate_predictions": accurate_predictions,
            "accuracy_rate": accuracy
        }
    )


@router.post("/batch-predict", response_model=BatchPredictionResponse)
def batch_predict(request: BatchPredictionRequest, db: Session = Depends(get_db)):
    """Classify multiple HTTP requests as normal or injection attacks."""
    traffic_logs = []
    predictions = []
    for http_request in request.requests:
        try:
            # Get prediction from model
            result = model.predict(http_request)
        except Exception as e:
            continue  # Skip failed predictions, process remaining

        # Determine action based on confidence level
        if result["confidence_level"] == "HIGH" and result["class"] != "Normal":
            action_taken = "BLOCKED"
        elif result["confidence_level"] == "MEDIUM":
            action_taken = "THROTTLED"
        else:
            action_taken = "ALLOWED"

        # Store in database
        traffic_log = TrafficLog(
            http_request=http_request,
            prediction=result["class"],
            confidence=result["confidence"],
            confidence_level=result["confidence_level"],
            action_taken=action_taken
        )
        traffic_logs.append(traffic_log)

        predictions.append(PredictionResponse(
            class_label=result["class"],
            confidence=result["confidence"],
            confidence_level=result["confidence_level"]
        ))

    db.add_all(traffic_logs)
    db.commit()

    return BatchPredictionResponse(predictions=predictions)


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
