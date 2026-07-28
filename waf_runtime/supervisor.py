from __future__ import annotations

import signal
import subprocess
import time
from typing import Sequence


class Supervisor:
    """Minimal PID-1 supervisor for foreground NGINX and one synchroniser."""

    def __init__(
        self,
        nginx_command: Sequence[str],
        synchroniser_command: Sequence[str],
        shutdown_grace: float = 5.0,
    ):
        self.nginx_command = list(nginx_command)
        self.synchroniser_command = list(synchroniser_command)
        self.shutdown_grace = shutdown_grace
        self.shutdown_requested = False

    def request_shutdown(self, signum, _frame) -> None:
        self.shutdown_requested = True

    def run_once(self) -> int:
        nginx = subprocess.Popen(self.nginx_command)
        synchroniser = subprocess.Popen(self.synchroniser_command)
        try:
            while True:
                nginx_code = nginx.poll()
                sync_code = synchroniser.poll()
                if self.shutdown_requested:
                    self._stop(nginx)
                    self._stop(synchroniser)
                    return 0
                if nginx_code is not None:
                    self._stop(synchroniser)
                    return nginx_code if nginx_code != 0 else 1
                if sync_code is not None:
                    self._stop(nginx)
                    return sync_code if sync_code != 0 else 1
                time.sleep(0.05)
        finally:
            for child in (nginx, synchroniser):
                if child.poll() is None:
                    self._stop(child)

    def run(self) -> int:
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGQUIT):
            signal.signal(signum, self.request_shutdown)
        return self.run_once()

    def _stop(self, child) -> None:
        try:
            child.terminate()
            child.wait(timeout=self.shutdown_grace)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=1)
