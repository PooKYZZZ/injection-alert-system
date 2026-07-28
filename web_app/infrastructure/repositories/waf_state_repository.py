from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from web_app.domain.waf_state import (
    PR7_DEFAULT_CAPACITY,
    PR7_ENFORCEMENT_MODE,
    PR7_PATH,
    PR7_POLICY_VERSION,
    PR7_SCOPE,
    WafLifecycle,
    canonicalize_waf_source_ip,
)
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
    """Async PostgreSQL transaction boundary for PR7 desired WAF state."""

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
    def _validate_expiry(value: datetime, name: str) -> None:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(f"{name} must be UTC-aware")

    @staticmethod
    def _validate_capacity(capacity: int) -> None:
        if not 1 <= capacity <= 512:
            raise ValueError("capacity must be between 1 and 512")

    async def _expire_active(
        self, control: WafEnforcementStateRow, now: datetime
    ) -> bool:
        rows = await self.session.scalars(
            select(WafEffectiveStateRow)
            .where(
                WafEffectiveStateRow.status == WafLifecycle.ACTIVE,
                WafEffectiveStateRow.expires_at <= now,
            )
            .with_for_update()
        )
        changed = list(rows)
        if not changed:
            return False
        revision = control.revision + 1
        control.revision = revision
        control.updated_at = now
        for row in changed:
            row.status = WafLifecycle.EXPIRED
            row.terminal_at = now
            row.revision = revision
        return True

    async def record_critical_waf_recommendation(
        self,
        *,
        trigger_traffic_log_id: int,
        recommendation_expires_at: datetime,
        effective_expires_at: datetime,
        capacity: int = PR7_DEFAULT_CAPACITY,
    ) -> WafMutationResult:
        """Atomically create and consider one fixed-policy PR7 recommendation.

        Source identity, path, prediction, confidence, status, provenance and
        recommendation policy are read from authoritative database rows. An
        existing recommendation is replay-only and is never reconsidered.
        """

        self._validate_expiry(recommendation_expires_at, "recommendation expiry")
        self._validate_expiry(effective_expires_at, "effective expiry")
        self._validate_capacity(capacity)
        dialect_name = self.session.bind.dialect.name if self.session.bind else ""
        insert = postgresql_insert if dialect_name == "postgresql" else sqlite_insert

        async with self.session.begin():
            await self.session.execute(
                text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            )
            control = await self._lock_control()
            now = await self._mutation_now()
            values = {
                "trigger_traffic_log_id": trigger_traffic_log_id,
                "scope": PR7_SCOPE,
                "enforcement_tier": "CRITICAL",
                "recommended_action": "WAF_BLOCK",
                "enforcement_mode": PR7_ENFORCEMENT_MODE,
                "policy_version": PR7_POLICY_VERSION,
                "created_at": now,
                "expires_at": recommendation_expires_at,
            }
            statement = insert(EnforcementRecommendationRow).values(**values)
            result = await self.session.execute(
                statement.on_conflict_do_nothing(
                    index_elements=[EnforcementRecommendationRow.trigger_traffic_log_id]
                ).returning(EnforcementRecommendationRow.id)
            )
            recommendation_id = result.scalar_one_or_none()
            inserted_now = recommendation_id is not None
            if recommendation_id is None:
                recommendation_id = await self.session.scalar(
                    select(EnforcementRecommendationRow.id).where(
                        EnforcementRecommendationRow.trigger_traffic_log_id
                        == trigger_traffic_log_id
                    )
                )
            if recommendation_id is None:
                raise RuntimeError("recommendation insert did not return an id")

            cleaned = await self._expire_active(control, now)
            if not inserted_now:
                return WafMutationResult(
                    "DUPLICATE_WITH_CLEANUP" if cleaned else "DUPLICATE",
                    int(recommendation_id),
                    control.revision,
                    cleaned,
                )

            recommendation = await self.session.scalar(
                select(EnforcementRecommendationRow).where(
                    EnforcementRecommendationRow.id == recommendation_id
                )
            )
            traffic = (
                await self.session.execute(
                    select(
                        TrafficLog.status,
                        TrafficLog.prediction,
                        TrafficLog.confidence_level,
                        TrafficLog.request_path,
                        TrafficLog.source_verification_status,
                        TrafficLog.source_provenance,
                        TrafficLog.source_ip,
                    ).where(TrafficLog.id == trigger_traffic_log_id)
                )
            ).one_or_none()
            if recommendation is None or traffic is None:
                return WafMutationResult(
                    "INELIGIBLE", int(recommendation_id), control.revision, cleaned
                )

            canonical_ip = canonicalize_waf_source_ip(traffic.source_ip)
            if (
                traffic.status != "COMPLETED"
                or traffic.prediction in (None, "Normal")
                or traffic.confidence_level != "CRITICAL"
                or traffic.request_path != PR7_PATH
                or traffic.source_verification_status != "VERIFIED"
                or traffic.source_provenance != "CLOUDFLARE_CONNECTING_IP"
                or canonical_ip is None
                or recommendation.scope != PR7_SCOPE
                or recommendation.enforcement_tier != "CRITICAL"
                or recommendation.recommended_action != "WAF_BLOCK"
                or recommendation.enforcement_mode != PR7_ENFORCEMENT_MODE
                or recommendation.policy_version != PR7_POLICY_VERSION
            ):
                return WafMutationResult(
                    "INELIGIBLE", int(recommendation_id), control.revision, cleaned
                )
            if (
                effective_expires_at <= now
                or effective_expires_at > recommendation.expires_at
            ):
                return WafMutationResult(
                    "EXPIRED_CANDIDATE",
                    int(recommendation_id),
                    control.revision,
                    cleaned,
                )

            owner = await self.session.scalar(
                select(WafEffectiveStateRow)
                .where(
                    WafEffectiveStateRow.status == WafLifecycle.ACTIVE,
                    WafEffectiveStateRow.source_ip == canonical_ip,
                    WafEffectiveStateRow.protected_path == PR7_PATH,
                )
                .with_for_update()
            )
            if owner is not None and effective_expires_at <= owner.expires_at:
                return WafMutationResult(
                    "SHORTER_OR_EQUAL",
                    int(recommendation_id),
                    control.revision,
                    cleaned,
                )

            active_count = await self.session.scalar(
                select(func.count())
                .select_from(WafEffectiveStateRow)
                .where(WafEffectiveStateRow.status == WafLifecycle.ACTIVE)
            )
            if owner is None and int(active_count or 0) >= capacity:
                return WafMutationResult(
                    "CAPACITY_REJECTED",
                    int(recommendation_id),
                    control.revision,
                    cleaned,
                )

            revision = control.revision + 1
            control.revision = revision
            control.updated_at = now
            if owner is not None:
                owner.status = WafLifecycle.SUPERSEDED
                owner.terminal_at = now
                owner.revision = revision
            self.session.add(
                WafEffectiveStateRow(
                    recommendation_id=int(recommendation_id),
                    source_ip=canonical_ip,
                    protected_path=PR7_PATH,
                    status=WafLifecycle.ACTIVE,
                    created_at=now,
                    activated_at=now,
                    expires_at=effective_expires_at,
                    revision=revision,
                )
            )
            return WafMutationResult(
                "SUPERSEDED" if owner is not None else "ACTIVATED",
                int(recommendation_id),
                revision,
                True,
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
                if revision is None:
                    raise RuntimeError("WAF enforcement state singleton is missing")
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
                revision=int(revision),
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
