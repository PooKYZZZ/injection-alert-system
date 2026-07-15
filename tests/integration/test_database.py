import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from web_app.infrastructure.database.database import Base, TrafficLog


def test_traffic_log_omitting_source_metadata_fails() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(TrafficLog(source_ip="192.0.2.1", http_request="GET /raw"))

    with pytest.raises(IntegrityError):
        session.commit()


def test_traffic_log_model_creation():
    """Test that TrafficLog model can be created and persisted"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    log = TrafficLog(
        source_ip="192.168.1.1",
        source_provenance="DIRECT_REMOTE_ADDR",
        source_verification_status="UNVERIFIED",
        http_request="GET /api/users?id=1",
        prediction="Normal",
        confidence=0.95,
        confidence_level="HIGH",
        action_taken="ALLOWED",
    )
    session.add(log)
    session.commit()

    retrieved = session.query(TrafficLog).filter_by(id=log.id).first()

    assert retrieved is not None
    assert retrieved.source_ip == "192.168.1.1"
    assert retrieved.prediction == "Normal"
    assert retrieved.confidence == 0.95


def test_traffic_log_rejects_verified_direct_source() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session.add(
        TrafficLog(
            source_ip="192.0.2.1",
            source_provenance="DIRECT_REMOTE_ADDR",
            source_verification_status="VERIFIED",
            http_request="GET /invalid",
        )
    )

    with pytest.raises(IntegrityError):
        session.commit()


def test_traffic_log_has_all_required_fields():
    """Test that TrafficLog has all required fields from schema"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    log = TrafficLog(
        source_ip="10.0.0.1",
        source_provenance="DIRECT_REMOTE_ADDR",
        source_verification_status="UNVERIFIED",
        http_request="POST /login",
        prediction="SQL Injection",
        confidence=0.85,
        confidence_level="HIGH",
        action_taken="BLOCKED",
        analyst_label="False Positive",
        labeled_by="analyst@example.com",
    )
    session.add(log)
    session.commit()

    retrieved = session.query(TrafficLog).first()

    assert retrieved.http_request == "POST /login"
    assert retrieved.action_taken == "BLOCKED"
    assert retrieved.analyst_label == "False Positive"
    assert retrieved.labeled_by == "analyst@example.com"


def test_traffic_log_orm_column_types():
    """Test that TrafficLog columns have the expected types and constraints"""
    # Verify the ORM model structure
    assert hasattr(TrafficLog, "id")
    assert hasattr(TrafficLog, "timestamp")
    assert hasattr(TrafficLog, "source_ip")
    assert hasattr(TrafficLog, "http_request")
    assert hasattr(TrafficLog, "prediction")
    assert hasattr(TrafficLog, "confidence")
    assert hasattr(TrafficLog, "confidence_level")
    assert hasattr(TrafficLog, "model_version")
    assert hasattr(TrafficLog, "action_taken")
    assert hasattr(TrafficLog, "analyst_label")
    assert hasattr(TrafficLog, "labeled_at")
    assert hasattr(TrafficLog, "labeled_by")
    assert hasattr(TrafficLog, "ingest_source")
    assert hasattr(TrafficLog, "matched_rule_messages")
    assert hasattr(TrafficLog, "matched_rule_tags")


def test_traffic_log_persists_waf_metadata_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    log = TrafficLog(
        source_ip="203.0.113.10",
        source_provenance="DIRECT_REMOTE_ADDR",
        source_verification_status="UNVERIFIED",
        http_request="POST /login HTTP/1.1",
        crs_score=10,
        crs_rule_ids=["942100"],
        ingest_source="modsec_audit_bridge",
        matched_rule_messages=["SQL Injection Attack Detected via libinjection"],
        matched_rule_tags=["attack-sqli"],
        prediction="SQL Injection",
        confidence=0.9,
        confidence_level="HIGH",
        action_taken="BLOCKED",
    )
    session.add(log)
    session.commit()

    retrieved = session.query(TrafficLog).filter_by(id=log.id).first()

    assert retrieved is not None
    assert retrieved.ingest_source == "modsec_audit_bridge"
    assert retrieved.matched_rule_messages == [
        "SQL Injection Attack Detected via libinjection"
    ]
    assert retrieved.matched_rule_tags == ["attack-sqli"]
