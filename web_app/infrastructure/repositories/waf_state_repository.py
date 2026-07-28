from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.domain.waf_state import WafLifecycle, canonicalize_waf_source_ip
from web_app.infrastructure.database.database import (
    EnforcementRecommendationRow,
    TrafficLog,
    WafEffectiveStateRow,
    WafEnforcementStateRow,
)


@dataclass(frozen=True)
class WafMutationResult:
    category: str
    recommendation_id: int
    revision: int
    state_changed: bool


@dataclass(frozen=True)
class WafSnapshot:
    revision: int
    items: list[dict[str, object]]


class WafStateRepository:
    """PostgreSQL transaction boundary for PR7 desired WAF state."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _lock_control(self) -> WafEnforcementStateRow:
        row = await self.session.scalar(
            select(WafEnforcementStateRow)
            .where(WafEnforcementStateRow.id == 1)
            .with_for_update()
        )
        if row is None:
            raise RuntimeError("WAF enforcement state singleton is missing")
        return row

    async def _mutation_now(self) -> datetime:
        value = await self.session.scalar(select(func.clock_timestamp()))
        if value is None:
            raise RuntimeError("database mutation clock unavailable")
        return value

    @staticmethod
    def _validate_candidate(
        *, source_ip: str, protected_path: str, expires_at: datetime, capacity: int
    ) -> str:
        canonical_ip = canonicalize_waf_source_ip(source_ip)
        if canonical_ip is None:
            raise ValueError("valid source IP required")
        if (
            not protected_path.startswith("/")
            or "?" in protected_path
            or len(protected_path) > 512
        ):
            raise ValueError("canonical protected path required")
        if expires_at.tzinfo is None or expires_at.utcoffset() is None:
            raise ValueError("UTC-aware datetime required")
        if not 1 <= capacity <= 512:
            raise ValueError("capacity must be between 1 and 512")
        return canonical_ip

    async def _record_active_in_transaction(
        self,
        *,
        recommendation_id: int,
        canonical_ip: str,
        protected_path: str,
        expires_at: datetime,
        capacity: int = 64,
    ) -> WafMutationResult:
        control = await self._lock_control()
        now = await self._mutation_now()
        recommendation = await self.session.scalar(
            select(EnforcementRecommendationRow).where(
                EnforcementRecommendationRow.id == recommendation_id
            )
        )
        if recommendation is None:
            raise ValueError("recommendation not found")
        changed_rows = await self.session.scalars(
            select(WafEffectiveStateRow)
            .where(
                WafEffectiveStateRow.status == WafLifecycle.ACTIVE,
                WafEffectiveStateRow.expires_at <= now,
            )
            .with_for_update()
        )
        changed = list(changed_rows)
        for row in changed:
            row.status = WafLifecycle.EXPIRED
            row.terminal_at = now
        revision = control.revision + (1 if changed else 0)
        if changed:
            control.revision = revision
            control.updated_at = now
            for row in changed:
                row.revision = revision

        if (
            recommendation.enforcement_tier != "CRITICAL"
            or recommendation.recommended_action != "WAF_BLOCK"
        ):
            return WafMutationResult(
                "INELIGIBLE", recommendation_id, revision, bool(changed)
            )
        source_record = (
            await self.session.execute(
                select(
                    TrafficLog.source_ip,
                    TrafficLog.source_verification_status,
                    TrafficLog.request_path,
                ).where(TrafficLog.id == recommendation.trigger_traffic_log_id)
            )
        ).one_or_none()
        if (
            source_record is None
            or source_record.source_verification_status != "VERIFIED"
            or canonicalize_waf_source_ip(source_record.source_ip) != canonical_ip
            or source_record.request_path != protected_path
        ):
            return WafMutationResult(
                "SOURCE_INELIGIBLE", recommendation_id, revision, bool(changed)
            )
        if expires_at <= now:
            return WafMutationResult(
                "EXPIRED_CANDIDATE", recommendation_id, revision, bool(changed)
            )

        existing = await self.session.scalar(
            select(WafEffectiveStateRow).where(
                WafEffectiveStateRow.recommendation_id == recommendation_id
            )
        )
        if existing is not None:
            return WafMutationResult(
                "DUPLICATE_WITH_CLEANUP" if changed else "DUPLICATE",
                recommendation_id,
                revision,
                bool(changed),
            )

        owner = await self.session.scalar(
            select(WafEffectiveStateRow)
            .where(
                WafEffectiveStateRow.status == WafLifecycle.ACTIVE,
                WafEffectiveStateRow.source_ip == canonical_ip,
                WafEffectiveStateRow.protected_path == protected_path,
            )
            .with_for_update()
        )
        if owner is not None and expires_at <= owner.expires_at:
            return WafMutationResult(
                "SHORTER_OR_EQUAL_WITH_CLEANUP" if changed else "SHORTER_OR_EQUAL",
                recommendation_id,
                revision,
                bool(changed),
            )

        active_count = await self.session.scalar(
            select(func.count())
            .select_from(WafEffectiveStateRow)
            .where(WafEffectiveStateRow.status == WafLifecycle.ACTIVE)
        )
        if owner is None and int(active_count or 0) >= capacity:
            return WafMutationResult(
                "CAPACITY_REJECTED", recommendation_id, revision, bool(changed)
            )

        if not changed:
            revision = control.revision + 1
            control.revision = revision
            control.updated_at = now
        if owner is not None:
            owner.status = WafLifecycle.SUPERSEDED
            owner.terminal_at = now
            owner.revision = revision
        self.session.add(
            WafEffectiveStateRow(
                recommendation_id=recommendation_id,
                source_ip=canonical_ip,
                protected_path=protected_path,
                status=WafLifecycle.ACTIVE,
                created_at=now,
                activated_at=now,
                expires_at=expires_at,
                revision=revision,
            )
        )
        return WafMutationResult(
            "SUPERSEDED" if owner is not None else "ACTIVATED",
            recommendation_id,
            revision,
            True,
        )

    async def record_active(
        self,
        *,
        recommendation_id: int,
        source_ip: str,
        protected_path: str,
        expires_at: datetime,
        capacity: int = 64,
    ) -> WafMutationResult:
        canonical_ip = self._validate_candidate(
            source_ip=source_ip,
            protected_path=protected_path,
            expires_at=expires_at,
            capacity=capacity,
        )
        async with self.session.begin():
            await self.session.execute(
                text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            )
            return await self._record_active_in_transaction(
                recommendation_id=recommendation_id,
                canonical_ip=canonical_ip,
                protected_path=protected_path,
                expires_at=expires_at,
                capacity=capacity,
            )

    async def record_recommendation_and_active(
        self,
        *,
        trigger_traffic_log_id: int,
        scope: str,
        enforcement_tier: str,
        recommended_action: str,
        enforcement_mode: str,
        policy_version: str,
        created_at: datetime,
        recommendation_expires_at: datetime,
        source_ip: str,
        protected_path: str,
        expires_at: datetime,
        capacity: int = 64,
    ) -> WafMutationResult:
        canonical_ip = self._validate_candidate(
            source_ip=source_ip,
            protected_path=protected_path,
            expires_at=expires_at,
            capacity=capacity,
        )
        values = {
            "trigger_traffic_log_id": trigger_traffic_log_id,
            "scope": scope,
            "enforcement_tier": enforcement_tier,
            "recommended_action": recommended_action,
            "enforcement_mode": enforcement_mode,
            "policy_version": policy_version,
            "created_at": created_at,
            "expires_at": recommendation_expires_at,
        }
        dialect_name = self.session.bind.dialect.name if self.session.bind else ""
        insert = postgresql_insert if dialect_name == "postgresql" else sqlite_insert
        async with self.session.begin():
            await self.session.execute(
                text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            )
            await self._lock_control()
            statement = insert(EnforcementRecommendationRow).values(**values)
            result = await self.session.execute(
                statement.on_conflict_do_nothing(
                    index_elements=[EnforcementRecommendationRow.trigger_traffic_log_id]
                ).returning(EnforcementRecommendationRow.id)
            )
            recommendation_id = result.scalar_one_or_none()
            if recommendation_id is None:
                recommendation_id = await self.session.scalar(
                    select(EnforcementRecommendationRow.id).where(
                        EnforcementRecommendationRow.trigger_traffic_log_id
                        == trigger_traffic_log_id
                    )
                )
            if recommendation_id is None:
                raise RuntimeError("recommendation upsert did not return an id")
            return await self._record_active_in_transaction(
                recommendation_id=int(recommendation_id),
                canonical_ip=canonical_ip,
                protected_path=protected_path,
                expires_at=expires_at,
                capacity=capacity,
            )

    async def snapshot(self) -> WafSnapshot:
        bind = self.session.bind
        if bind is None:
            raise RuntimeError("snapshot database bind is missing")
        snapshot_engine = bind.execution_options(
            isolation_level="REPEATABLE READ",
            postgresql_readonly=True,
        )
        async with snapshot_engine.connect() as connection:
            async with connection.begin():
                revision = (
                    await connection.execute(
                        select(WafEnforcementStateRow.revision).where(
                            WafEnforcementStateRow.id == 1
                        )
                    )
                ).scalar_one_or_none()
                rows = (
                    await connection.execute(
                        select(
                            WafEffectiveStateRow.id,
                            WafEffectiveStateRow.recommendation_id,
                            WafEffectiveStateRow.source_ip,
                            WafEffectiveStateRow.protected_path,
                            WafEffectiveStateRow.expires_at,
                        )
                        .where(WafEffectiveStateRow.status == WafLifecycle.ACTIVE)
                        .order_by(WafEffectiveStateRow.id)
                    )
                ).all()
            return WafSnapshot(
                revision=int(revision or 0),
                items=[
                    {
                        "entry_id": row.id,
                        "recommendation_id": row.recommendation_id,
                        "source_ip": row.source_ip,
                        "request_path": row.protected_path,
                        "expires_at": row.expires_at,
                    }
                    for row in rows
                ],
            )

    async def revoke(self, *, recommendation_id: int) -> WafMutationResult:
        async with self.session.begin():
            await self.session.execute(
                text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            )
            control = await self._lock_control()
            now = await self._mutation_now()
            row = await self.session.scalar(
                select(WafEffectiveStateRow)
                .where(WafEffectiveStateRow.recommendation_id == recommendation_id)
                .with_for_update()
            )
            if row is None or row.status != WafLifecycle.ACTIVE:
                return WafMutationResult(
                    "TERMINAL_NOOP", recommendation_id, control.revision, False
                )
            revision = control.revision + 1
            row.status = WafLifecycle.REVOKED
            row.terminal_at = now
            row.revision = revision
            control.revision = revision
            control.updated_at = now
            return WafMutationResult("REVOKED", recommendation_id, revision, True)
