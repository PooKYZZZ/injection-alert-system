"""Add triage lease ownership fields.

Revision ID: 20260322_000004
Revises: 20260319_000003
Create Date: 2026-03-22 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260322_000004"
down_revision = "20260319_000003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "traffic_logs",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "traffic_logs",
        sa.Column("processing_owner_token", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "traffic_logs",
        sa.Column(
            "processing_attempt",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("traffic_logs", "processing_attempt")
    op.drop_column("traffic_logs", "processing_owner_token")
    op.drop_column("traffic_logs", "lease_expires_at")
