from __future__ import annotations

from pathlib import Path


MIGRATION = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260711_000017_step_up_recovery_enrollment_v61.py"
)


def test_step_up_migration_has_distinct_purpose_functions() -> None:
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'revision = "20260711_000017"' in source
    assert 'down_revision = "20260711_000016"' in source
    assert "begin_recent_totp_challenge_v61" in source
    assert "record_recent_totp_attempt_v61" in source
    assert "begin_recovery_totp_enrollment_v61" in source
    assert "recent_reauthentication" in source
    assert source.count("SECURITY INVOKER") >= 3
    assert source.count("SET search_path = ''") >= 3
