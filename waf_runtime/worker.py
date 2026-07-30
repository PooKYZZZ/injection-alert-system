from __future__ import annotations

import time

from .activation import ActivationError, RollbackError
from .config import RuntimeConfig
from .logging import JsonEventLogger
from .nginx import NginxController
from .reconcile import Reconciler
from .reconcile import RuntimeConfig as ReconcileConfig
from .snapshot import SnapshotClient, SnapshotRejected
from .state import CandidateStateStore


def main() -> int:
    config = RuntimeConfig.from_env()
    logger = JsonEventLogger(config.sync_api_key)
    store = CandidateStateStore(config.state_dir)
    client = SnapshotClient(
        config.snapshot_url,
        config.sync_api_key,
        total_timeout=config.subprocess_timeout,
    )
    nginx = NginxController(
        config_path=config.nginx_config,
        timeout=config.subprocess_timeout,
        active_path=f"{config.state_dir}/selected.conf",
        probe_url=config.probe_url,
        audit_log_path=config.audit_log_path,
    )
    reconciler = Reconciler(store, nginx, client, ReconcileConfig(config.mode))
    logger.emit("waf_sync_started", mode=config.mode)
    while True:
        reconcile_once(reconciler, logger, config.mode)
        time.sleep(config.poll_interval)


def reconcile_once(reconciler, logger, mode: str):
    try:
        result = reconciler.reconcile()
    except SnapshotRejected as exc:
        logger.emit("waf_snapshot_rejected", mode=mode, reason=type(exc).__name__)
        return None
    except RollbackError as exc:
        logger.emit("waf_rollback_failed", mode=mode, reason=type(exc).__name__)
        raise
    except ActivationError as exc:
        logger.emit("waf_activation_failed", mode=mode, reason=type(exc).__name__)
        return None
    if result in {"stale_ignored", "conflict_rejected"}:
        logger.emit("waf_snapshot_rejected", mode=mode, reason=result)
    else:
        logger.emit(
            "waf_reconcile_no_change"
            if result == "no_change"
            else "waf_candidate_selected",
            mode=mode,
            selected_kind=result,
        )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
