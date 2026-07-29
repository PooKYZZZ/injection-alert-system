from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import httpx


class NginxController:
    def __init__(
        self,
        *,
        config_path: str | Path,
        timeout: float = 5.0,
        nginx_binary: str = "nginx",
        active_path: str | Path = "/pr7-state/selected.conf",
        probe_url: str = "http://127.0.0.1:8080",
    ):
        self.config_path = str(config_path)
        self.timeout = timeout
        self.nginx_binary = nginx_binary
        self.active_path = Path(active_path)
        self.probe_url = probe_url.rstrip("/")

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args, check=False, capture_output=True, text=True, timeout=self.timeout
        )

    def validate_candidate(self, path: Path) -> bool:
        if (
            path.is_symlink()
            or not path.is_file()
            or self.active_path.is_symlink()
            or not self.active_path.is_file()
        ):
            return False
        candidate = path.read_bytes()
        original = self.active_path.read_bytes()
        self._replace(self.active_path, candidate)
        try:
            try:
                result = self._run([self.nginx_binary, "-t", "-c", self.config_path])
            except (OSError, subprocess.SubprocessError):
                return False
            return result.returncode == 0
        finally:
            self._replace(self.active_path, original)

    def reload_and_confirm(self) -> bool:
        before = self.worker_generation()
        try:
            result = self._run([self.nginx_binary, "-s", "reload"])
        except (OSError, subprocess.SubprocessError):
            return False
        if result.returncode != 0:
            return False
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            after = self.worker_generation()
            if after and after != before:
                return True
            time.sleep(0.05)
        return False

    def probe_candidate(self, candidate: Path) -> bool:
        if not self._is_selected(candidate):
            return False
        try:
            with httpx.Client(
                follow_redirects=False,
                trust_env=False,
                timeout=self.timeout,
                headers={"Accept-Encoding": "identity"},
            ) as client:
                response = client.get(
                    f"{self.probe_url}/records/search",
                    timeout=min(2.0, self.timeout),
                )
            return response.status_code == 403
        except httpx.HTTPError:
            return False

    def probe_empty(self, candidate: Path) -> bool:
        if not self._is_selected(candidate):
            return False
        try:
            with httpx.Client(
                follow_redirects=False,
                trust_env=False,
                timeout=self.timeout,
                headers={"Accept-Encoding": "identity"},
            ) as client:
                response = client.get(
                    f"{self.probe_url}/records/search",
                    timeout=min(2.0, self.timeout),
                )
            return response.status_code != 403
        except httpx.HTTPError:
            return False

    def _is_selected(self, candidate: Path) -> bool:
        if (
            candidate.is_symlink()
            or not candidate.is_file()
            or self.active_path.is_symlink()
            or not self.active_path.is_file()
        ):
            return False
        try:
            return candidate.read_bytes() == self.active_path.read_bytes()
        except OSError:
            return False

    def worker_generation(self) -> tuple[str, ...]:
        pid_path = Path("/run/nginx.pid")
        if not pid_path.is_file():
            return ()
        try:
            master_pid = pid_path.read_text(encoding="ascii").strip()
            children_path = Path(f"/proc/{master_pid}/task/{master_pid}/children")
            return tuple(sorted(children_path.read_text().split()))
        except (OSError, ValueError):
            return ()

    @staticmethod
    def _replace(path: Path, content: bytes) -> None:
        temporary = path.with_name(f".{path.name}.validation-{os.getpid()}")
        with temporary.open("wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
