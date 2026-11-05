from pathlib import Path


SOURCE = Path(
    'migrations/versions/20261105_000034_auth_login_throttle.py'
).read_text()


def test_login_throttle_migration_bounds_state_by_canonical_account() -> None:
    assert 'auth_login_throttle_state' in SOURCE
    assert 'auth_login_attempt_reservations' in SOURCE
    assert 'sa.ForeignKey("auth_accounts.id", ondelete="CASCADE")' in SOURCE
    assert 'expires_at' in SOURCE
    assert 'FOR UPDATE' in SOURCE
    assert 'SECURITY INVOKER' in SOURCE
    assert "SET search_path = ''" in SOURCE


def test_login_throttle_rpc_grants_and_downgrade_are_restricted() -> None:
    for function_name in (
        'begin_auth_login_attempt_v1',
        'complete_auth_login_attempt_v1',
    ):
        assert f'public.{function_name}' in SOURCE
    assert SOURCE.count('REVOKE EXECUTE ON FUNCTION') >= 2
    assert 'FROM PUBLIC' in SOURCE
    assert 'FROM anon' in SOURCE
    assert 'FROM authenticated' in SOURCE
    assert 'TO service_role' in SOURCE
    assert 'op.drop_table("auth_login_attempt_reservations")' in SOURCE
    assert 'op.drop_table("auth_login_throttle_state")' in SOURCE
