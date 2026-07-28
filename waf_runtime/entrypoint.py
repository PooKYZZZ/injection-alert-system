from __future__ import annotations

from .supervisor import Supervisor


def main() -> int:
    # The original image entrypoint remains the child bootstrap for NGINX.
    nginx_command = ["/docker-entrypoint.sh", "nginx", "-g", "daemon off;"]
    supervisor = Supervisor(nginx_command, ["python3", "-m", "waf_runtime.worker"])
    return supervisor.run()
