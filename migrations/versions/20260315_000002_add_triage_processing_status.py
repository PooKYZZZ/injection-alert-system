"""Add processing status support for reservation-first triage ingest.

Revision ID: 20260315_000002
Revises: 20260314_000001
Create Date: 2026-03-15 12:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260315_000002"
down_revision = "20260314_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    op.add_column(
        "traffic_logs",
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "traffic_logs",
        sa.Column("status", sa.String(length=16), server_default="COMPLETED", nullable=False),
    )

    if dialect_name == "sqlite":
        with op.batch_alter_table("traffic_logs") as batch_op:
            batch_op.alter_column("prediction", existing_type=sa.String(length=50), nullable=True)
            batch_op.alter_column("confidence", existing_type=sa.Float(), nullable=True)
            batch_op.alter_column("confidence_level", existing_type=sa.String(length=10), nullable=True)
            batch_op.alter_column("action_taken", existing_type=sa.String(length=50), nullable=True)
    else:
        op.alter_column("traffic_logs", "prediction", existing_type=sa.String(length=50), nullable=True)
        op.alter_column("traffic_logs", "confidence", existing_type=sa.Float(), nullable=True)
        op.alter_column("traffic_logs", "confidence_level", existing_type=sa.String(length=10), nullable=True)
        op.alter_column("traffic_logs", "action_taken", existing_type=sa.String(length=50), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "sqlite":
        with op.batch_alter_table("traffic_logs") as batch_op:
            batch_op.alter_column("action_taken", existing_type=sa.String(length=50), nullable=True)
            batch_op.alter_column("confidence_level", existing_type=sa.String(length=10), nullable=False)
            batch_op.alter_column("confidence", existing_type=sa.Float(), nullable=False)
            batch_op.alter_column("prediction", existing_type=sa.String(length=50), nullable=True)
    else:
        op.alter_column("traffic_logs", "action_taken", existing_type=sa.String(length=50), nullable=True)
        op.alter_column("traffic_logs", "confidence_level", existing_type=sa.String(length=10), nullable=False)
        op.alter_column("traffic_logs", "confidence", existing_type=sa.Float(), nullable=False)
        op.alter_column("traffic_logs", "prediction", existing_type=sa.String(length=50), nullable=True)

    op.drop_column("traffic_logs", "status")
    op.drop_column("traffic_logs", "created_at")
