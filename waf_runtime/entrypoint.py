from __future__ import annotations

import subprocess

from .config import RuntimeConfig
from .nginx import NginxController
from .state import CandidateStateStore
from .supervisor import Supervisor


def prepare_startup_state(store: CandidateStateStore, mode: str) -> str:
    with store.locked():
        if store.is_disabled():
            kind = "disabled_empty"
        elif mode in {"off", "dry_run"}:
            kind = "mode_empty"
        else:
            kind = "pending_empty"
        store.set_empty_state(kind)
        return kind


def prepare_nginx_configuration() -> None:
    result = subprocess.run(
        ["/docker-entrypoint.sh", "nginx", "-t", "-q"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError("NGINX startup configuration validation failed")


def main() -> int:
    config = RuntimeConfig.from_env()
    store = CandidateStateStore(config.state_dir)
    prepare_startup_state(store, config.mode)
    prepare_nginx_configuration()
    nginx = NginxController(
        config_path=config.nginx_config,
        timeout=config.subprocess_timeout,
        active_path=f"{config.state_dir}/selected.conf",
        probe_url=config.probe_url,
        audit_log_path=config.audit_log_path,
    )
    nginx_command = ["/docker-entrypoint.sh", "nginx", "-g", "daemon off;"]
    supervisor = Supervisor(
        nginx_command,
        ["python3", "-m", "waf_runtime.worker"],
        ready_check=nginx.wait_ready,
    )
    return supervisor.run()
