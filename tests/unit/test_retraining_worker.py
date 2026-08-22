import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ml_model.retraining.dashboard_contracts import RunState
from ml_model.retraining.dashboard_pipeline import (
    PipelineFailure,
    SmokeDashboardPipeline,
)
from ml_model.retraining.dashboard_worker import (
    EXIT_NOOP,
    EXIT_RETRYABLE_FAILURE,
    EXIT_SUCCESS,
    EXIT_TERMINAL_FAILURE,
    DashboardWorker,
)
import ml_model.retraining.dashboard_worker as dashboard_worker_module
from web_app.infrastructure.repositories.retraining_run_artifact_repository import (
    ArtifactIntegrityError,
    RetrainingRunArtifactRepository,
    RetrainingRunRecord,
    WorkerLockBusy,
)
from web_app.infrastructure.retraining_process_runner import (
    RetrainingProcessRunner,
    WorkerProcessHandle,
)
from web_app.infrastructure.retraining_worker_supervisor import (
    RetrainingWorkerSupervisor,
)

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
RUN_ID = "retrain-20260810T120000Z-000000000001"


def _record(
    *,
    run_id=RUN_ID,
    input_fingerprint="a" * 64,
    max_retries=2,
    approved_sample_count=1,
):
    return RetrainingRunRecord(
        run_id=run_id,
        state=RunState.QUEUED,
        stage="queued",
        attempt=0,
        retry_count=0,
        max_retries=max_retries,
        created_at=NOW,
        updated_at=NOW,
        heartbeat_at=None,
        trigger="manual",
        requested_by="analyst-1",
        requested_timezone="UTC",
        input_fingerprint=input_fingerprint,
        source_review_revisions=("1:1",),
        source_dataset_version="v3_907k_cleaned",
        source_dataset_digest="b" * 64,
        pipeline_fingerprint="c" * 64,
        active_model_version="active-v1",
        active_model_digest="d" * 64,
        approved_sample_count=approved_sample_count,
    )


class FailingPipeline:
    def __init__(self, failure):
        self.failure = failure

    def execute(self, run, repository, heartbeat):
        raise self.failure


class SlowPipeline:
    def execute(self, run, repository, heartbeat):
        time.sleep(0.02)


class RecordingLock:
    def __init__(self):
        self.heartbeats = 0
        self.released = False

    def heartbeat(self, now=None):
        del now
        self.heartbeats += 1

    def release(self):
        self.released = True


def test_smoke_worker_publishes_artifacts_and_never_claims_quality(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())
    worker = DashboardWorker(
        repository,
        root=tmp_path / "runs",
        pipeline=SmokeDashboardPipeline(),
        worker_id="worker-a",
        clock=lambda: NOW,
    )

    result = worker.run_once()
    run = repository.load_run(RUN_ID)

    assert result.exit_code == EXIT_SUCCESS
    assert run.state is RunState.NOT_ENOUGH_EVIDENCE
    assert repository.verify_artifacts(
        RUN_ID,
        (
            "stages/export.json",
            "stages/dataset.json",
            "stages/training.json",
            "stages/evaluation.json",
            "stages/comparison.json",
        ),
    )
    evaluation = json.loads(
        (tmp_path / "runs" / RUN_ID / "stages" / "evaluation.json").read_text(
            encoding="utf-8"
        )
    )
    assert evaluation["evidence_status"] == "NOT_RUN"
    assert "model_input_text" not in json.dumps(repository.read_events(RUN_ID))


def test_worker_lock_contention_is_a_safe_noop(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())
    lock = repository.acquire_worker_lock(
        worker_id="other", now=NOW, stale_after_seconds=60
    )
    try:
        result = DashboardWorker(
            repository,
            root=tmp_path / "runs",
            pipeline=SmokeDashboardPipeline(),
            worker_id="worker-a",
            clock=lambda: NOW,
        ).run_once()
    finally:
        lock.release()
    assert result.exit_code == EXIT_NOOP
    assert repository.load_run(RUN_ID).state is RunState.QUEUED


def test_worker_skips_no_approved_data_without_pipeline_execution(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record(approved_sample_count=0))

    result = DashboardWorker(
        repository,
        root=tmp_path / "runs",
        pipeline=FailingPipeline(PipelineFailure("SHOULD_NOT_RUN", retryable=False)),
        worker_id="worker-a",
        clock=lambda: NOW,
    ).run_once()

    assert result.exit_code == EXIT_SUCCESS
    assert repository.load_run(RUN_ID).state is RunState.SKIPPED_NO_APPROVED_DATA


