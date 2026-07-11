from __future__ import annotations

import pytest

from web_app.notifications.outbox import (
    LeaseLostError,
    PostgresNotificationOutboxRepository,
    build_threat_notification,
)


class ResultStub:
    def __init__(self, rows=None, scalar=True) -> None:
        self._rows = rows or []
        self._scalar = scalar

    def mappings(self):
        return self

    def all(self):
        return self._rows

    def scalar_one(self):
        return self._scalar


class SessionStub:
    def __init__(self, results) -> None:
        self.results = list(results)
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return None

    def begin(self):
        return self

    async def execute(self, statement, params):
        self.calls.append((str(statement), params))
        return self.results.pop(0)


@pytest.mark.asyncio
async def test_repository_maps_claimed_rows_and_uses_narrow_rpc() -> None:
    session = SessionStub(
        [
            ResultStub(
                [
                    {
                        "id": "job-1",
                        "kind": "password_changed",
                        "recipient": "owner@example.test",
                        "payload_safe_json": {},
                        "template_version": 1,
                        "dedupe_key": "password-changed/account-1/v2",
                        "provider_idempotency_key": "password-changed/account-1/v2",
                        "attempts": 1,
                        "max_attempts": 5,
                    }
                ]
            )
        ]
    )
    repository = PostgresNotificationOutboxRepository(lambda: session)

    jobs = await repository.claim_batch("worker-a", 10, 60)

    assert jobs[0].id == "job-1"
    assert jobs[0].attempt_count == 1
    assert "claim_notification_outbox_batch_v61" in session.calls[0][0]
    assert session.calls[0][1] == {
        "worker_id": "worker-a",
        "batch_size": 10,
        "lease_seconds": 60,
    }


@pytest.mark.asyncio
async def test_repository_rejects_lost_lease_on_completion() -> None:
    session = SessionStub([ResultStub(scalar=False)])
    repository = PostgresNotificationOutboxRepository(lambda: session)

    with pytest.raises(LeaseLostError):
        await repository.complete("job-1", "worker-a", "provider-1")


def test_build_threat_notification_excludes_query_and_raw_request_data() -> None:
    notification = build_threat_notification(
        alert_id=42,
        timestamp="2026-07-10T09:00:00Z",
        attack_category="SQL Injection",
        confidence_tier="CRITICAL",
        action_taken="BLOCKED",
        request_path="/records/search?secret=raw",
        dashboard_base_url="https://dashboard.example.test",
        recipient="soc@example.test",
    )

    assert notification.safe_payload["route_path"] == "/records/search"
    assert "query_string" not in notification.safe_payload
    assert "raw" not in notification.safe_payload
    assert notification.dedupe_key == "threat/42"
    assert notification.provider_idempotency_key == "threat/42"
