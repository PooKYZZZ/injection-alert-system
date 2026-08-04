"""Add exact model-input and immutable label-review provenance snapshots."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260802_000027"
down_revision = "20260802_000026"
branch_labels = None
depends_on = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def _security() -> None:
    if _is_sqlite():
        return
    op.execute(
        sa.text("ALTER TABLE public.traffic_label_reviews ENABLE ROW LEVEL SECURITY")
    )
    op.execute(
        sa.text("REVOKE ALL ON TABLE public.traffic_label_reviews FROM PUBLIC")
    )


def upgrade() -> None:
    op.add_column(
        "traffic_logs",
        sa.Column("model_input_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "traffic_logs",
        sa.Column("preprocessing_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "traffic_label_reviews",
        sa.Column("prediction_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "traffic_label_reviews",
        sa.Column("prediction_confidence_level", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "traffic_label_reviews",
        sa.Column("model_input_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "traffic_label_reviews",
        sa.Column("preprocessing_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "traffic_label_reviews",
        sa.Column("ingest_event_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "traffic_label_reviews",
        sa.Column("source_verification_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "traffic_label_reviews",
        sa.Column("source_provenance", sa.String(length=32), nullable=True),
    )
    _security()


def downgrade() -> None:
    op.drop_column("traffic_label_reviews", "source_provenance")
    op.drop_column("traffic_label_reviews", "source_verification_status")
    op.drop_column("traffic_label_reviews", "ingest_event_hash")
    op.drop_column("traffic_label_reviews", "preprocessing_version")
    op.drop_column("traffic_label_reviews", "model_input_hash")
    op.drop_column("traffic_label_reviews", "prediction_confidence_level")
    op.drop_column("traffic_label_reviews", "prediction_confidence")
    op.drop_column("traffic_logs", "preprocessing_version")
    op.drop_column("traffic_logs", "model_input_hash")
