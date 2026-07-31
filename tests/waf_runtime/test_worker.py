from __future__ import annotations

import pytest

from waf_runtime.activation import ActivationError
from waf_runtime.worker import reconcile_once


class BrokenReconciler:
    def reconcile(self):
        raise RuntimeError("programming failure")


class Logger:
    def emit(self, *args, **kwargs):
        pass


def test_programming_errors_escape_the_worker_loop():
    with pytest.raises(RuntimeError, match="programming failure"):
        reconcile_once(BrokenReconciler(), Logger(), "enforce")


def test_expected_activation_rejections_do_not_kill_the_worker_loop():
    class RejectedReconciler:
        def reconcile(self):
            raise ActivationError("candidate rejected")

    events = []

    class EventLogger:
        def emit(self, *args, **kwargs):
            events.append((args, kwargs))

    assert reconcile_once(RejectedReconciler(), EventLogger(), "enforce") is None
    assert events[-1][0][0] == "waf_activation_failed"


@pytest.mark.parametrize("result", ["stale_ignored", "conflict_rejected"])
def test_revision_rejections_have_explicit_events(result):
    class RejectedReconciler:
        def reconcile(self):
            return result

    events = []

    class EventLogger:
        def emit(self, *args, **kwargs):
            events.append((args, kwargs))

    assert reconcile_once(RejectedReconciler(), EventLogger(), "enforce") == result
    assert events[-1][0][0] == "waf_snapshot_rejected"
    assert events[-1][1]["reason"] == result


def test_reconcile_events_include_bounded_total_duration(monkeypatch):
    class UnchangedReconciler:
        def reconcile(self):
            return "no_change"

    events = []

    class EventLogger:
        def emit(self, *args, **kwargs):
            events.append((args, kwargs))

    ticks = iter([10.0, 10.125])
    monkeypatch.setattr("waf_runtime.worker.time.perf_counter", lambda: next(ticks))

    assert reconcile_once(UnchangedReconciler(), EventLogger(), "enforce") == "no_change"
    assert events[-1][1]["total_ms"] == 125.0
