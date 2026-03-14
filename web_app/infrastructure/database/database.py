from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, MetaData
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import AsyncGenerator

from web_app.config import get_settings

settings = get_settings()

if "postgresql://" in settings.database_url and not settings.database_url.startswith("postgresql+asyncpg://"):
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
elif settings.database_url.startswith("sqlite://") and not settings.database_url.startswith("sqlite+aiosqlite://"):
    database_url = settings.database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
else:
    database_url = settings.database_url

engine = create_async_engine(
    database_url,
    echo=settings.is_development
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

Base = declarative_base(metadata=MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}))


class TrafficLog(Base):
    """Database model for storing traffic logs and predictions."""

    __tablename__ = "traffic_logs"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(128), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    source_ip = Column(String(45), index=True)
    request_path = Column(String(512), nullable=True)
    request_method = Column(String(16), nullable=True)
    # Retain raw header/body fidelity by folding them into http_request at ingest
    # time; do not add standalone request_headers/request_body columns.
    http_request = Column(Text, nullable=False)
    crs_score = Column(Integer, nullable=True)
    crs_rule_ids = Column(JSON, nullable=True)
    prediction = Column(String(50), index=True, nullable=True)
    confidence = Column(Float, nullable=True)
    confidence_level = Column(String(10), nullable=True)
    inference_latency_ms = Column(Float, nullable=True)
    status = Column(String(16), nullable=False, server_default="COMPLETED")
    model_version = Column(String(50), nullable=True)
    action_taken = Column(String(50), nullable=True)
    analyst_label = Column(String(50), nullable=True)
    labeled_at = Column(DateTime, nullable=True)
    labeled_by = Column(String(100), nullable=True)


async def init_db():
    """Initialize the database tables asynchronously."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency for FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session
