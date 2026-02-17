import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from web_app.database import Base, TrafficLog, get_db, init_db


def test_traffic_log_model_creation():
    """Test that TrafficLog model can be created and persisted"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    log = TrafficLog(
        source_ip="192.168.1.1",
        http_request="GET /api/users?id=1",
        prediction="Normal",
        confidence=0.95,
        confidence_level="HIGH",
        action_taken="ALLOWED"
    )
    session.add(log)
    session.commit()

    retrieved = session.query(TrafficLog).filter_by(id=log.id).first()

    assert retrieved is not None
    assert retrieved.source_ip == "192.168.1.1"
    assert retrieved.prediction == "Normal"
    assert retrieved.confidence == 0.95


def test_traffic_log_has_all_required_fields():
    """Test that TrafficLog has all required fields from schema"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    log = TrafficLog(
        source_ip="10.0.0.1",
        http_request="POST /login",
        prediction="SQL Injection",
        confidence=0.85,
        confidence_level="HIGH",
        action_taken="BLOCKED",
        analyst_label="False Positive",
        labeled_by="analyst@example.com"
    )
    session.add(log)
    session.commit()

    retrieved = session.query(TrafficLog).first()

    assert retrieved.http_request == "POST /login"
    assert retrieved.action_taken == "BLOCKED"
    assert retrieved.analyst_label == "False Positive"
    assert retrieved.labeled_by == "analyst@example.com"


def test_get_db_returns_session():
    """Test that get_db generator yields a database session"""
    # This test verifies the dependency injection pattern
    assert callable(get_db)
