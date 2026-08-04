"""Persist the exact sanitized model input used for inference."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260803_000028"
down_revision = "20260802_000027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "traffic_logs",
        sa.Column("model_input_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "traffic_label_reviews",
        sa.Column("model_input_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("traffic_label_reviews", "model_input_text")
    op.drop_column("traffic_logs", "model_input_text")
