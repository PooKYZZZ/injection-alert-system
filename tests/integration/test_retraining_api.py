from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import web_app.presentation.api.retraining_router as retraining_router_module
from ml_model.retraining.dashboard_contracts import RunState
from web_app.application.retraining_run_use_case import RetrainingStartResult
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    RetrainingRunRecord,
)
from web_app.presentation.api.retraining_router import (
    get_retraining_control_use_case,
    router,
)
from web_app.presentation.dependencies import auth as auth_dependencies
from web_app.presentation.dependencies import retraining as retraining_dependencies

NOW = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
RUN_ID = "retrain-20260811T120000Z-000000000001"
API_KEY = "internal-api-key"


def _record(state: RunState = RunState.QUEUED) -> RetrainingRunRecord:
    return RetrainingRunRecord(
        run_id=RUN_ID,
        state=state,
        stage=state.value,
        attempt=0,
        retry_count=0,
        max_retries=2,
        created_at=NOW,
        updated_at=NOW,
        heartbeat_at=None,
        trigger="manual",
        requested_by="analyst-1",
        requested_timezone="Asia/Manila",
        input_fingerprint="a" * 64,
        source_review_revisions=("1:1",),
        source_dataset_version="v3_907k_cleaned",
        source_dataset_digest="b" * 64,
        pipeline_fingerprint="c" * 64,
        active_model_version="active-v1",
        active_model_digest="d" * 64,
        approved_sample_count=2,
    )


class FakeControlPlane:
    def __init__(self) -> None:
        self.start_calls: list[dict[str, object]] = []
        self.decision_calls: list[dict[str, object]] = []
        self.retry_calls: list[dict[str, object]] = []
        self.start_count = 0

    async def get_summary(self):
        from web_app.application.retraining_control_use_case import (
            RetrainingSummarySnapshot,
        )

        return RetrainingSummarySnapshot(
            active_model_version="active-v1",
            latest_run_state="queued",
            approved_count=2,
            unreviewed_count=3,
            excluded_count=1,
            latest_dataset_version=None,
            run_in_progress=True,
            last_trigger_time=NOW,
        )

    async def start_run(self, **kwargs):
        self.start_calls.append(kwargs)
        self.start_count += 1
        return RetrainingStartResult(run=_record(), created=self.start_count == 1)

    def list_runs(self):
        return [_record()]

    def retry_run(self, **kwargs):
        self.retry_calls.append(kwargs)
        return _record(RunState.QUEUED)

    def get_run_detail(self, _run_id):
        from web_app.application.retraining_control_use_case import (
            RetrainingRunDetail,
        )

        return RetrainingRunDetail(
            record=_record(),
            events=(
                {
                    "created_at": "2026-08-11T12:00:00Z",
                    "stage": "queued",
                    "outcome": "INFO",
                    "code": "RUN_QUEUED",
                    "message": "run accepted",
                },
            ),
            evidence_status="NOT_RUN",
            heartbeat_age_seconds=None,
            retry_available=False,
        )

    def decide(self, **kwargs):
        self.decision_calls.append(kwargs)
        return SimpleNamespace(run=_record(RunState.HELD), decision="hold")

    def deploy(self, **_kwargs):
        from web_app.application.retraining_control_use_case import (
            RetrainingControlError,
        )

        raise RetrainingControlError(
            "DEPLOYMENT_NOT_AVAILABLE", "Deployment is not available.", status_code=501
        )

    def rollback(self, **_kwargs):
        from web_app.application.retraining_control_use_case import (
            RetrainingControlError,
        )

        raise RetrainingControlError(
            "ROLLBACK_NOT_AVAILABLE", "Rollback is not available.", status_code=501
        )


@pytest.fixture
def client(monkeypatch):
    settings = SimpleNamespace(
        app_env="testing",
        is_development=False,
        is_testing=True,
        is_production=False,
        is_staging=False,
        api_secret_key=API_KEY,
        retraining_enabled=True,
    )
    monkeypatch.setattr(auth_dependencies, "get_settings", lambda: settings)

    app = FastAPI()
    app.include_router(router, prefix="/api")
    control = FakeControlPlane()
    app.dependency_overrides[get_retraining_control_use_case] = lambda: control
    settings_dependency = retraining_dependencies.get_retraining_settings
    app.dependency_overrides[settings_dependency] = lambda: settings
    with TestClient(app) as test_client:
        yield test_client, control


