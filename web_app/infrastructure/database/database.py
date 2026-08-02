from typing import AsyncGenerator

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
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
    model_input_hash = Column(String(64), nullable=True)
    preprocessing_version = Column(String(64), nullable=True)
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


class TrafficLabelReview(Base):
    """Immutable analyst review revision for one traffic log."""

    __tablename__ = "traffic_label_reviews"
    __table_args__ = (
        UniqueConstraint(
            "traffic_log_id", "revision", name="uq_traffic_label_review_revision"
        ),
        CheckConstraint(
            "verified_label IN ('Normal', 'SQL Injection', 'Code Injection', 'Other Attacks')",
            name="traffic_label_review_verified_label_allowed",
        ),
        CheckConstraint(
            "approval_state IN ('approved_for_training', 'excluded_from_training', 'superseded')",
            name="traffic_label_review_approval_state_allowed",
        ),
        CheckConstraint("revision >= 1", name="traffic_label_review_revision_positive"),
        Index(
            "ix_traffic_label_reviews_traffic_log_revision",
            "traffic_log_id",
            "revision",
        ),
        Index("ix_traffic_label_reviews_approval_state", "approval_state"),
    )

    id = Column(Integer, primary_key=True, index=True)
    traffic_log_id = Column(
        Integer,
        ForeignKey("traffic_logs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision = Column(Integer, nullable=False)
    predicted_label = Column(String(50), nullable=True)
    verified_label = Column(String(50), nullable=False)
    approval_state = Column(String(32), nullable=False)
    reviewer_id = Column(String(128), nullable=False)
    reviewer_role = Column(String(32), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=False)
    model_version = Column(String(100), nullable=True)
    prediction_confidence = Column(Float, nullable=True)
    prediction_confidence_level = Column(String(10), nullable=True)
    model_input_hash = Column(String(64), nullable=True)
    preprocessing_version = Column(String(64), nullable=True)
    ingest_event_hash = Column(String(64), nullable=True)
    source_verification_status = Column(String(32), nullable=True)
    source_provenance = Column(String(32), nullable=True)
    # Deprecated compatibility field. New reviews use model_input_hash.
    input_hash = Column(String(64), nullable=True)
    review_note = Column(String(1000), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


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
            "recommended_action IN ('MONITOR', 'CHALLENGE', 'THROTTLE', 'APPLICATION_BLOCK', 'WAF_BLOCK')",
            name="enforcement_recommendations_action_allowed",
        ),
        CheckConstraint(
            "enforcement_mode IN ('SHADOW', 'ENFORCE')",
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


class EnforcementRequestWindowRow(Base):
    """Atomic fixed-window counters for active LOW/MEDIUM enforcement."""

    __tablename__ = "enforcement_request_windows"
    __table_args__ = (
        CheckConstraint(
            "scope = 'RECORD_SEARCH'",
            name="enforcement_request_windows_scope_allowed",
        ),
        CheckConstraint(
            "counter_kind IN ('LOW_LIGHT', 'MEDIUM_HARD')",
            name="enforcement_request_windows_counter_kind_allowed",
        ),
        CheckConstraint(
            "request_count >= 0",
            name="enforcement_request_windows_count_nonnegative",
        ),
        CheckConstraint(
            "window_end > window_start",
            name="enforcement_request_windows_valid_window",
        ),
        CheckConstraint(
            "length(policy_version) BETWEEN 1 AND 64",
            name="enforcement_request_windows_policy_version_length",
        ),
        UniqueConstraint(
            "source_ip",
            "scope",
            "counter_kind",
            "policy_version",
            "window_start",
            name="uq_enforcement_request_window_key",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_ip = Column(String(45), nullable=False)
    scope = Column(String(32), nullable=False)
    counter_kind = Column(String(32), nullable=False)
    policy_version = Column(String(64), nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    request_count = Column(Integer, nullable=False, server_default="0")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EnforcementChallengeGrantRow(Base):
    """Bounded server-verified challenge state, separated by confidence tier."""

    __tablename__ = "enforcement_challenge_grants"
    __table_args__ = (
        CheckConstraint(
            "scope = 'RECORD_SEARCH'",
            name="enforcement_challenge_grants_scope_allowed",
        ),
        CheckConstraint(
            "enforcement_tier IN ('LOW', 'MEDIUM')",
            name="enforcement_challenge_grants_tier_allowed",
        ),
        CheckConstraint(
            "expires_at > verified_at",
            name="enforcement_challenge_grants_expiry_after_verification",
        ),
        CheckConstraint(
            "length(policy_version) BETWEEN 1 AND 64",
            name="enforcement_challenge_grants_policy_version_length",
        ),
        UniqueConstraint(
            "source_ip",
            "scope",
            "enforcement_tier",
            "policy_version",
            name="uq_enforcement_challenge_grant_key",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    source_ip = Column(String(45), nullable=False)
    scope = Column(String(32), nullable=False)
    enforcement_tier = Column(String(10), nullable=False)
    policy_version = Column(String(64), nullable=False)
    verified_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WafEnforcementStateRow(Base):
    """Singleton revision for the desired PR7 WAF state."""

    __tablename__ = "waf_enforcement_state"
    __table_args__ = (
        CheckConstraint("id = 1", name="waf_enforcement_state_singleton_id"),
        CheckConstraint("revision >= 0", name="waf_enforcement_state_revision_nonnegative"),
    )

    id = Column(Integer, primary_key=True, nullable=False)
    revision = Column(BigInteger, nullable=False, server_default="0")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class WafEffectiveStateRow(Base):
    """Revisioned effective-state provenance consumed by the future synchronizer."""

    __tablename__ = "waf_effective_state"
    __table_args__ = (
        CheckConstraint(
            "status IN ('ACTIVE', 'SUPERSEDED', 'REVOKED', 'EXPIRED')",
            name="waf_effective_state_status_allowed",
        ),
        CheckConstraint(
            "expires_at > created_at",
            name="waf_effective_state_expiry_after_creation",
        ),
        CheckConstraint(
            "(status = 'ACTIVE' AND terminal_at IS NULL) OR "
            "(status <> 'ACTIVE' AND terminal_at IS NOT NULL)",
            name="waf_effective_state_terminal_consistency",
        ),
        CheckConstraint(
            "activated_at IS NOT NULL",
            name="waf_effective_state_activation_timestamp",
        ),
        CheckConstraint(
            "revision >= 0",
            name="waf_effective_state_revision_nonnegative",
        ),
        CheckConstraint(
            "protected_path = '/records/search'",
            name="waf_effective_state_protected_path_allowed",
        ),
        UniqueConstraint("recommendation_id", name="uq_waf_effective_state_recommendation_id"),
        Index(
            "uq_waf_effective_state_active_source_path",
            "source_ip",
            "protected_path",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
            sqlite_where=text("status = 'ACTIVE'"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    recommendation_id = Column(
        Integer,
        ForeignKey("enforcement_recommendations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source_ip = Column(String(45), nullable=False)
    protected_path = Column(String(512), nullable=False)
    status = Column(String(16), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    terminal_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revision = Column(BigInteger, nullable=False)


async def init_db():
    """Initialize the database tables asynchronously."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency for FastAPI."""
    async with AsyncSessionLocal() as session:
        yield session
