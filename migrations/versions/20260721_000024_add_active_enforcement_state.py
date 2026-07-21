"""Add PR5 active LOW/MEDIUM enforcement state."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260721_000024"
down_revision = "20260720_000023"
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


def _replace_recommendation_constraints(*, active: bool) -> None:
    mode_expression = (
        "enforcement_mode IN ('SHADOW', 'ENFORCE')"
        if active
        else "enforcement_mode = 'SHADOW'"
    )
    action_expression = (
        "recommended_action IN ('MONITOR', 'CHALLENGE', 'THROTTLE', 'APPLICATION_BLOCK', 'WAF_BLOCK')"
        if active
        else "recommended_action IN ('MONITOR', 'THROTTLE', 'APPLICATION_BLOCK', 'WAF_BLOCK')"
    )
    if _is_sqlite():
        metadata = sa.MetaData()
        recommendation_table = sa.Table(
            "enforcement_recommendations",
            metadata,
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
            sa.Column("enforcement_mode", sa.String(length=16), nullable=False),
            sa.Column("policy_version", sa.String(length=64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
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
                action_expression,
                name="enforcement_recommendations_action_allowed",
            ),
            sa.CheckConstraint(
                mode_expression,
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
            sa.Index(
                "ix_enforcement_recommendations_scope_expires_at",
                "scope",
                "expires_at",
            ),
        )
        with op.batch_alter_table(
            "enforcement_recommendations",
            recreate="always",
            copy_from=recommendation_table,
        ) as batch:
            pass
        return

    op.drop_constraint(
        "enforcement_recommendations_action_allowed",
        "enforcement_recommendations",
        type_="check",
    )
    op.drop_constraint(
        "enforcement_recommendations_mode_allowed",
        "enforcement_recommendations",
        type_="check",
    )
    op.create_check_constraint(
        "enforcement_recommendations_action_allowed",
        "enforcement_recommendations",
        action_expression,
    )
    op.create_check_constraint(
        "enforcement_recommendations_mode_allowed",
        "enforcement_recommendations",
        mode_expression,
    )


def upgrade() -> None:
    _replace_recommendation_constraints(active=True)
    op.create_table(
        "enforcement_request_windows",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("source_ip", sa.String(length=45), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("counter_kind", sa.String(length=32), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "source_ip",
            "scope",
            "counter_kind",
            "policy_version",
            "window_start",
            name="uq_enforcement_request_window_key",
        ),
        sa.CheckConstraint(
            "scope = 'RECORD_SEARCH'",
            name="enforcement_request_windows_scope_allowed",
        ),
        sa.CheckConstraint(
            "counter_kind IN ('LOW_LIGHT', 'MEDIUM_HARD')",
            name="enforcement_request_windows_counter_kind_allowed",
        ),
        sa.CheckConstraint(
            "request_count >= 0",
            name="enforcement_request_windows_count_nonnegative",
        ),
        sa.CheckConstraint(
            "window_end > window_start",
            name="enforcement_request_windows_valid_window",
        ),
        sa.CheckConstraint(
            "length(policy_version) BETWEEN 1 AND 64",
            name="enforcement_request_windows_policy_version_length",
        ),
    )
    op.create_table(
        "enforcement_challenge_grants",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("source_ip", sa.String(length=45), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("enforcement_tier", sa.String(length=10), nullable=False),
        sa.Column("policy_version", sa.String(length=64), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "source_ip",
            "scope",
            "enforcement_tier",
            "policy_version",
            name="uq_enforcement_challenge_grant_key",
        ),
        sa.CheckConstraint(
            "scope = 'RECORD_SEARCH'",
            name="enforcement_challenge_grants_scope_allowed",
        ),
        sa.CheckConstraint(
            "enforcement_tier IN ('LOW', 'MEDIUM')",
            name="enforcement_challenge_grants_tier_allowed",
        ),
        sa.CheckConstraint(
            "expires_at > verified_at",
            name="enforcement_challenge_grants_expiry_after_verification",
        ),
        sa.CheckConstraint(
            "length(policy_version) BETWEEN 1 AND 64",
            name="enforcement_challenge_grants_policy_version_length",
        ),
    )
    _security("enforcement_request_windows")
    _security("enforcement_challenge_grants")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(
        sa.text(
            "SELECT count(*) FROM enforcement_recommendations "
            "WHERE enforcement_mode = 'ENFORCE'"
        )
    ).scalar_one():
        raise RuntimeError(
            "cannot downgrade active enforcement while ENFORCE recommendations exist"
        )
    op.drop_table("enforcement_challenge_grants")
    op.drop_table("enforcement_request_windows")
    _replace_recommendation_constraints(active=False)