def _headers(*, role: str = "ANALYST", actor: str = "analyst-1"):
    return {
        "Authorization": f"Bearer {API_KEY}",
        "X-Reviewer-Id": actor,
        "X-Reviewer-Role": role,
    }


def test_internal_retraining_routes_require_api_key(client):
    test_client, control = client

    response = test_client.get("/api/retraining/summary")

    assert response.status_code == 401
    assert control.start_calls == []


def test_retraining_run_request_is_strict_and_does_not_accept_paths_or_flags(client):
    test_client, control = client

    response = test_client.post(
        "/api/retraining/runs",
        headers=_headers(),
        json={
            "trigger": "manual",
            "operator_note": "controlled run",
            "filesystem_path": "C:/outside",
            "training_flags": ["--epochs", "100"],
        },
    )

    assert response.status_code == 422
    assert control.start_calls == []


def test_deploy_and_rollback_requests_reject_model_paths_and_forbidden_text(client):
    test_client, _ = client

    deploy = test_client.post(
        f"/api/retraining/runs/{RUN_ID}/deploy",
        headers=_headers(role="ADMIN"),
        json={"expected_candidate_version": "C:/models/candidate"},
    )
    rollback = test_client.post(
        f"/api/retraining/runs/{RUN_ID}/rollback",
        headers=_headers(role="ADMIN", actor="admin-1"),
        json={
            "previous_staging_version": "staging-v1",
            "reason": "INTERNAL_API_KEY=not-a-reason",
        },
    )

    assert deploy.status_code == 422
    assert rollback.status_code == 422


def test_deploy_and_rollback_return_typed_run_records(client):
    test_client, control = client
    deploy_calls = []
    rollback_calls = []
    control.deploy = lambda **kwargs: (
        deploy_calls.append(kwargs) or _record(RunState.DEPLOYED)
    )
    control.rollback = lambda **kwargs: (
        rollback_calls.append(kwargs) or _record(RunState.ROLLED_BACK)
    )

    deploy = test_client.post(
        f"/api/retraining/runs/{RUN_ID}/deploy",
        headers=_headers(role="ADMIN"),
        json={"expected_candidate_version": "candidate-v1"},
    )
    rollback = test_client.post(
        f"/api/retraining/runs/{RUN_ID}/rollback",
        headers=_headers(role="ADMIN", actor="admin-1"),
        json={
            "previous_staging_version": "active-v1",
            "reason": "Restore the verified local staging model.",
        },
    )

    assert deploy.status_code == 200
    assert deploy.json()["state"] == "deployed"
    assert rollback.status_code == 200
    assert rollback.json()["state"] == "rolled_back"
    assert deploy_calls[0]["actor_role"] == "ADMIN"
    assert rollback_calls[0]["actor_id"] == "admin-1"


def test_retraining_run_is_accepted_without_waiting_for_worker(client):
    test_client, control = client

    response = test_client.post(
        "/api/retraining/runs",
        headers=_headers(),
        json={"trigger": "manual", "operator_note": "controlled run"},
    )

    assert response.status_code == 202
    assert response.json()["run_id"] == RUN_ID
    assert response.json()["created"] is True
    assert control.start_calls[0]["requested_by"] == "analyst-1"


