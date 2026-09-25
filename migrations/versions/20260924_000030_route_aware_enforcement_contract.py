"""Widen enforcement state to the approved public route contract."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260924_000030"
down_revision = "20260905_000029"
branch_labels = None
depends_on = None

_SCOPES = (
    "'RECORD_SEARCH', 'RECORD_DETAIL', 'TRACK_STATUS', "
    "'SUPPORT_SUBMIT', 'APPOINTMENT_SUBMIT', 'COMMENTS_SUBMIT', "
    "'LOGIN_SUBMIT', 'REQUEST_COPY_SUBMIT'"
)
_SCOPE_CHECK = f"scope IN ({_SCOPES})"


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


def _recommendation_table(*, include_route_contract: bool) -> sa.Table:
    metadata = sa.MetaData()
    table = sa.Table(
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
        sa.Column(
            "decision_reason",
            sa.String(length=128),
            nullable=False,
            server_default="LEGACY_POLICY",
        ),
        sa.Column("evidence_context", sa.JSON(), nullable=True),
        sa.UniqueConstraint(
            "trigger_traffic_log_id",
            name="uq_enforcement_recommendations_trigger_traffic_log_id",
        ),
        sa.CheckConstraint(
            _SCOPE_CHECK if include_route_contract else "scope = 'RECORD_SEARCH'",
            name="enforcement_recommendations_scope_allowed",
        ),
        sa.CheckConstraint(
            "enforcement_tier IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="enforcement_recommendations_tier_allowed",
        ),
        sa.CheckConstraint(
            "recommended_action IN ("
            "'MONITOR', 'CHALLENGE', 'THROTTLE', 'APPLICATION_BLOCK', 'WAF_BLOCK'"
            ")",
            name="enforcement_recommendations_action_allowed",
        ),
        sa.CheckConstraint(
            "enforcement_mode IN ('SHADOW', 'ENFORCE')"
            if include_route_contract
            else "enforcement_mode = 'SHADOW'",
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
    return table


def _request_window_table(*, include_route_contract: bool) -> sa.Table:
    metadata = sa.MetaData()
    return sa.Table(
        "enforcement_request_windows",
        metadata,
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
            _SCOPE_CHECK if include_route_contract else "scope = 'RECORD_SEARCH'",
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


def _challenge_grant_table(*, include_route_contract: bool) -> sa.Table:
    metadata = sa.MetaData()
    return sa.Table(
        "enforcement_challenge_grants",
        metadata,
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
            _SCOPE_CHECK if include_route_contract else "scope = 'RECORD_SEARCH'",
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


def _replace_sqlite_tables(*, include_route_contract: bool) -> None:
    with op.batch_alter_table(
        "enforcement_recommendations",
        recreate="always",
        copy_from=_recommendation_table(
            include_route_contract=include_route_contract
        ),
    ):
        pass
    with op.batch_alter_table(
        "enforcement_request_windows",
        recreate="always",
        copy_from=_request_window_table(include_route_contract=include_route_contract),
    ):
        pass
    with op.batch_alter_table(
        "enforcement_challenge_grants",
        recreate="always",
        copy_from=_challenge_grant_table(include_route_contract=include_route_contract),
    ):
        pass


def upgrade() -> None:
    if _is_sqlite():
        op.add_column(
            "enforcement_recommendations",
            sa.Column(
                "decision_reason",
                sa.String(length=128),
                nullable=False,
                server_default="LEGACY_POLICY",
            ),
        )
        op.add_column(
            "enforcement_recommendations",
            sa.Column("evidence_context", sa.JSON(), nullable=True),
        )
        _replace_sqlite_tables(include_route_contract=True)
        return

    op.add_column(
        "enforcement_recommendations",
        sa.Column(
            "decision_reason",
            sa.String(length=128),
            nullable=False,
            server_default="LEGACY_POLICY",
        ),
    )
    op.add_column(
        "enforcement_recommendations",
        sa.Column("evidence_context", sa.JSON(), nullable=True),
    )
    for table_name, constraint_name in (
        (
            "enforcement_recommendations",
            "enforcement_recommendations_scope_allowed",
        ),
        ("enforcement_request_windows", "enforcement_request_windows_scope_allowed"),
        ("enforcement_challenge_grants", "enforcement_challenge_grants_scope_allowed"),
    ):
        op.drop_constraint(constraint_name, table_name, type_="check")
        op.create_check_constraint(constraint_name, table_name, _SCOPE_CHECK)

    _security("enforcement_recommendations")
    _security("enforcement_request_windows")
    _security("enforcement_challenge_grants")


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in (
        "enforcement_recommendations",
        "enforcement_request_windows",
        "enforcement_challenge_grants",
    ):
        if bind.execute(
            sa.text(
                f"SELECT count(*) FROM {table_name} "
                "WHERE scope <> 'RECORD_SEARCH'"
            )
        ).scalar_one():
            raise RuntimeError(
                f"cannot downgrade route-aware enforcement while {table_name} "
                "contains non-search scopes"
            )

    if _is_sqlite():
        _replace_sqlite_tables(include_route_contract=False)
        return

    for table_name, constraint_name in (
        (
            "enforcement_recommendations",
            "enforcement_recommendations_scope_allowed",
        ),
        ("enforcement_request_windows", "enforcement_request_windows_scope_allowed"),
        ("enforcement_challenge_grants", "enforcement_challenge_grants_scope_allowed"),
    ):
        op.drop_constraint(constraint_name, table_name, type_="check")
        op.create_check_constraint(
            constraint_name, table_name, "scope = 'RECORD_SEARCH'"
        )
    op.drop_column("enforcement_recommendations", "evidence_context")
    op.drop_column("enforcement_recommendations", "decision_reason")
