from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import AsyncGenerator

from web_app.config import get_settings

settings = get_settings()

if "postgresql://" in settings.database_url and not settings.database_url.startswith("postgresql+asyncpg://"):
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
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
    model_version = Column(String(50), nullable=True)
    action_taken = Column(String(50))
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
