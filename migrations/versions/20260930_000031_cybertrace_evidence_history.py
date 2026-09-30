"""Store request evidence outcomes and analyst action history."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260930_000031"
down_revision = "20260924_000030"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def _has_column(table: str, column: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return inspector.has_table(table) and column in {
        item["name"] for item in inspector.get_columns(table)
    }


def _secure_action_history_table() -> None:
    if _is_sqlite():
        return
    op.execute(
        sa.text(
            "ALTER TABLE public.traffic_log_action_history ENABLE ROW LEVEL SECURITY"
        )
    )
    op.execute(
        sa.text("REVOKE ALL ON TABLE public.traffic_log_action_history FROM PUBLIC")
    )
    op.execute(
        sa.text(
            """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.traffic_log_action_history FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.traffic_log_action_history FROM authenticated';
  END IF;
END
$$
"""
        )
    )


def _refuse_informational_tier_downgrade() -> None:
    bind = op.get_bind()
    for table, column in (
        ("traffic_logs", "confidence_level"),
        ("traffic_label_reviews", "prediction_confidence_level"),
    ):
        if not _has_column(table, column):
            continue
        count = bind.execute(
            sa.text(
                f"SELECT COUNT(*) FROM {table} WHERE {column} = 'INFORMATIONAL'"
            )
        ).scalar_one()
        if count:
            raise RuntimeError(
                "Cannot downgrade confidence columns while INFORMATIONAL "
                "values are stored; preserve the data or migrate it explicitly first."
            )


def upgrade() -> None:
    with op.batch_alter_table("traffic_logs") as batch_op:
        if _has_column("traffic_logs", "confidence_level"):
            batch_op.alter_column(
                "confidence_level",
                existing_type=sa.String(length=10),
                type_=sa.String(length=13),
                existing_nullable=True,
            )
        batch_op.add_column(sa.Column("request_correlation_id", sa.String(64)))
        batch_op.add_column(sa.Column("observed_http_status", sa.SmallInteger()))
        batch_op.create_check_constraint(
            "request_correlation_id_length",
            "request_correlation_id IS NULL OR length(request_correlation_id) BETWEEN 1 AND 64",
        )
        batch_op.create_check_constraint(
            "observed_http_status_range",
            "observed_http_status IS NULL OR observed_http_status BETWEEN 100 AND 599",
        )

    if _has_column("traffic_label_reviews", "prediction_confidence_level"):
        with op.batch_alter_table("traffic_label_reviews") as batch_op:
            batch_op.alter_column(
                "prediction_confidence_level",
                existing_type=sa.String(length=10),
                type_=sa.String(length=13),
                existing_nullable=True,
            )

    op.create_index(
        "ix_traffic_logs_request_correlation_id",
        "traffic_logs",
        ["request_correlation_id"],
    )
    op.create_table(
        "traffic_log_action_history",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "traffic_log_id",
            sa.Integer(),
            sa.ForeignKey("traffic_logs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("previous_action", sa.String(length=50), nullable=True),
        sa.Column("new_action", sa.String(length=50), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.String(length=1000), nullable=True),
        sa.CheckConstraint(
            "previous_action IS NULL OR previous_action IN ('BLOCKED', 'THROTTLED', 'ALLOWED')",
            name="previous_action_allowed",
        ),
        sa.CheckConstraint(
            "new_action IN ('BLOCKED', 'THROTTLED', 'ALLOWED')",
            name="new_action_allowed",
        ),
    )
    op.create_index(
        "ix_traffic_log_action_history_alert_changed_at",
        "traffic_log_action_history",
        ["traffic_log_id", "changed_at"],
    )
    _secure_action_history_table()


def downgrade() -> None:
    _refuse_informational_tier_downgrade()
    op.drop_index(
        "ix_traffic_log_action_history_alert_changed_at",
        table_name="traffic_log_action_history",
    )
    op.drop_table("traffic_log_action_history")
    op.drop_index("ix_traffic_logs_request_correlation_id", table_name="traffic_logs")
    with op.batch_alter_table("traffic_logs") as batch_op:
        batch_op.drop_constraint("request_correlation_id_length", type_="check")
        batch_op.drop_constraint("observed_http_status_range", type_="check")
        batch_op.drop_column("observed_http_status")
        batch_op.drop_column("request_correlation_id")
        batch_op.alter_column(
            "confidence_level",
            existing_type=sa.String(length=13),
            type_=sa.String(length=10),
            existing_nullable=True,
        )
    if _has_column("traffic_label_reviews", "prediction_confidence_level"):
        with op.batch_alter_table("traffic_label_reviews") as batch_op:
            batch_op.alter_column(
                "prediction_confidence_level",
                existing_type=sa.String(length=13),
                type_=sa.String(length=10),
                existing_nullable=True,
            )
