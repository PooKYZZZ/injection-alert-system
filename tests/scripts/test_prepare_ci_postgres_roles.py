from __future__ import annotations

import pytest

from scripts import prepare_ci_postgres_roles


def test_role_provisioning_refuses_non_ci_environments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")

    with pytest.raises(RuntimeError, match="outside GitHub Actions"):
        prepare_ci_postgres_roles.main()


def test_role_provisioning_requires_testing_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CI", "true")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://unused")

    with pytest.raises(RuntimeError, match="outside APP_ENV=testing"):
        prepare_ci_postgres_roles.main()


def test_ci_role_contract_matches_supabase_runtime_topology() -> None:
    assert set(prepare_ci_postgres_roles.ROLE_ATTRIBUTES) == {
        "anon",
        "authenticated",
        "service_role",
    }
    assert prepare_ci_postgres_roles.ROLE_ATTRIBUTES["service_role"] == (
        "NOLOGIN BYPASSRLS"
    )
