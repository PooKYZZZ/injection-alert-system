from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from enum import StrEnum
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class FaultMode(StrEnum):
    VALID = "valid"
    UNAUTHORIZED = "unauthorized"
    SERVER_ERROR = "server_error"
    REDIRECT = "redirect"
    WRONG_CONTENT_TYPE = "wrong_content_type"
    MALFORMED_JSON = "malformed_json"
    OVERSIZED = "oversized"
    TIMEOUT = "timeout"


@dataclass(frozen=True, slots=True)
class FaultResponse:
    mode: FaultMode = FaultMode.VALID
    payload: dict[str, Any] | None = None
    delay_seconds: float = 0.0


class _FaultHandler(BaseHTTPRequestHandler):
    server: "SnapshotFaultServer"

    def do_GET(self) -> None:  # noqa: N802
        fault = self.server.response
        if fault.delay_seconds:
            time.sleep(fault.delay_seconds)
        if fault.mode is FaultMode.TIMEOUT:
            time.sleep(self.server.timeout_delay_seconds)
            return
        if fault.mode is FaultMode.UNAUTHORIZED:
            self.send_response(401)
            self.end_headers()
            return
        if fault.mode is FaultMode.SERVER_ERROR:
            self.send_response(500)
            self.end_headers()
            return
        if fault.mode is FaultMode.REDIRECT:
            self.send_response(302)
            self.send_header("Location", "http://evil.invalid/")
            self.end_headers()
            return
        if fault.mode is FaultMode.WRONG_CONTENT_TYPE:
            body = b"{}"
            content_type = "text/plain"
        elif fault.mode is FaultMode.MALFORMED_JSON:
            body = b"{malformed"
            content_type = "application/json"
        elif fault.mode is FaultMode.OVERSIZED:
            body = b"{" + b"x" * (1024 * 1024 + 1) + b"}"
            content_type = "application/json"
        else:
            body = json.dumps(fault.payload or {}).encode("utf-8")
            content_type = "application/json"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


class SnapshotFaultServer(ThreadingHTTPServer):
    allow_reuse_address = True
    timeout_delay_seconds = 10.0

    def __init__(self, response: FaultResponse):
        super().__init__(("127.0.0.1", 0), _FaultHandler)
        self.response = response
        self._thread: threading.Thread | None = None

    @property
    def endpoint(self) -> str:
        return f"http://127.0.0.1:{self.server_port}/api/internal/waf-enforcement/snapshot"

    def __enter__(self) -> "SnapshotFaultServer":
        self._thread = threading.Thread(target=self.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.shutdown()
        self.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
