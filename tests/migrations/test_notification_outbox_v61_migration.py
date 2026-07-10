from pathlib import Path


MIGRATION = (
    Path(__file__).parents[2]
    / "migrations"
    / "versions"
    / "20260710_000009_notification_outbox_v61.py"
)


def migration_source() -> str:
    return MIGRATION.read_text(encoding="utf-8").lower()


def test_migration_adds_v61_outbox_contract_without_recreating_table() -> None:
    source = migration_source()

    for required in (
        "kind",
        "template_version",
        "provider_idempotency_key",
        "lease_expires_at",
        "last_error_class",
        "provider_message_id",
        "pending",
        "leased",
        "retry_wait",
        "sent",
        "permanent_failure",
    ):
        assert required in source

    assert "create_table" not in source
    assert "drop_table" not in source


def test_migration_defines_narrow_atomic_outbox_functions() -> None:
    source = migration_source()

    for function in (
        "claim_notification_outbox_batch",
        "complete_notification_outbox_job",
        "fail_notification_outbox_job",
    ):
        assert f"create function public.{function}" in source
        assert f"drop function if exists public.{function}" in source

    assert "for update skip locked" in source
    assert "security invoker" in source
    assert "set search_path = ''" in source
    assert "revoke execute" in source
    assert "from public" in source
    assert "from anon" in source
    assert "from authenticated" in source
    assert "to service_role" in source


def test_migration_recovers_legacy_leases_and_completes_only_by_owner() -> None:
    source = migration_source()

    assert "lease_expires_at = clock_timestamp()" in source
    completion = source.split(
        "create function public.complete_notification_outbox_job", 1
    )[1].split("create function public.fail_notification_outbox_job", 1)[0]
    assert "locked_by = p_worker_id" in completion
    assert "lease_expires_at > clock_timestamp()" not in completion
