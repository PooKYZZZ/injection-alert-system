"""Add durable PR4 shadow enforcement recommendations."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260720_000023"
down_revision = "20260720_000022"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def _apply_postgres_security() -> None:
    if _is_sqlite():
        return

    op.execute(
        sa.text(
            "ALTER TABLE public.enforcement_recommendations ENABLE ROW LEVEL SECURITY"
        )
    )
    op.execute(
        sa.text(
            "REVOKE ALL ON TABLE public.enforcement_recommendations FROM PUBLIC"
        )
    )
    op.execute(
        sa.text(
            """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.enforcement_recommendations FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.enforcement_recommendations FROM authenticated';
  END IF;
END
$$
"""
        )
    )


def upgrade() -> None:
    op.create_table(
        "enforcement_recommendations",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "trigger_traffic_log_id",
            sa.Integer(),
            sa.ForeignKey("traffic_logs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("enforcement_tier", sa.String(length=10), nullable=False),
        sa.Column("recommended_action", sa.String(length=32), nullable=False),
        sa.Column(
            "enforcement_mode",
            sa.String(length=16),
            nullable=False,
            server_default="SHADOW",
        ),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "trigger_traffic_log_id",
            name="uq_enforcement_recommendations_trigger_traffic_log_id",
        ),
        sa.CheckConstraint(
            "scope = 'RECORD_SEARCH'",
            name="enforcement_recommendations_scope_allowed",
        ),
        sa.CheckConstraint(
            "enforcement_tier IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="enforcement_recommendations_tier_allowed",
        ),
        sa.CheckConstraint(
            "recommended_action IN ('MONITOR', 'THROTTLE', 'APPLICATION_BLOCK', 'WAF_BLOCK')",
            name="enforcement_recommendations_action_allowed",
        ),
        sa.CheckConstraint(
            "enforcement_mode = 'SHADOW'",
            name="enforcement_recommendations_mode_allowed",
        ),
        sa.CheckConstraint(
            "length(policy_version) BETWEEN 1 AND 64",
            name="enforcement_recommendations_policy_version_length",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="enforcement_recommendations_expiry_after_creation",
        ),
    )
    op.create_index(
        "ix_enforcement_recommendations_scope_expires_at",
        "enforcement_recommendations",
        ["scope", "expires_at"],
    )
    _apply_postgres_security()


def downgrade() -> None:
    op.drop_index(
        "ix_enforcement_recommendations_scope_expires_at",
        table_name="enforcement_recommendations",
    )
    op.drop_table("enforcement_recommendations")
