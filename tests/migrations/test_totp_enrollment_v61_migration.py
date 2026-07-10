from pathlib import Path


SOURCE = Path('migrations/versions/20260710_000011_totp_enrollment_v61.py').read_text()


def test_totp_migration_has_encrypted_factor_and_backup_lifecycle_fields() -> None:
    for fragment in ('secret_nonce', 'expires_at', 'activated_at', 'revoked_at', 'lookup_prefix'):
        assert fragment in SOURCE
    assert "status IN ('pending', 'active', 'revoked')" in SOURCE
    assert "status = 'revoked'" in SOURCE


def test_totp_migration_has_replay_and_single_use_rpc_contracts() -> None:
    for function_name in (
        'begin_totp_enrollment',
        'activate_totp_factor',
        'consume_totp_step',
        'list_backup_code_candidates',
        'consume_backup_code',
    ):
        assert f'public.{function_name}' in SOURCE
    assert 'last_used_time_step' in SOURCE
    assert 'used_at IS NULL AND revoked_at IS NULL' in SOURCE


def test_totp_rpc_security_is_fail_closed() -> None:
    assert SOURCE.count('SECURITY INVOKER') >= 5
    assert SOURCE.count("SET search_path = ''") >= 5
    assert 'REVOKE EXECUTE ON FUNCTION' in SOURCE
