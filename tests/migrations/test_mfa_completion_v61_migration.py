from pathlib import Path


SOURCE = Path('migrations/versions/20260710_000012_mfa_completion_v61.py').read_text()


def test_completion_migration_adds_bound_challenge_fields() -> None:
    for fragment in ('purpose', 'preauth_handle_hash', 'verified_method', 'completion_token_hash', 'consumed_at'):
        assert fragment in SOURCE
    assert "status IN ('pending', 'verified', 'consumed', 'expired', 'locked')" in SOURCE


def test_completion_migration_has_single_use_rpc_contracts() -> None:
    for function_name in (
        'begin_login_mfa_challenge',
        'verify_totp_and_issue_completion',
        'consume_mfa_completion_token',
    ):
        assert f'public.{function_name}' in SOURCE
    assert 'FOR UPDATE' in SOURCE
    assert "status = 'used'" in SOURCE


def test_completion_rpc_security_is_fail_closed() -> None:
    assert SOURCE.count('SECURITY INVOKER') == 3
    assert SOURCE.count("SET search_path = ''") == 3
    assert 'REVOKE EXECUTE ON FUNCTION' in SOURCE
