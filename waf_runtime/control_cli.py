from __future__ import annotations

import argparse
import json

from .config import RuntimeConfig
from .controls import WafControls
from .nginx import NginxController
from .reconcile import Reconciler
from .reconcile import RuntimeConfig as ReconcileConfig
from .snapshot import SnapshotClient
from .state import CandidateStateStore


def main() -> int:
    parser = argparse.ArgumentParser(prog="pr7-waf-control")
    parser.add_argument("command", choices=("disable", "enable", "status"))
    args = parser.parse_args()
    config = RuntimeConfig.from_env()
    store = CandidateStateStore(config.state_dir)
    nginx = NginxController(
        config_path=config.nginx_config,
        timeout=config.subprocess_timeout,
        active_path=f"{config.state_dir}/selected.conf",
        probe_url=config.probe_url,
        audit_log_path=config.audit_log_path,
    )
    reconcile = None
    if args.command == "enable":
        client = SnapshotClient(
            config.snapshot_url,
            config.sync_api_key,
            total_timeout=config.subprocess_timeout,
        )
        reconciler = Reconciler(
            store, nginx, client, config=ReconcileConfig(mode=config.mode)
        )
        reconcile = reconciler.reconcile
    result = getattr(
        WafControls(store, nginx, reconcile=reconcile),
        args.command,
    )()
    print(json.dumps(result, sort_keys=True) if isinstance(result, dict) else result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
