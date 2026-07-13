from pathlib import Path


SOURCE = Path('migrations/versions/20260710_000013_mfa_recovery_v61.py').read_text()


def test_recovery_migration_has_atomic_backup_and_email_paths() -> None:
    for function_name in (
        'consume_backup_code_for_recovery',
        'begin_email_recovery_challenge',
        'consume_email_otp_for_recovery',
        'consume_mfa_recovery_completion_token',
    ):
        assert f'public.{function_name}' in SOURCE
    assert "status = 'revoked'" in SOURCE
    assert 'max_attempts' in SOURCE


def test_recovery_migration_locks_and_restricts_security_transitions() -> None:
    assert 'FOR UPDATE' in SOURCE
    assert SOURCE.count('SECURITY INVOKER') == 4
    assert SOURCE.count("SET search_path = ''") == 4
    assert 'REVOKE EXECUTE ON FUNCTION' in SOURCE
