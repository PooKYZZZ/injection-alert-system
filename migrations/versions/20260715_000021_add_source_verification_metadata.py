"""Add authoritative source verification metadata to traffic logs."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260715_000021"
down_revision = "20260712_000020"
branch_labels = None
depends_on = None


CHECKS = (
    (
        "source_provenance_allowed",
        "source_provenance IN ('CLOUDFLARE_CONNECTING_IP', 'DIRECT_REMOTE_ADDR', 'LEGACY_UNKNOWN')",
    ),
    (
        "source_verification_status_allowed",
        "source_verification_status IN ('VERIFIED', 'UNVERIFIED', 'INVALID', 'LEGACY_UNKNOWN')",
    ),
    (
        "verified_source_ip_present",
        "source_verification_status <> 'VERIFIED' OR source_ip IS NOT NULL",
    ),
    (
        "invalid_source_ip_absent",
        "source_verification_status <> 'INVALID' OR source_ip IS NULL",
    ),
    (
        "legacy_source_metadata_paired",
        "(source_provenance = 'LEGACY_UNKNOWN') = (source_verification_status = 'LEGACY_UNKNOWN')",
    ),
    (
        "verified_source_not_legacy",
        "source_verification_status <> 'VERIFIED' OR source_provenance <> 'LEGACY_UNKNOWN'",
    ),
    (
        "missing_source_status_valid",
        "source_ip IS NOT NULL OR source_verification_status IN ('INVALID', 'LEGACY_UNKNOWN')",
    ),
    (
        "ingest_fingerprint_length",
        "ingest_fingerprint_sha256 IS NULL OR length(ingest_fingerprint_sha256) = 64",
    ),
)


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def _make_source_columns_non_nullable() -> None:
    if _is_sqlite():
        with op.batch_alter_table("traffic_logs", recreate="always") as batch_op:
            batch_op.alter_column(
                "source_provenance",
                existing_type=sa.String(length=32),
                nullable=False,
                server_default=None,
            )
            batch_op.alter_column(
                "source_verification_status",
                existing_type=sa.String(length=32),
                nullable=False,
                server_default=None,
            )
            for name, condition in CHECKS:
                batch_op.create_check_constraint(name, condition)
        return

    op.alter_column(
        "traffic_logs",
        "source_provenance",
        existing_type=sa.String(length=32),
        nullable=False,
        server_default=None,
    )
    op.alter_column(
        "traffic_logs",
        "source_verification_status",
        existing_type=sa.String(length=32),
        nullable=False,
        server_default=None,
    )
    for name, condition in CHECKS:
        op.create_check_constraint(name, "traffic_logs", condition)


def upgrade() -> None:
    op.add_column(
        "traffic_logs",
        sa.Column(
            "source_provenance",
            sa.String(length=32),
            nullable=True,
            server_default="LEGACY_UNKNOWN",
        ),
    )
    op.add_column(
        "traffic_logs",
        sa.Column(
            "source_verification_status",
            sa.String(length=32),
            nullable=True,
            server_default="LEGACY_UNKNOWN",
        ),
    )
    op.add_column(
        "traffic_logs",
        sa.Column("ingest_fingerprint_sha256", sa.String(length=64), nullable=True),
    )

    op.execute(
        sa.text(
            """
UPDATE traffic_logs
SET source_provenance = 'LEGACY_UNKNOWN',
    source_verification_status = 'LEGACY_UNKNOWN'
WHERE source_provenance IS NULL
   OR source_verification_status IS NULL
"""
        )
    )
    _make_source_columns_non_nullable()


def downgrade() -> None:
    if _is_sqlite():
        with op.batch_alter_table("traffic_logs", recreate="always") as batch_op:
            for name, _condition in reversed(CHECKS):
                batch_op.drop_constraint(name, type_="check")
            batch_op.drop_column("ingest_fingerprint_sha256")
            batch_op.drop_column("source_verification_status")
            batch_op.drop_column("source_provenance")
        return

    for name, _condition in reversed(CHECKS):
        op.drop_constraint(name, "traffic_logs", type_="check")
    op.drop_column("traffic_logs", "ingest_fingerprint_sha256")
    op.drop_column("traffic_logs", "source_verification_status")
    op.drop_column("traffic_logs", "source_provenance")
