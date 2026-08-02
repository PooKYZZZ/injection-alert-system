"""Add append-only verified traffic label review revisions."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260802_000026"
down_revision = "20260728_000025"
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
    op.execute(sa.text("REVOKE ALL ON TABLE public.traffic_label_reviews FROM PUBLIC"))
    op.execute(
        sa.text(
            """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.traffic_label_reviews FROM anon';
  END IF;
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    EXECUTE 'REVOKE ALL ON TABLE public.traffic_label_reviews FROM authenticated';
  END IF;
END
$$
"""
        )
    )


def upgrade() -> None:
    op.create_table(
        "traffic_label_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "traffic_log_id",
            sa.Integer(),
            sa.ForeignKey("traffic_logs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("predicted_label", sa.String(length=50), nullable=True),
        sa.Column("verified_label", sa.String(length=50), nullable=False),
        sa.Column("approval_state", sa.String(length=32), nullable=False),
        sa.Column("reviewer_id", sa.String(length=128), nullable=False),
        sa.Column("reviewer_role", sa.String(length=32), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("model_version", sa.String(length=100), nullable=True),
        sa.Column("input_hash", sa.String(length=64), nullable=True),
        sa.Column("review_note", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("traffic_log_id", "revision", name="uq_traffic_label_review_revision"),
        sa.CheckConstraint(
            "verified_label IN ('Normal', 'SQL Injection', 'Code Injection', 'Other Attacks')",
            name="traffic_label_review_verified_label_allowed",
        ),
        sa.CheckConstraint(
            "approval_state IN ('approved_for_training', 'excluded_from_training', 'superseded')",
            name="traffic_label_review_approval_state_allowed",
        ),
        sa.CheckConstraint("revision >= 1", name="traffic_label_review_revision_positive"),
    )
    op.create_index(
        "ix_traffic_label_reviews_traffic_log_revision",
        "traffic_label_reviews",
        ["traffic_log_id", "revision"],
    )
    op.create_index(
        "ix_traffic_label_reviews_approval_state",
        "traffic_label_reviews",
        ["approval_state"],
    )
    _security()


def downgrade() -> None:
    op.drop_index(
        "ix_traffic_label_reviews_approval_state", table_name="traffic_label_reviews"
    )
    op.drop_index(
        "ix_traffic_label_reviews_traffic_log_revision",
        table_name="traffic_label_reviews",
    )
    op.drop_table("traffic_label_reviews")
