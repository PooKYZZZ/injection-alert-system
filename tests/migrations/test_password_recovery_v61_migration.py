from pathlib import Path


SOURCE = Path('migrations/versions/20260710_000014_password_recovery_v61.py').read_text()


def test_password_recovery_migration_has_atomic_reset_and_admin_mfa_rpc() -> None:
    for function_name in (
        'create_password_reset_token',
        'consume_password_reset_and_change_password',
        'admin_reset_mfa',
        'operator_reset_admin_mfa',
    ):
        assert f'public.{function_name}' in SOURCE
    assert "purpose = 'password_reset'" in SOURCE
    assert "status = 'used'" in SOURCE
    assert "p_actor_account_id = p_target_account_id" in SOURCE


def test_password_recovery_rpc_security_is_fail_closed() -> None:
    assert SOURCE.count('SECURITY INVOKER') == 4
    assert SOURCE.count("SET search_path = ''") == 4
    assert 'REVOKE EXECUTE ON FUNCTION' in SOURCE
