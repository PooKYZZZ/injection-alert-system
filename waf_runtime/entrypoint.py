from __future__ import annotations

from .config import RuntimeConfig
from .state import CandidateStateStore
from .supervisor import Supervisor


def main() -> int:
    # Seed the selected file before the NGINX child starts.  The mounted state
    # volume may be empty on first boot, while the rendered NGINX config reads
    # this file during bootstrap.
    config = RuntimeConfig.from_env()
    CandidateStateStore(config.state_dir)
    # The original image entrypoint remains the child bootstrap for NGINX.
    nginx_command = ["/docker-entrypoint.sh", "nginx", "-g", "daemon off;"]
    supervisor = Supervisor(nginx_command, ["python3", "-m", "waf_runtime.worker"])
    return supervisor.run()
