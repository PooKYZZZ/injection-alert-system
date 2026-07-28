from __future__ import annotations

import time

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
        config_path=config.nginx_config, timeout=config.subprocess_timeout
    )
    reconciler = Reconciler(store, nginx, client, ReconcileConfig(config.mode))
    logger.emit("waf_sync_started", mode=config.mode)
    while True:
        try:
            result = reconciler.reconcile()
            logger.emit(
                "waf_reconcile_no_change"
                if result == "no_change"
                else "waf_candidate_selected",
                mode=config.mode,
                selected_kind=result,
            )
        except SnapshotRejected as exc:
            logger.emit(
                "waf_snapshot_rejected", mode=config.mode, reason=type(exc).__name__
            )
        except Exception as exc:
            logger.emit(
                "waf_sync_degraded", mode=config.mode, reason=type(exc).__name__
            )
        time.sleep(config.poll_interval)


if __name__ == "__main__":
    raise SystemExit(main())
