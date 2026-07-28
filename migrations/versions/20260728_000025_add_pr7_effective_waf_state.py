"""Add PR7 effective WAF state and singleton desired-state revision."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260728_000025"
down_revision = "20260721_000024"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def _security(table_name: str) -> None:
    if _is_sqlite():
        return
    op.execute(sa.text(f"ALTER TABLE public.{table_name} ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text(f"REVOKE ALL ON TABLE public.{table_name} FROM PUBLIC"))
    op.execute(
        sa.text(
            f"""
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.{table_name} FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.{table_name} FROM authenticated';
  END IF;
END
$$
"""
        )
    )


def upgrade() -> None:
    op.create_table(
        "waf_enforcement_state",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("id = 1", name="waf_enforcement_state_singleton_id"),
        sa.CheckConstraint(
            "revision >= 0", name="waf_enforcement_state_revision_nonnegative"
        ),
    )
    op.execute(
        sa.text("INSERT INTO waf_enforcement_state (id, revision) VALUES (1, 0)")
    )
    op.create_table(
        "waf_effective_state",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "recommendation_id",
            sa.Integer(),
            sa.ForeignKey("enforcement_recommendations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_ip", sa.String(length=45), nullable=False),
        sa.Column("protected_path", sa.String(length=512), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint(
            "recommendation_id", name="uq_waf_effective_state_recommendation_id"
        ),
        sa.CheckConstraint(
            "status IN ('ACTIVE', 'SUPERSEDED', 'REVOKED', 'EXPIRED')",
            name="waf_effective_state_status_allowed",
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name="waf_effective_state_expiry_after_creation"
        ),
        sa.CheckConstraint(
            "(status = 'ACTIVE' AND terminal_at IS NULL) OR (status <> 'ACTIVE' AND terminal_at IS NOT NULL)",
            name="waf_effective_state_terminal_consistency",
        ),
        sa.CheckConstraint(
            "activated_at IS NOT NULL",
            name="waf_effective_state_activation_timestamp",
        ),
        sa.CheckConstraint(
            "revision >= 0", name="waf_effective_state_revision_nonnegative"
        ),
        sa.CheckConstraint(
            "protected_path = '/records/search'",
            name="waf_effective_state_protected_path_allowed",
        ),
    )
    op.create_index(
        "uq_waf_effective_state_active_source_path",
        "waf_effective_state",
        ["source_ip", "protected_path"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )
    _security("waf_enforcement_state")
    _security("waf_effective_state")


def downgrade() -> None:
    op.drop_index(
        "uq_waf_effective_state_active_source_path", table_name="waf_effective_state"
    )
    op.drop_table("waf_effective_state")
    op.drop_table("waf_enforcement_state")
