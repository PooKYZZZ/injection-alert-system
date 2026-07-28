from __future__ import annotations

import argparse
import json
import os

from .controls import WafControls
from .state import CandidateStateStore


def main() -> int:
    parser = argparse.ArgumentParser(prog="pr7-waf-control")
    parser.add_argument("command", choices=("disable", "enable", "status"))
    args = parser.parse_args()
    result = getattr(
        WafControls(CandidateStateStore(os.environ.get("PR7_STATE_DIR", "/pr7-state"))),
        args.command,
    )()
    print(json.dumps(result, sort_keys=True) if isinstance(result, dict) else result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
