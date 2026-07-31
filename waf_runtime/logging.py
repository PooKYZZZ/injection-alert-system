from __future__ import annotations

import json
import sys
import time


class JsonEventLogger:
    SAFE_FIELDS = {
        "mode",
        "selected_kind",
        "result",
        "revision",
        "state_checksum",
        "candidate_checksum",
        "entry_count",
        "duration_ms",
        "total_ms",
        "attempt",
        "candidate_basename",
        "worker_count",
        "process",
        "exit_code",
        "signal",
        "reason",
    }

    def __init__(self, secret: str = ""):
        self.secret = secret

    def emit(self, event: str, **fields) -> None:
        safe = {key: value for key, value in fields.items() if key in self.SAFE_FIELDS}
        output = json.dumps(
            {"event": event, "timestamp": time.time(), **safe}, sort_keys=True
        )
        if self.secret:
            output = output.replace(self.secret, "[REDACTED]")
        sys.stdout.write(output + "\n")
        sys.stdout.flush()
