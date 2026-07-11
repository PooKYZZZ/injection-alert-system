from pathlib import Path


SOURCE = Path(
    "migrations/versions/20260711_000015_auth_state_hardening_v61.py"
).read_text(encoding="utf-8")


def test_auth_hardening_migration_is_additive_and_purpose_bound() -> None:
    assert 'down_revision = "20260710_000014"' in SOURCE
    assert "create_table" not in SOURCE
    for function_name in (
        "begin_mfa_challenge_v61",
        "mfa_enrollment_challenge_available_v61",
        "record_totp_attempt_v61",
        "complete_totp_enrollment_v61",
        "consume_mfa_completion_token_v61",
        "consume_mfa_recovery_completion_token_v61",
        "preflight_password_token_v61",
    ):
        assert f"CREATE FUNCTION public.{function_name}" in SOURCE
    assert "purpose = 'mfa_recovery'" in SOURCE
    assert "verified_method = 'totp'" in SOURCE
    assert "auth_level text" in SOURCE
    assert "verified_at timestamptz" in SOURCE


def test_auth_hardening_migration_commits_invalid_attempts_and_limits_retries() -> None:
    assert "attempt_count = v_attempt" in SOURCE
    assert "status = CASE WHEN v_attempt >= v_max_attempts" in SOURCE
    assert "handoff_attempts BETWEEN 0 AND 2" in SOURCE
    assert "retry_until" in SOURCE
    assert "FOR UPDATE OF" in SOURCE
    assert SOURCE.count("SECURITY INVOKER") == 11
    assert SOURCE.count("SET search_path = ''") == 11
    assert "REVOKE EXECUTE ON FUNCTION" in SOURCE
