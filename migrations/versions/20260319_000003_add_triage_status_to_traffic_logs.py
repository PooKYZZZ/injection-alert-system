"""Add triage_status column to traffic_logs table.

Revision ID: 20260319_000003
Revises: 20260315_000002
Create Date: 2026-03-19 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260319_000003"
down_revision = "20260315_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add triage_status column for analyst triage workflow."""
    op.add_column(
        "traffic_logs",
        sa.Column(
            "triage_status",
            sa.String(32),
            nullable=True,
            server_default=None,
        ),
    )


def downgrade() -> None:
    """Remove triage_status column."""
    op.drop_column("traffic_logs", "triage_status")
