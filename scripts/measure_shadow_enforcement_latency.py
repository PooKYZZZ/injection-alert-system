from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from urllib.parse import urlsplit, urlunsplit
import urllib.error
import urllib.request


def percentile(samples: list[float], percent: float) -> float | None:
    if not samples:
        return None
    ordered = sorted(samples)
    position = (len(ordered) - 1) * (percent / 100)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction, 2)


def _safe_route(route: str) -> str:
    parsed = urlsplit(route)
    return urlunsplit(("", "", parsed.path or "/", "", ""))


def _request_once(url: str, timeout: float) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "CyberTrace-shadow-latency/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return "success" if 200 <= int(response.status) < 400 else "error"
    except (TimeoutError, urllib.error.URLError, OSError) as exc:
        return "timeout" if isinstance(exc, TimeoutError) else "error"


def measure_samples(
    base_url: str,
    route: str,
    *,
    count: int,
    timeout: float,
    clock: Callable[[], float] = time.perf_counter,
) -> dict:
    safe_route = _safe_route(route)
    url = f"{base_url.rstrip('/')}{safe_route}"
    latencies: list[float] = []
    successes = errors = timeouts = 0
    for _ in range(count):
        started = clock()
        try:
            outcome = _request_once(url, timeout)
        except TimeoutError:
            outcome = "timeout"
        elapsed_ms = (clock() - started) * 1000
        if outcome == "success":
            successes += 1
            latencies.append(elapsed_ms)
        elif outcome == "timeout":
            timeouts += 1
        else:
            errors += 1
    return {
        "samples": count,
        "successes": successes,
        "errors": errors,
        "timeouts": timeouts,
        "p50_ms": percentile(latencies, 50),
        "p95_ms": percentile(latencies, 95),
        "p99_ms": percentile(latencies, 99),
        "max_ms": round(max(latencies), 2) if latencies else None,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Measure shadow check request latency")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--route", default="/records/search")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--json-output")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.count < 1 or args.timeout <= 0 or args.warmup < 0:
        raise SystemExit("count must be positive, timeout must be positive, warmup cannot be negative")
    safe_route = _safe_route(args.route)
    for _ in range(args.warmup):
        _request_once(f"{args.base_url.rstrip('/')}{safe_route}", args.timeout)
    result = measure_samples(args.base_url, safe_route, count=args.count, timeout=args.timeout)
    payload = {
        "base_url": urlunsplit((*urlsplit(args.base_url)[:2], "", "", "")),
        "route": safe_route,
        "timeout_seconds": args.timeout,
        "warmup": args.warmup,
        **result,
    }
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
    if args.json:
        print(json.dumps(payload, separators=(",", ":")))
    else:
        print(json.dumps(payload, indent=2))
    return 0 if result["successes"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