def test_retraining_run_preserves_idempotent_existing_run_response(client):
    test_client, control = client

    first = test_client.post(
        "/api/retraining/runs",
        headers=_headers(),
        json={"trigger": "manual"},
    )
    second = test_client.post(
        "/api/retraining/runs",
        headers=_headers(),
        json={"trigger": "manual"},
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["run_id"] == second.json()["run_id"]
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert len(control.start_calls) == 2


def test_scheduled_run_accepts_bounded_schedule_timestamp(client):
    test_client, control = client

    response = test_client.post(
        "/api/retraining/runs",
        headers={
            **_headers(),
            "X-Requester-Timezone": "Asia/Manila",
            "X-Scheduled-At": "2026-08-11T12:00:00+00:00",
        },
        json={"trigger": "scheduled"},
    )

    assert response.status_code == 202
    assert control.start_calls[0]["scheduled_at"] == datetime(
        2026, 8, 11, 12, 0, tzinfo=timezone.utc
    )

    invalid = test_client.post(
        "/api/retraining/runs",
        headers={**_headers(), "X-Scheduled-At": "not-a-timestamp"},
        json={"trigger": "scheduled"},
    )
    assert invalid.status_code == 422


def test_summary_and_run_detail_are_safe_contracts(client):
    test_client, _ = client

    summary = test_client.get("/api/retraining/summary", headers=_headers())
    detail = test_client.get(f"/api/retraining/runs/{RUN_ID}", headers=_headers())

    assert summary.status_code == 200
    assert summary.json()["approved_count"] == 2
    assert detail.status_code == 200
    assert detail.json()["evidence_status"] == "NOT_RUN"
    assert "model_input_text" not in detail.text
    assert "http_request" not in detail.text


def test_retry_is_operator_only_and_has_no_client_training_options(client):
    test_client, control = client

    forbidden = test_client.post(
        f"/api/retraining/runs/{RUN_ID}/retry",
        headers=_headers(role="VIEWER"),
        json={},
    )
    assert forbidden.status_code == 403
    assert control.retry_calls == []

    response = test_client.post(
        f"/api/retraining/runs/{RUN_ID}/retry",
        headers=_headers(role="ANALYST"),
        json={},
    )

    assert response.status_code == 202
    assert response.json()["state"] == "queued"
    assert control.retry_calls == [
        {
            "run_id": RUN_ID,
            "actor_id": "analyst-1",
            "actor_role": "ANALYST",
        }
    ]

    invalid = test_client.post(
        f"/api/retraining/runs/{RUN_ID}/retry",
        headers=_headers(role="ANALYST"),
        json={"training_flags": ["--epochs", "100"]},
    )
    assert invalid.status_code == 422


def test_retry_offloads_synchronous_control_work(client, monkeypatch):
    test_client, control = client
    offloaded_calls = []

    async def fake_run_in_threadpool(function, *args, **kwargs):
        offloaded_calls.append((function, args, kwargs))
        return function(*args, **kwargs)

    monkeypatch.setattr(
        retraining_router_module,
        "run_in_threadpool",
        fake_run_in_threadpool,
    )

    response = test_client.post(
        f"/api/retraining/runs/{RUN_ID}/retry",
        headers=_headers(role="ANALYST"),
        json={},
    )

    assert response.status_code == 202
    assert offloaded_calls
    function, args, kwargs = offloaded_calls[0]
    assert function == control.retry_run
    assert args == ()
    assert kwargs == {
        "run_id": RUN_ID,
        "actor_id": "analyst-1",
        "actor_role": "ANALYST",
    }


def test_sync_control_reads_and_decisions_are_offloaded(client, monkeypatch):
    test_client, control = client
    offloaded_calls = []

    async def fake_run_in_threadpool(function, *args, **kwargs):
        offloaded_calls.append((function.__name__, args, kwargs))
        return function(*args, **kwargs)

    monkeypatch.setattr(
        retraining_router_module,
        "run_in_threadpool",
        fake_run_in_threadpool,
    )

    list_response = test_client.get("/api/retraining/runs", headers=_headers())
    detail_response = test_client.get(
        f"/api/retraining/runs/{RUN_ID}", headers=_headers()
    )
    decision_response = test_client.post(
        f"/api/retraining/runs/{RUN_ID}/decision",
        headers=_headers(role="ADMIN"),
        json={"decision": "hold", "reason": "need more evidence"},
    )

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert decision_response.status_code == 200
    assert [name for name, _, _ in offloaded_calls] == [
        "list_runs",
        "get_run_detail",
        "decide",
    ]


def test_only_administrators_can_decide_candidate_state(client):
    test_client, control = client

    response = test_client.post(
        f"/api/retraining/runs/{RUN_ID}/decision",
        headers=_headers(role="ANALYST"),
        json={"decision": "hold", "reason": "need more evidence"},
    )

    assert response.status_code == 403
    assert control.decision_calls == []


def test_deploy_and_rollback_are_explicit_control_plane_boundaries(client):
    test_client, _ = client

    deploy = test_client.post(
        f"/api/retraining/runs/{RUN_ID}/deploy",
        headers=_headers(role="ADMIN"),
        json={"expected_candidate_version": "candidate-v1"},
    )
    rollback = test_client.post(
        f"/api/retraining/runs/{RUN_ID}/rollback",
        headers=_headers(role="ADMIN"),
        json={"previous_staging_version": "staging-v1", "reason": "demo"},
    )

    assert deploy.status_code == 501
    assert rollback.status_code == 501
    assert "absolute" not in deploy.text.lower()
