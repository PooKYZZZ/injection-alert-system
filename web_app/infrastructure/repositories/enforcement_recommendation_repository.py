from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.domain.enforcement import (
    ChallengeGrant,
    CounterKind,
    EffectiveRecommendation,
    EnforcementMode,
    EnforcementScope,
    EnforcementTier,
    IEnforcementRecommendationRepository,
    NewEnforcementRecommendation,
    RecommendedAction,
    RequestWindowState,
)
from web_app.infrastructure.database.database import (
    EnforcementChallengeGrantRow,
    EnforcementRecommendationRow,
    EnforcementRequestWindowRow,
    TrafficLog,
)


class EnforcementRecommendationRepository(IEnforcementRecommendationRepository):
    """Async SQLAlchemy adapter for the PR4 recommendation table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    async def insert_if_absent(
        self, recommendation: NewEnforcementRecommendation
    ) -> bool:
        values = {
            "trigger_traffic_log_id": recommendation.trigger_traffic_log_id,
            "scope": recommendation.scope.value,
            "enforcement_tier": recommendation.tier.value,
            "recommended_action": recommendation.action.value,
            "enforcement_mode": recommendation.mode.value.upper(),
            "policy_version": recommendation.policy_version,
            "created_at": recommendation.created_at,
            "expires_at": recommendation.expires_at,
        }
        dialect_name = self._session.bind.dialect.name if self._session.bind else ""
        if dialect_name == "postgresql":
            statement = postgresql_insert(EnforcementRecommendationRow).values(**values)
        else:
            statement = sqlite_insert(EnforcementRecommendationRow).values(**values)

        result = await self._session.execute(
            statement.on_conflict_do_nothing(
                index_elements=[EnforcementRecommendationRow.trigger_traffic_log_id]
            ).returning(EnforcementRecommendationRow.id)
        )
        inserted_id = result.scalar_one_or_none()
        await self._session.commit()
        return inserted_id is not None

    async def find_effective_active(
        self,
        *,
        source_ip: str,
        scope: EnforcementScope,
        now: datetime,
    ) -> EffectiveRecommendation | None:
        tier_rank = case(
            (EnforcementRecommendationRow.enforcement_tier == "CRITICAL", 4),
            (EnforcementRecommendationRow.enforcement_tier == "HIGH", 3),
            (EnforcementRecommendationRow.enforcement_tier == "MEDIUM", 2),
            (EnforcementRecommendationRow.enforcement_tier == "LOW", 1),
            else_=0,
        )
        statement = (
            select(EnforcementRecommendationRow, TrafficLog.source_verification_status)
            .join(
                TrafficLog,
                EnforcementRecommendationRow.trigger_traffic_log_id == TrafficLog.id,
            )
            .where(
                TrafficLog.source_ip == source_ip,
                EnforcementRecommendationRow.scope == scope.value,
                EnforcementRecommendationRow.enforcement_mode == "SHADOW",
                EnforcementRecommendationRow.expires_at > now,
            )
            .order_by(
                tier_rank.desc(),
                EnforcementRecommendationRow.created_at.desc(),
                EnforcementRecommendationRow.id.desc(),
            )
            .limit(1)
        )
        row = (await self._session.execute(statement)).first()
        if row is None:
            return None

        recommendation, source_verification_status = row
        return EffectiveRecommendation(
            trigger_traffic_log_id=recommendation.trigger_traffic_log_id,
            scope=EnforcementScope(recommendation.scope),
            tier=EnforcementTier(recommendation.enforcement_tier),
            action=RecommendedAction(recommendation.recommended_action),
            mode=EnforcementMode(recommendation.enforcement_mode.lower()),
            policy_version=recommendation.policy_version,
            created_at=recommendation.created_at,
            expires_at=recommendation.expires_at,
            source_verification_status=source_verification_status,
        )

    async def find_effective_enforceable(
        self,
        *,
        source_ip: str,
        scope: EnforcementScope,
        now: datetime,
        policy_version: str,
        require_verified: bool,
    ) -> EffectiveRecommendation | None:
        tier_rank = case(
            (EnforcementRecommendationRow.enforcement_tier == "MEDIUM", 2),
            (EnforcementRecommendationRow.enforcement_tier == "LOW", 1),
            else_=0,
        )
        statement = (
            select(EnforcementRecommendationRow, TrafficLog.source_verification_status)
            .join(
                TrafficLog,
                EnforcementRecommendationRow.trigger_traffic_log_id == TrafficLog.id,
            )
            .where(
                TrafficLog.source_ip == source_ip,
                EnforcementRecommendationRow.scope == scope.value,
                EnforcementRecommendationRow.enforcement_mode == "ENFORCE",
                EnforcementRecommendationRow.policy_version == policy_version,
                EnforcementRecommendationRow.enforcement_tier.in_(["LOW", "MEDIUM"]),
                EnforcementRecommendationRow.expires_at > now,
            )
            .order_by(
                tier_rank.desc(),
                EnforcementRecommendationRow.created_at.desc(),
                EnforcementRecommendationRow.id.desc(),
            )
            .limit(1)
        )
        if require_verified:
            statement = statement.where(
                TrafficLog.source_verification_status == "VERIFIED"
            )
        row = (await self._session.execute(statement)).first()
        if row is None:
            return None
        recommendation, source_verification_status = row
        return EffectiveRecommendation(
            trigger_traffic_log_id=recommendation.trigger_traffic_log_id,
            scope=EnforcementScope(recommendation.scope),
            tier=EnforcementTier(recommendation.enforcement_tier),
            action=RecommendedAction(recommendation.recommended_action),
            mode=EnforcementMode(recommendation.enforcement_mode.lower()),
            policy_version=recommendation.policy_version,
            created_at=recommendation.created_at,
            expires_at=recommendation.expires_at,
            source_verification_status=source_verification_status,
        )

    @staticmethod
    def _window_bounds(now: datetime, window_seconds: int) -> tuple[datetime, datetime]:
        current = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
        epoch_seconds = int(current.timestamp())
        window_start_epoch = epoch_seconds // window_seconds * window_seconds
        window_start = datetime.fromtimestamp(window_start_epoch, tz=timezone.utc)
        return window_start, window_start + timedelta(seconds=window_seconds)

    async def increment_request_window(
        self,
        *,
        source_ip: str,
        scope: EnforcementScope,
        counter_kind: CounterKind,
        policy_version: str,
        now: datetime,
        window_seconds: int,
    ) -> RequestWindowState:
        window_start, window_end = self._window_bounds(now, window_seconds)
        values = {
            "source_ip": source_ip,
            "scope": scope.value,
            "counter_kind": counter_kind.value,
            "policy_version": policy_version,
            "window_start": window_start,
            "window_end": window_end,
            "request_count": 1,
            "created_at": now,
            "updated_at": now,
        }
        dialect_name = self._session.bind.dialect.name if self._session.bind else ""
        insert = (
            postgresql_insert(EnforcementRequestWindowRow)
            if dialect_name == "postgresql"
            else sqlite_insert(EnforcementRequestWindowRow)
        )
        statement = insert.values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=[
                EnforcementRequestWindowRow.source_ip,
                EnforcementRequestWindowRow.scope,
                EnforcementRequestWindowRow.counter_kind,
                EnforcementRequestWindowRow.policy_version,
                EnforcementRequestWindowRow.window_start,
            ],
            set_={
                "request_count": EnforcementRequestWindowRow.request_count + 1,
                "updated_at": now,
            },
        ).returning(
            EnforcementRequestWindowRow.window_start,
            EnforcementRequestWindowRow.window_end,
            EnforcementRequestWindowRow.request_count,
        )
        row = (await self._session.execute(statement)).one()
        await self._session.commit()
        return RequestWindowState(
            source_ip=source_ip,
            scope=scope,
            counter_kind=counter_kind,
            policy_version=policy_version,
            window_start=self._as_utc(row.window_start),
            window_end=self._as_utc(row.window_end),
            request_count=row.request_count,
        )

    async def find_valid_challenge_grant(
        self,
        *,
        source_ip: str,
        scope: EnforcementScope,
        tier: EnforcementTier,
        policy_version: str,
        now: datetime,
    ) -> ChallengeGrant | None:
        statement = select(EnforcementChallengeGrantRow).where(
            EnforcementChallengeGrantRow.source_ip == source_ip,
            EnforcementChallengeGrantRow.scope == scope.value,
            EnforcementChallengeGrantRow.enforcement_tier == tier.value,
            EnforcementChallengeGrantRow.policy_version == policy_version,
            EnforcementChallengeGrantRow.expires_at > now,
        )
        row = (await self._session.execute(statement)).scalar_one_or_none()
        if row is None:
            return None
        return ChallengeGrant(
            source_ip=row.source_ip,
            scope=EnforcementScope(row.scope),
            tier=EnforcementTier(row.enforcement_tier),
            policy_version=row.policy_version,
            verified_at=self._as_utc(row.verified_at),
            expires_at=self._as_utc(row.expires_at),
        )

    async def upsert_challenge_grant(self, grant: ChallengeGrant) -> ChallengeGrant:
        values = {
            "source_ip": grant.source_ip,
            "scope": grant.scope.value,
            "enforcement_tier": grant.tier.value,
            "policy_version": grant.policy_version,
            "verified_at": grant.verified_at,
            "expires_at": grant.expires_at,
            "created_at": grant.verified_at,
            "updated_at": grant.verified_at,
        }
        dialect_name = self._session.bind.dialect.name if self._session.bind else ""
        insert = (
            postgresql_insert(EnforcementChallengeGrantRow)
            if dialect_name == "postgresql"
            else sqlite_insert(EnforcementChallengeGrantRow)
        )
        statement = insert.values(**values).on_conflict_do_update(
            index_elements=[
                EnforcementChallengeGrantRow.source_ip,
                EnforcementChallengeGrantRow.scope,
                EnforcementChallengeGrantRow.enforcement_tier,
                EnforcementChallengeGrantRow.policy_version,
            ],
            set_={
                "verified_at": grant.verified_at,
                "expires_at": grant.expires_at,
                "updated_at": grant.verified_at,
            },
        )
        await self._session.execute(statement)
        await self._session.commit()
        return grant
