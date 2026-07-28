from __future__ import annotations

import subprocess
from pathlib import Path


class NginxController:
    def __init__(
        self,
        *,
        config_path: str | Path,
        timeout: float = 5.0,
        nginx_binary: str = "nginx",
    ):
        self.config_path = str(config_path)
        self.timeout = timeout
        self.nginx_binary = nginx_binary

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args, check=False, capture_output=True, text=True, timeout=self.timeout
        )

    def validate_candidate(self, path: Path) -> bool:
        result = self._run([self.nginx_binary, "-t", "-c", self.config_path])
        return result.returncode == 0

    def reload_and_confirm(self) -> bool:
        result = self._run([self.nginx_binary, "-s", "reload"])
        return result.returncode == 0

    def probe_candidate(self, candidate: Path) -> bool:
        return candidate.is_file() and candidate.stat().st_size >= 0
