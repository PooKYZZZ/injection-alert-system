"""Add WAF ingest metadata columns to traffic_logs.

Revision ID: 20260324_000006
Revises: 20260322_000005
Create Date: 2026-03-24 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260324_000006"
down_revision = "20260322_000005"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    existing = _column_names("traffic_logs")
    if not existing:
        return

    if "ingest_source" not in existing:
        op.add_column(
            "traffic_logs",
            sa.Column("ingest_source", sa.String(length=64), nullable=True),
        )
    if "matched_rule_messages" not in existing:
        op.add_column(
            "traffic_logs",
            sa.Column("matched_rule_messages", sa.JSON(), nullable=True),
        )
    if "matched_rule_tags" not in existing:
        op.add_column(
            "traffic_logs",
            sa.Column("matched_rule_tags", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    existing = _column_names("traffic_logs")
    if not existing:
        return

    if "matched_rule_tags" in existing:
        op.drop_column("traffic_logs", "matched_rule_tags")
    if "matched_rule_messages" in existing:
        op.drop_column("traffic_logs", "matched_rule_messages")
    if "ingest_source" in existing:
        op.drop_column("traffic_logs", "ingest_source")
