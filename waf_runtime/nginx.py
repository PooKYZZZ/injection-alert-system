from __future__ import annotations

import os
import re
import subprocess
import time
import uuid
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
        probe_url: str = "http://127.0.0.1:8081",
        audit_log_path: str | Path | None = None,
        pid_path: str | Path = "/tmp/nginx.pid",
        crs_probe_url: str = "http://127.0.0.1:8080",
    ):
        self.config_path = str(config_path)
        self.timeout = timeout
        self.nginx_binary = nginx_binary
        self.active_path = Path(active_path)
        self.probe_url = probe_url.rstrip("/")
        self.audit_log_path = Path(audit_log_path) if audit_log_path else None
        self.pid_path = Path(pid_path)
        self.crs_probe_url = crs_probe_url.rstrip("/")

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
            if (
                after
                and after != before
                and self._request_status(
                    "/__pr7/ready", None, uuid.uuid4().hex
                )
                == 204
            ):
                time.sleep(min(1.0, self.timeout / 2))
                return True
            time.sleep(0.05)
        return False

    def probe_candidate(
        self,
        candidate: Path,
        source_ip: str | None = None,
        revision: int | None = None,
        recommendation_id: int | None = None,
    ) -> bool:
        if not self._is_selected(candidate):
            return False
        source_ip = source_ip or self._candidate_sources(candidate)[0]
        if self.audit_log_path is not None:
            revision = revision or self._candidate_tag(candidate, "revision")
            recommendation_id = recommendation_id or self._candidate_tag(
                candidate, "recommendation"
            )
        marker = self._probe_positive_candidate(
            source_ip, revision, recommendation_id
        )
        if marker is None:
            return False
        wrong_source = self._wrong_source(self._candidate_sources(candidate))
        if self._request_status("/records/search", wrong_source, marker) != 204:
            return False
        if self._request_status("/records/not-search", source_ip, marker) != 204:
            return False
        if self._request_status(
            "/records/search?query=%27%20UNION%20SELECT%20null--",
            wrong_source,
            marker,
            base_url=self.crs_probe_url,
        ) != 403:
            return False
        return self._audit_contains_any(marker, '"attack-sqli"', '"942100"')

    def _probe_positive_candidate(
        self,
        source_ip: str,
        revision: int | None,
        recommendation_id: int | None,
    ) -> str | None:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            marker = uuid.uuid4().hex
            if self._request_status("/records/search", source_ip, marker) == 403:
                if self._audit_contains_all(
                    marker,
                    '"pr7"',
                    f'"revision-{revision}"',
                    f'"recommendation-{recommendation_id}"',
                ):
                    return marker
            time.sleep(0.05)
        return None

    def probe_empty(self, candidate: Path) -> bool:
        if not self._is_selected(candidate):
            return False
        return self._request_status("/records/search", None, uuid.uuid4().hex) == 204

    def wait_ready(self) -> bool:
        return bool(self.worker_generation()) and (
            self._request_status("/__pr7/ready", None, uuid.uuid4().hex) == 204
        )

    def _request_status(
        self,
        path: str,
        source_ip: str | None,
        marker: str,
        *,
        base_url: str | None = None,
    ) -> int | None:
        try:
            headers = {"Accept-Encoding": "identity"}
            if source_ip:
                headers["X-PR7-Probe-Source"] = source_ip
            with httpx.Client(
                follow_redirects=False,
                trust_env=False,
                timeout=self.timeout,
                headers=headers,
            ) as client:
                separator = "&" if "?" in path else "?"
                endpoint = (base_url or self.probe_url).rstrip("/")
                response = client.get(
                    f"{endpoint}{path}{separator}pr7_probe_id={marker}",
                    timeout=min(2.0, self.timeout),
                )
            return response.status_code
        except httpx.HTTPError:
            return None

    def _audit_contains_all(self, marker: str, *tokens: str) -> bool:
        if self.audit_log_path is None:
            return True
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                for line in self.audit_log_path.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()[-100:]:
                    if marker in line and all(token in line for token in tokens):
                        return True
            except OSError:
                pass
            time.sleep(0.05)
        return False

    def _audit_contains_any(self, marker: str, *tokens: str) -> bool:
        if self.audit_log_path is None:
            return True
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            try:
                for line in self.audit_log_path.read_text(
                    encoding="utf-8", errors="replace"
                ).splitlines()[-100:]:
                    if marker in line and any(token in line for token in tokens):
                        return True
            except OSError:
                pass
            time.sleep(0.05)
        return False

    @staticmethod
    def _candidate_tag(candidate: Path, name: str) -> str:
        match = re.search(rf"tag:'{name}-([0-9]+)'", candidate.read_text())
        if not match:
            raise ValueError(f"candidate has no {name} tag")
        return match.group(1)

    @staticmethod
    def _candidate_sources(candidate: Path) -> list[str]:
        sources = re.findall(r'@ipMatch ([0-9.]+)', candidate.read_text())
        if not sources:
            raise ValueError("candidate has no source rule")
        return sources

    @staticmethod
    def _wrong_source(sources: list[str]) -> str:
        for suffix in range(1, 255):
            candidate = f"198.51.100.{suffix}"
            if candidate not in sources:
                return candidate
        raise ValueError("candidate source space is exhausted")

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
        pid_path = self.pid_path
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