def test_retryable_process_failure_uses_budget_and_does_not_claim_success(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record(max_retries=1))
    pipeline = FailingPipeline(
        PipelineFailure("TRAINING_PROCESS_FAILED", retryable=True)
    )
    worker = DashboardWorker(
        repository,
        root=tmp_path / "runs",
        pipeline=pipeline,
        worker_id="worker-a",
        clock=lambda: NOW,
    )

    first = worker.run_once()
    assert first.exit_code == EXIT_RETRYABLE_FAILURE
    assert repository.load_run(RUN_ID).state is RunState.RETRYABLE_FAILED
    second = worker.run_once(now=NOW + timedelta(seconds=10))

    assert second.exit_code == EXIT_TERMINAL_FAILURE
    assert repository.load_run(RUN_ID).state is RunState.FAILED
    assert repository.load_run(RUN_ID).error_code == "TRAINING_PROCESS_FAILED"


def test_invalid_artifact_failure_is_terminal_and_not_retried(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record(max_retries=2))
    worker = DashboardWorker(
        repository,
        root=tmp_path / "runs",
        pipeline=FailingPipeline(ArtifactIntegrityError("tampered artifact")),
        worker_id="worker-a",
        clock=lambda: NOW,
    )

    result = worker.run_once()

    assert result.exit_code == EXIT_TERMINAL_FAILURE
    run = repository.load_run(RUN_ID)
    assert run.state is RunState.FAILED
    assert run.retry_count == 0


def test_timeout_is_retryable_and_worker_restart_recovers_stale_run(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record(max_retries=2))
    worker = DashboardWorker(
        repository,
        root=tmp_path / "runs",
        pipeline=SlowPipeline(),
        worker_id="worker-a",
        timeout_seconds=0.001,
        clock=lambda: NOW,
    )

    result = worker.run_once()

    assert result.exit_code == EXIT_RETRYABLE_FAILURE
    assert repository.load_run(RUN_ID).state is RunState.RETRYABLE_FAILED


def test_worker_heartbeat_refreshes_both_run_and_host_lock(tmp_path, monkeypatch):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())
    lock = RecordingLock()
    monkeypatch.setattr(repository, "acquire_worker_lock", lambda **_: lock)

    result = DashboardWorker(
        repository,
        root=tmp_path / "runs",
        pipeline=SmokeDashboardPipeline(),
        worker_id="worker-a",
        clock=lambda: NOW,
    ).run_once()

    assert result.exit_code == EXIT_SUCCESS
    assert lock.heartbeats >= 4
    assert lock.released is True


def test_worker_until_idle_drains_all_runnable_runs(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())
    second_id = "retrain-20260810T120001Z-000000000002"
    repository.create_or_get_run(
        _record(run_id=second_id, input_fingerprint="e" * 64)
    )

    result = DashboardWorker(
        repository,
        root=tmp_path / "runs",
        pipeline=SmokeDashboardPipeline(),
        worker_id="worker-a",
        clock=lambda: NOW,
    ).run_until_idle(poll_seconds=0.001, max_runtime_seconds=5)

    assert result.exit_code == EXIT_SUCCESS
    assert repository.load_run(RUN_ID).state is RunState.NOT_ENOUGH_EVIDENCE
    assert repository.load_run(second_id).state is RunState.NOT_ENOUGH_EVIDENCE


def test_isolated_pipeline_timeout_terminates_child_before_retrying(tmp_path, monkeypatch):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())

    class HungProcess:
        pid = 4321

        def __init__(self):
            self.killed = False

        def wait(self, timeout=None):
            if not self.killed:
                raise subprocess.TimeoutExpired("dashboard-pipeline", timeout)
            return -9

        def kill(self):
            self.killed = True

    child = HungProcess()
    monkeypatch.setattr(
        dashboard_worker_module.subprocess,
        "Popen",
        lambda *args, **kwargs: child,
    )
    monkeypatch.setattr(
        dashboard_worker_module.subprocess,
        "run",
        lambda *args, **kwargs: None,
    )

    result = DashboardWorker(
        repository,
        root=tmp_path / "runs",
        worker_id="worker-a",
        timeout_seconds=0.001,
        clock=lambda: NOW,
    ).run_once()

    assert result.exit_code == EXIT_RETRYABLE_FAILURE
    assert child.killed is True
    assert repository.load_run(RUN_ID).error_code == "WORKER_TIMEOUT"


