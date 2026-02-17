from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Generator

from web_app.config import get_settings

settings = get_settings()

# Use SQLite for testing, PostgreSQL for production
engine = create_engine(
    settings.database_url if not settings.is_development else "sqlite:///./test.db",
    connect_args={"check_same_thread": False} if settings.is_development else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class TrafficLog(Base):
    """Database model for storing traffic logs and predictions."""

    __tablename__ = "traffic_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    source_ip = Column(String(45), index=True)
    http_request = Column(Text, nullable=False)
    prediction = Column(String(50), index=True)
    confidence = Column(Float, nullable=False)
    confidence_level = Column(String(10), nullable=False)
    action_taken = Column(String(50))
    analyst_label = Column(String(50), nullable=True)
    labeled_at = Column(DateTime, nullable=True)
    labeled_by = Column(String(100), nullable=True)


def init_db():
    """Initialize the database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Database session dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
