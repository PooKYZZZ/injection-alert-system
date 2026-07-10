"""Run the guarded, harmless Resend development connectivity smoke test."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from web_app.config import get_settings
from web_app.notifications.smoke import run_smoke_cli


def main() -> int:
    return asyncio.run(run_smoke_cli(get_settings()))


if __name__ == "__main__":
    raise SystemExit(main())
