from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Index,
    JSON,
    MetaData,
    String,
    Text,
)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

from web_app.config import get_settings

# Type alias for backward compatibility
DatabaseSession = AsyncSession

settings = get_settings()

if "postgresql://" in settings.database_url and not settings.database_url.startswith(
    "postgresql+asyncpg://"
):
    database_url = settings.database_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    )
elif settings.database_url.startswith(
    "sqlite://"
) and not settings.database_url.startswith("sqlite+aiosqlite://"):
    database_url = settings.database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
else:
    database_url = settings.database_url

_pool_kwargs = {}
if "sqlite" not in database_url:
    _pool_kwargs = {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 3600,
        "pool_pre_ping": True,
    }
else:
    _pool_kwargs = {"pool_pre_ping": True}

engine = create_async_engine(
    database_url,
    echo=settings.is_development,
    **_pool_kwargs,
    # Supabase transaction pooler (PgBouncer) is incompatible with asyncpg
    # prepared statement caching. Disable it when using pooler endpoints.
    connect_args=(
        {"statement_cache_size": 0}
        if ("pooler.supabase.com" in database_url or ":6543/" in database_url)
        else {}
    ),
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)

Base = declarative_base(
    metadata=MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
)


class TrafficLog(Base):
    """Database model for storing traffic logs and predictions."""

    __tablename__ = "traffic_logs"
    __table_args__ = (
        CheckConstraint(
            "source_provenance IN ('CLOUDFLARE_CONNECTING_IP', 'DIRECT_REMOTE_ADDR', 'LEGACY_UNKNOWN')",
            name="source_provenance_allowed",
        ),
        CheckConstraint(
            "source_verification_status IN ('VERIFIED', 'UNVERIFIED', 'INVALID', 'LEGACY_UNKNOWN')",
            name="source_verification_status_allowed",
        ),
        CheckConstraint(
            "source_verification_status <> 'VERIFIED' OR source_ip IS NOT NULL",
            name="verified_source_ip_present",
        ),
        CheckConstraint(
            "source_verification_status <> 'INVALID' OR source_ip IS NULL",
            name="invalid_source_ip_absent",
        ),
        CheckConstraint(
            "(source_provenance = 'LEGACY_UNKNOWN') = (source_verification_status = 'LEGACY_UNKNOWN')",
            name="legacy_source_metadata_paired",
        ),
        CheckConstraint(
            "source_verification_status <> 'VERIFIED' OR source_provenance <> 'LEGACY_UNKNOWN'",
            name="verified_source_not_legacy",
        ),
        CheckConstraint(
            "source_verification_status <> 'VERIFIED' OR source_provenance = 'CLOUDFLARE_CONNECTING_IP'",
            name="verified_source_requires_cloudflare_provenance",
        ),
        CheckConstraint(
            "source_ip IS NOT NULL OR source_verification_status IN ('INVALID', 'LEGACY_UNKNOWN')",
            name="missing_source_status_valid",
        ),
        CheckConstraint(
            "ingest_fingerprint_sha256 IS NULL OR length(ingest_fingerprint_sha256) = 64",
            name="ingest_fingerprint_length",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String(128), unique=True, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    timestamp = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source_ip = Column(String(45), index=True)
    source_provenance = Column(String(32), nullable=False)
    source_verification_status = Column(String(32), nullable=False)
    ingest_fingerprint_sha256 = Column(String(64), nullable=True)
    request_path = Column(String(512), nullable=True)
    query_string = Column(String(4096), nullable=True)
    request_method = Column(String(16), nullable=True)
    # Retain raw header/body fidelity by folding them into http_request at ingest
    # time; do not add standalone request_headers/request_body columns.
    http_request = Column(Text, nullable=False)
    crs_score = Column(Integer, nullable=True)
    crs_rule_ids = Column(JSON, nullable=True)
    ingest_source = Column(String(64), nullable=True)
    matched_rule_messages = Column(JSON, nullable=True)
    matched_rule_tags = Column(JSON, nullable=True)
    prediction = Column(String(50), index=True, nullable=True)
    confidence = Column(Float, nullable=True)
    confidence_level = Column(String(10), nullable=True)
    inference_latency_ms = Column(Float, nullable=True)
    status = Column(String(16), nullable=False, server_default="COMPLETED")
    model_version = Column(String(50), nullable=True)
    lease_expires_at = Column(DateTime(timezone=True), nullable=True)
    processing_owner_token = Column(String(64), nullable=True)
    processing_attempt = Column(Integer, nullable=False, server_default="0")
    action_taken = Column(String(50), nullable=True)
    analyst_label = Column(String(50), nullable=True)
    labeled_at = Column(DateTime(timezone=True), nullable=True)
    labeled_by = Column(String(100), nullable=True)
    triage_status = Column(String(32), nullable=True)


class EnforcementRecommendationRow(Base):
    """Durable, shadow-only policy intent linked to one completed alert."""

    __tablename__ = "enforcement_recommendations"
    __table_args__ = (
        CheckConstraint(
            "scope = 'RECORD_SEARCH'",
            name="enforcement_recommendations_scope_allowed",
        ),
        CheckConstraint(
            "enforcement_tier IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="enforcement_recommendations_tier_allowed",
        ),
        CheckConstraint(
            "recommended_action IN ('MONITOR', 'THROTTLE', 'APPLICATION_BLOCK', 'WAF_BLOCK')",
            name="enforcement_recommendations_action_allowed",
        ),
        CheckConstraint(
            "enforcement_mode = 'SHADOW'",
            name="enforcement_recommendations_mode_allowed",
        ),
        CheckConstraint(
            "length(policy_version) BETWEEN 1 AND 64",
            name="enforcement_recommendations_policy_version_length",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="enforcement_recommendations_expiry_after_creation",
        ),
        Index(
            "ix_enforcement_recommendations_scope_expires_at",
            "scope",
            "expires_at",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    trigger_traffic_log_id = Column(
        Integer,
        ForeignKey("traffic_logs.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    scope = Column(String(32), nullable=False)
    enforcement_tier = Column(String(10), nullable=False)
    recommended_action = Column(String(32), nullable=False)
    enforcement_mode = Column(
        String(16), nullable=False, server_default="SHADOW"
    )
    policy_version = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)


async def init_db():
    """Initialize the database tables asynchronously."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency for FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session
