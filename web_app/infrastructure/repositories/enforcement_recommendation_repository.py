from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.domain.enforcement import (
    EffectiveRecommendation,
    EnforcementMode,
    EnforcementScope,
    EnforcementTier,
    IEnforcementRecommendationRepository,
    NewEnforcementRecommendation,
    RecommendedAction,
)
from web_app.infrastructure.database.database import (
    EnforcementRecommendationRow,
    TrafficLog,
)


class EnforcementRecommendationRepository(IEnforcementRecommendationRepository):
    """Async SQLAlchemy adapter for the PR4 recommendation table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
            statement = postgresql_insert(EnforcementRecommendationRow).values(
                **values
            )
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
