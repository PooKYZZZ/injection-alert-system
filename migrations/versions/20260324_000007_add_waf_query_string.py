"""Add query string storage for WAF ingest events.

Revision ID: 20260324_000007
Revises: 20260324_000006
Create Date: 2026-03-24 12:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "20260324_000007"
down_revision = "20260324_000006"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str] | None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        return None
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    existing = _column_names("traffic_logs")
    if existing is None:
        raise RuntimeError(
            "traffic_logs must exist before applying revision 20260324_000007"
        )
    if "query_string" in existing:
        return

    op.add_column(
        "traffic_logs",
        sa.Column("query_string", sa.String(length=4096), nullable=True),
    )


def downgrade() -> None:
    existing = _column_names("traffic_logs")
    if existing and "query_string" in existing:
        op.drop_column("traffic_logs", "query_string")
