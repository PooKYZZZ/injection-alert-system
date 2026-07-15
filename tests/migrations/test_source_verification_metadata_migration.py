from pathlib import Path


MIGRATION = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260715_000021_add_source_verification_metadata.py"
)


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def test_migration_follows_current_single_head() -> None:
    source = migration_source()
    assert 'revision = "20260715_000021"' in source
    assert 'down_revision = "20260712_000020"' in source


def test_upgrade_backfills_legacy_metadata_then_drops_defaults() -> None:
    source = migration_source()
    upgrade = source.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]

    assert '"source_provenance"' in upgrade
    assert '"source_verification_status"' in upgrade
    assert '"ingest_fingerprint_sha256"' in upgrade
    assert "LEGACY_UNKNOWN" in upgrade
    assert "nullable=False" in upgrade
    assert "server_default=None" in upgrade


def test_upgrade_defines_all_named_checks_and_no_fingerprint_index() -> None:
    source = migration_source()
    upgrade = source.split("def upgrade()", 1)[1].split("def downgrade()", 1)[0]

    for name in (
        "source_provenance_allowed",
        "source_verification_status_allowed",
        "verified_source_ip_present",
        "invalid_source_ip_absent",
        "legacy_source_metadata_paired",
        "verified_source_not_legacy",
        "missing_source_status_valid",
        "ingest_fingerprint_length",
    ):
        assert name in source

    assert "create_index" not in upgrade
    assert "length(ingest_fingerprint_sha256) = 64" in source


def test_downgrade_removes_only_added_constraints_and_columns() -> None:
    source = migration_source()
    downgrade = source.split("def downgrade()", 1)[1]

    assert "reversed(CHECKS)" in downgrade
    assert "op.drop_constraint(name, \"traffic_logs\", type_=\"check\")" in downgrade
    assert downgrade.count("op.drop_column(") == 3
    assert "drop_table" not in downgrade
