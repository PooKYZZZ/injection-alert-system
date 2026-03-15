"""Add missing traffic_logs columns for prerequisite B.

Revision ID: 20260314_000001
Revises:
Create Date: 2026-03-14 18:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "20260314_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    inspector = inspect(bind)

    if not inspector.has_table("traffic_logs"):
        op.create_table(
            "traffic_logs",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("transaction_id", sa.String(length=128), nullable=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("source_ip", sa.String(length=45), nullable=True),
            sa.Column("request_path", sa.String(length=512), nullable=True),
            sa.Column("request_method", sa.String(length=16), nullable=True),
            sa.Column("http_request", sa.Text(), nullable=False),
            sa.Column("crs_score", sa.Integer(), nullable=True),
            sa.Column("crs_rule_ids", sa.JSON(), nullable=True),
            sa.Column("prediction", sa.String(length=50), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("confidence_level", sa.String(length=10), nullable=False),
            sa.Column("inference_latency_ms", sa.Float(), nullable=True),
            sa.Column("model_version", sa.String(length=50), nullable=True),
            sa.Column("action_taken", sa.String(length=50), nullable=True),
            sa.Column("analyst_label", sa.String(length=50), nullable=True),
            sa.Column("labeled_at", sa.DateTime(), nullable=True),
            sa.Column("labeled_by", sa.String(length=100), nullable=True),
            sa.UniqueConstraint("transaction_id", name="uq_traffic_logs_transaction_id"),
        )
        op.create_index("ix_traffic_logs_id", "traffic_logs", ["id"], unique=False)
        op.create_index("ix_traffic_logs_source_ip", "traffic_logs", ["source_ip"], unique=False)
        op.create_index("ix_traffic_logs_prediction", "traffic_logs", ["prediction"], unique=False)
        return

    op.add_column("traffic_logs", sa.Column("transaction_id", sa.String(length=128), nullable=True))
    op.add_column("traffic_logs", sa.Column("request_path", sa.String(length=512), nullable=True))
    op.add_column("traffic_logs", sa.Column("request_method", sa.String(length=16), nullable=True))
    op.add_column("traffic_logs", sa.Column("crs_score", sa.Integer(), nullable=True))
    op.add_column("traffic_logs", sa.Column("crs_rule_ids", sa.JSON(), nullable=True))
    op.add_column("traffic_logs", sa.Column("inference_latency_ms", sa.Float(), nullable=True))

    if dialect_name == "sqlite":
        with op.batch_alter_table("traffic_logs") as batch_op:
            batch_op.create_unique_constraint(
                "uq_traffic_logs_transaction_id",
                ["transaction_id"],
            )
    else:
        op.create_unique_constraint("uq_traffic_logs_transaction_id", "traffic_logs", ["transaction_id"])


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    inspector = inspect(bind)
    if not inspector.has_table("traffic_logs"):
        return

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("traffic_logs")
        if constraint["name"]
    }
    if "uq_traffic_logs_transaction_id" in unique_constraints:
        if dialect_name == "sqlite":
            with op.batch_alter_table("traffic_logs") as batch_op:
                batch_op.drop_constraint("uq_traffic_logs_transaction_id", type_="unique")
        else:
            op.drop_constraint("uq_traffic_logs_transaction_id", "traffic_logs", type_="unique")

    op.drop_column("traffic_logs", "inference_latency_ms")
    op.drop_column("traffic_logs", "crs_rule_ids")
    op.drop_column("traffic_logs", "crs_score")
    op.drop_column("traffic_logs", "request_method")
    op.drop_column("traffic_logs", "request_path")
    op.drop_column("traffic_logs", "transaction_id")
