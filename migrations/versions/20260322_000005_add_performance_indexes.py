"""Add performance indexes for query optimization.

Revision ID: 20260322_000005
Revises: 20260322_000004
Create Date: 2026-03-22 00:00:00
"""

from __future__ import annotations

from alembic import op


revision = "20260322_000005"
down_revision = "20260322_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_traffic_logs_confidence_level",
        "traffic_logs",
        ["confidence_level"],
    )
    op.create_index(
        "ix_traffic_logs_triage_status",
        "traffic_logs",
        ["triage_status"],
    )
    op.create_index(
        "ix_traffic_logs_action_taken",
        "traffic_logs",
        ["action_taken"],
    )
    op.create_index(
        "ix_traffic_logs_source_ip",
        "traffic_logs",
        ["source_ip"],
    )
    op.create_index(
        "ix_traffic_logs_prediction",
        "traffic_logs",
        ["prediction"],
    )
    op.create_index(
        "ix_traffic_logs_status_timestamp",
        "traffic_logs",
        ["status", "timestamp"],
    )
    op.create_index(
        "ix_traffic_logs_lease_expires_at",
        "traffic_logs",
        ["lease_expires_at"],
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_traffic_logs_timestamp_brin ON traffic_logs USING brin (timestamp)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_traffic_logs_timestamp_brin")
    op.drop_index("ix_traffic_logs_lease_expires_at", table_name="traffic_logs")
    op.drop_index("ix_traffic_logs_status_timestamp", table_name="traffic_logs")
    op.drop_index("ix_traffic_logs_prediction", table_name="traffic_logs")
    op.drop_index("ix_traffic_logs_source_ip", table_name="traffic_logs")
    op.drop_index("ix_traffic_logs_action_taken", table_name="traffic_logs")
    op.drop_index("ix_traffic_logs_triage_status", table_name="traffic_logs")
    op.drop_index("ix_traffic_logs_confidence_level", table_name="traffic_logs")
