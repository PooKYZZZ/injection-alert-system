from __future__ import annotations

import signal
import subprocess
import time
from collections.abc import Callable
from typing import Sequence

SIGQUIT = getattr(
    signal, "SIGQUIT", getattr(signal, "SIGBREAK", signal.SIGTERM)
)

class Supervisor:
    """Minimal PID-1 supervisor for foreground NGINX and one synchroniser."""

    def __init__(
        self,
        nginx_command: Sequence[str],
        synchroniser_command: Sequence[str],
        shutdown_grace: float = 5.0,
        ready_check: Callable[[], bool] | None = None,
    ):
        self.nginx_command = list(nginx_command)
        self.synchroniser_command = list(synchroniser_command)
        self.shutdown_grace = shutdown_grace
        self.ready_check = ready_check
        self.shutdown_requested = False
        self.shutdown_signal = signal.SIGTERM

    def request_shutdown(self, signum, _frame) -> None:
        self.shutdown_requested = True
        self.shutdown_signal = signum

    def run_once(self) -> int:
        nginx = subprocess.Popen(self.nginx_command)
        synchroniser = None
        try:
            if self.ready_check is not None and not self._wait_ready(nginx):
                self._stop(nginx, signal.SIGTERM)
                return 1
            synchroniser = subprocess.Popen(self.synchroniser_command)
            while True:
                nginx_code = nginx.poll()
                sync_code = synchroniser.poll()
                if self.shutdown_requested:
                    nginx_signal = (
                        SIGQUIT
                        if self.shutdown_signal == SIGQUIT
                        else self.shutdown_signal
                    )
                    self._stop(nginx, nginx_signal)
                    self._stop(synchroniser, signal.SIGTERM)
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
                if child is not None and child.poll() is None:
                    self._stop(child)

    def _wait_ready(self, nginx) -> bool:
        deadline = time.monotonic() + self.shutdown_grace
        while time.monotonic() < deadline:
            if nginx.poll() is not None:
                return False
            if self.ready_check and self.ready_check():
                return True
            time.sleep(0.05)
        return False

    def run(self) -> int:
        for signum in (signal.SIGTERM, signal.SIGINT, SIGQUIT):
            signal.signal(signum, self.request_shutdown)
        return self.run_once()

    def _stop(self, child, signum=signal.SIGTERM) -> None:
        try:
            if hasattr(child, "send_signal"):
                child.send_signal(signum)
            else:
                child.terminate()
            child.wait(timeout=self.shutdown_grace)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=1)