def test_isolated_pipeline_lock_loss_terminates_child(tmp_path, monkeypatch):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())

    class LostLock:
        def heartbeat(self, now=None):
            del now
            raise WorkerLockBusy("lock ownership changed")

        def release(self):
            pass

    class HungProcess:
        pid = 4323

        def __init__(self):
            self.killed = False

        def poll(self):
            return None if not self.killed else -9

        def wait(self, timeout=None):
            if not self.killed:
                raise subprocess.TimeoutExpired("dashboard-pipeline", timeout)
            return -9

        def kill(self):
            self.killed = True

    child = HungProcess()
    monkeypatch.setattr(
        dashboard_worker_module.subprocess,
        "Popen",
        lambda *args, **kwargs: child,
    )
    monkeypatch.setattr(
        dashboard_worker_module.subprocess,
        "run",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(repository, "acquire_worker_lock", lambda **_: LostLock())

    result = DashboardWorker(
        repository,
        root=tmp_path / "runs",
        worker_id="worker-a",
        timeout_seconds=1,
        clock=lambda: NOW,
    ).run_once()

    assert result.exit_code == EXIT_RETRYABLE_FAILURE
    assert child.killed is True
    assert repository.load_run(RUN_ID).error_code == "WORKER_LOCK_LOST"


def test_isolated_success_requires_a_published_terminal_state(tmp_path, monkeypatch):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())

    class ExitedProcess:
        pid = 4322

        def wait(self, timeout=None):
            del timeout
            return 0

    monkeypatch.setattr(
        dashboard_worker_module.subprocess,
        "Popen",
        lambda *args, **kwargs: ExitedProcess(),
    )

    result = DashboardWorker(
        repository,
        root=tmp_path / "runs",
        worker_id="worker-a",
        clock=lambda: NOW,
    ).run_once()

    assert result.exit_code == EXIT_TERMINAL_FAILURE
    assert repository.load_run(RUN_ID).error_code == "PIPELINE_STATE_INCOMPLETE"


def test_process_runner_uses_explicit_argument_list_and_restricted_environment(
    tmp_path, monkeypatch
):
    captured = {}

    class FakeProcess:
        pid = 1234

        def poll(self):
            return None

    def fake_popen(arguments, **kwargs):
        captured["arguments"] = arguments
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    runner = RetrainingProcessRunner(
        python_executable=Path(sys.executable),
        project_root=tmp_path,
        timeout_seconds=42,
    )

    handle = runner.start_worker(tmp_path / "runs")

    assert handle.pid == 1234
    assert captured["arguments"][:3] == [
        sys.executable,
        "-m",
        "ml_model.retraining.dashboard_worker",
    ]
    assert "--once" not in captured["arguments"]
    assert "--smoke" in captured["arguments"]
    assert captured["arguments"][captured["arguments"].index("--max-runtime-seconds") + 1] == "42"
    assert captured["arguments"][captured["arguments"].index("--timeout-seconds") + 1] == "42"
    assert captured["kwargs"]["shell"] is False
    assert "API_SECRET_KEY" not in captured["kwargs"]["env"]


def test_supervisor_starts_once_and_replaces_dead_worker_marker(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())

    class FakeRunner:
        def __init__(self):
            self.calls = 0

        def start_worker(self, _root):
            self.calls += 1
            return WorkerProcessHandle(1000 + self.calls, NOW)

    alive = {1001}
    runner = FakeRunner()
    supervisor = RetrainingWorkerSupervisor(
        repository,
        root=tmp_path / "runs",
        process_runner=runner,
        clock=lambda: NOW,
        process_checker=lambda pid: pid in alive,
    )

    first = supervisor.ensure_worker_available()
    second = supervisor.ensure_worker_available()
    alive.clear()
    third = supervisor.ensure_worker_available()

    assert first.started is True
    assert second.reason == "already_running"
    assert third.started is True
    assert runner.calls == 2


def test_supervisor_does_not_remove_a_guard_owned_by_another_start(tmp_path):
    repository = RetrainingRunArtifactRepository(tmp_path / "runs", clock=lambda: NOW)
    repository.create_or_get_run(_record())

    class FakeRunner:
        def start_worker(self, _root):
            raise AssertionError("competing supervisor must not start a worker")

    guard = tmp_path / "runs" / ".worker.supervisor.guard"
    guard.write_text("owned", encoding="utf-8")
    supervisor = RetrainingWorkerSupervisor(
        repository,
        root=tmp_path / "runs",
        process_runner=FakeRunner(),
        clock=lambda: NOW,
        process_checker=lambda _pid: False,
    )

    result = supervisor.ensure_worker_available()

    assert result.reason == "another_supervisor_starting"
    assert guard.is_file()
