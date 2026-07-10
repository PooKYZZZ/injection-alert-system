from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "scripts" / "run_resend_smoke.py"


def test_direct_smoke_script_uses_safe_disabled_path() -> None:
    env = {
        **os.environ,
        "DATABASE_URL": "sqlite+aiosqlite:///smoke-test.db",
        "MODEL_PATH": "unused",
        "RESEND_LIVE_TEST_ENABLED": "false",
        "RESEND_API_KEY": "must-not-print",
    }

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout.strip() == "SKIP: live Resend smoke test is disabled"
    assert "must-not-print" not in result.stdout
    assert result.stderr == ""
