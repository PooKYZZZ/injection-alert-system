"""Add performance indexes for query optimization.

Revision ID: 20260322_000005
Revises: 20260322_000004
Create Date: 2026-03-22 00:00:00
"""

from __future__ import annotations

from alembic import op
from sqlalchemy import text


revision = "20260322_000005"
down_revision = "20260322_000004"
branch_labels = None
depends_on = None


def _is_postgres() -> bool:
    """Check if the current database dialect is PostgreSQL."""
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_traffic_logs_confidence_level ON traffic_logs (confidence_level)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_traffic_logs_triage_status ON traffic_logs (triage_status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_traffic_logs_action_taken ON traffic_logs (action_taken)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_traffic_logs_source_ip ON traffic_logs (source_ip)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_traffic_logs_prediction ON traffic_logs (prediction)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_traffic_logs_status_timestamp ON traffic_logs (status, timestamp)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_traffic_logs_lease_expires_at ON traffic_logs (lease_expires_at)"
    )
    if _is_postgres():
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_traffic_logs_timestamp_brin ON traffic_logs USING brin (timestamp)"
        )


def downgrade() -> None:
    if _is_postgres():
        op.execute("DROP INDEX IF EXISTS ix_traffic_logs_timestamp_brin")
    op.execute("DROP INDEX IF EXISTS ix_traffic_logs_lease_expires_at")
    op.execute("DROP INDEX IF EXISTS ix_traffic_logs_status_timestamp")
    op.execute("DROP INDEX IF EXISTS ix_traffic_logs_prediction")
    op.execute("DROP INDEX IF EXISTS ix_traffic_logs_source_ip")
    op.execute("DROP INDEX IF EXISTS ix_traffic_logs_action_taken")
    op.execute("DROP INDEX IF EXISTS ix_traffic_logs_triage_status")
    op.execute("DROP INDEX IF EXISTS ix_traffic_logs_confidence_level")
