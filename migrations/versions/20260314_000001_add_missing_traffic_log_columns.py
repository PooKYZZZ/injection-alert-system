"""Add missing traffic_logs columns for prerequisite B.

Revision ID: 20260314_000001
Revises:
Create Date: 2026-03-14 18:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260314_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.add_column("traffic_logs", sa.Column("transaction_id", sa.String(length=128), nullable=True))
    op.add_column("traffic_logs", sa.Column("request_path", sa.String(length=512), nullable=True))
    op.add_column("traffic_logs", sa.Column("request_method", sa.String(length=16), nullable=True))
    op.add_column("traffic_logs", sa.Column("crs_score", sa.Integer(), nullable=True))
    op.add_column("traffic_logs", sa.Column("crs_rule_ids", sa.JSON(), nullable=True))
    op.add_column("traffic_logs", sa.Column("inference_latency_ms", sa.Float(), nullable=True))

    if dialect_name == "sqlite":
        op.create_index(
            "uq_traffic_logs_transaction_id",
            "traffic_logs",
            ["transaction_id"],
            unique=True,
        )
    else:
        op.create_unique_constraint("uq_traffic_logs_transaction_id", "traffic_logs", ["transaction_id"])


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "sqlite":
        op.drop_index("uq_traffic_logs_transaction_id", table_name="traffic_logs")
    else:
        op.drop_constraint("uq_traffic_logs_transaction_id", "traffic_logs", type_="unique")

    op.drop_column("traffic_logs", "inference_latency_ms")
    op.drop_column("traffic_logs", "crs_rule_ids")
    op.drop_column("traffic_logs", "crs_score")
    op.drop_column("traffic_logs", "request_method")
    op.drop_column("traffic_logs", "request_path")
    op.drop_column("traffic_logs", "transaction_id")
