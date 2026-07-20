#!/usr/bin/env python3
"""
CyberTrace local WAF serious probe runner.

Purpose
-------
Run a local, repeatable, evidence-oriented WAF/security smoke test against your
WAF-protected demo website. It is designed for your CyberTrace demo path:

    protected demo website -> ModSecurity/OWASP CRS -> audit JSONL -> bridge -> FastAPI -> dashboard

Default target:
    http://localhost:8089

Default audit log:
    ./logs/modsecurity/demo-target/modsec_audit.jsonl

Output:
    ./waf_probe_<timestamp>.json

Safety
------
By default this script only targets loopback/local/private addresses. Use
--allow-non-local only when you own the target and have permission.

This is not an exploit tool. It sends common non-destructive payloads to verify
blocking, logging, ingestion, and dashboard evidence. It does not attempt data
exfiltration, shell callbacks, password brute-force, or destructive mutation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
from html.parser import HTMLParser
import ipaddress
import json
import os
from pathlib import Path
import random
import re
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen


# ----------------------------
# Seeds and payload corpus
# ----------------------------

DEFAULT_COMMON_PATHS = [
    "/",
    "/health",
    "/healthz",
    "/login",
    "/login/submit",
    "/admin",
    "/dashboard",
    "/records",
    "/records/search",
    "/records/1",
    "/records/LND-2026-0001",
    "/records/LND-2026-0001/request-copy",
    "/records/LND-2026-0001/request-copy/submit",
    "/appointments",
    "/appointments/submit",
    "/comments",
    "/comments/submit",
    "/support",
    "/support/submit",
    "/transactions/status",
    "/search",
    "/api/health",
    "/api/login",
    "/api/records",
    "/api/records/search",
    "/api/appointments",
    "/api/comments",
    "/api/support",
    "/api/transactions/status",
]

COMMON_PARAM_NAMES = [
    "q",
    "query",
    "search",
    "id",
    "recordId",
    "record_id",
    "ref",
    "reference",
    "tracking",
    "page",
    "limit",
    "sort",
    "order",
    "filter",
    "status",
    "type",
    "name",
    "email",
    "username",
    "password",
    "role",
    "message",
    "comment",
    "file",
    "path",
    "url",
    "next",
    "redirect",
    "callback",
    "returnUrl",
]

PAYLOADS: dict[str, list[str]] = {
    "sqli-basic": [
        "'",
        "''",
        "\"",
        "' OR '1'='1'--",
        "\" OR \"1\"=\"1\"--",
        "admin'--",
        "1' AND '1'='2'--",
        "1' AND '1'='1'--",
        "1) OR (1=1)--",
        "' UNION SELECT null,null,null--",
        "' UNION ALL SELECT NULL,NULL,NULL--",
        "1; SELECT version()--",
        "1;WAITFOR DELAY '0:0:1'--",
        "1' OR SLEEP(1)--",
    ],
    "xss": [
        "<script>alert(1)</script>",
        "<ScRiPt>alert(1)</ScRiPt>",
        "\"><svg/onload=alert(1)>",
        "'><img src=x onerror=alert(1)>",
        "<body onload=alert(1)>",
        "javascript:alert(1)",
        "<iframe src=javascript:alert(1)>",
        "<math><mtext></form><form><mglyph><style></math><img src=x onerror=alert(1)>",
    ],
    "cmd": [
        "test;whoami",
        "test|whoami",
        "test&&whoami",
        "$(whoami)",
        "`whoami`",
        "test%0Aid",
        "test\nid",
        "test${IFS}&&${IFS}whoami",
    ],
    "traversal": [
        "../../../../etc/passwd",
        "..\\..\\windows\\win.ini",
        "..%2f..%2f..%2fetc%2fpasswd",
        "%252e%252e%252f%252e%252e%252fetc%252fpasswd",
        "....//....//etc/passwd",
        "/proc/self/environ",
        "file:///etc/passwd",
    ],
    "ssti-template": [
        "{{7*7}}",
        "${7*7}",
        "<%= 7*7 %>",
        "#{7*7}",
        "{{config}}",
    ],
    "xxe-ish": [
        "<?xml version='1.0'?><!DOCTYPE x [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><x>&xxe;</x>",
    ],
    "nosql-ish": [
        '{"$ne": null}',
        '{"$gt": ""}',
        '{"username":{"$ne":null},"password":{"$ne":null}}',
    ],
    "redirect-ssrf-ish": [
        "http://127.0.0.1:8000/health",
        "http://localhost:8000/health",
        "http://169.254.169.254/latest/meta-data/",
        "//evil.example.test/path",
    ],
    "edge-long": [
        "A" * 512,
        "B" * 2048,
        "C" * 8192,
        "%00",
        "\x00",
        "test\r\nX-Injected-Header: yes",
        "こんにちは<script>alert(1)</script>",
    ],
}

HEADER_PAYLOADS = [
    ("User-Agent", "CyberTraceProbe/1.0 ' OR '1'='1'--", "header-sqli"),
    ("User-Agent", "<script>alert(1)</script>", "header-xss"),
    ("Referer", "<script>alert(1)</script>", "header-xss"),
    ("Referer", "http://127.0.0.1:8000/admin", "header-ssrf-ish"),
    ("X-Forwarded-For", "127.0.0.1' OR '1'='1'--", "header-sqli"),
    ("X-Forwarded-Host", "evil.example.test", "header-host"),
    ("X-Original-URL", "/admin", "header-routing"),
    ("X-Rewrite-URL", "/admin", "header-routing"),
    ("X-Test", "../../../../etc/passwd", "header-traversal"),
]

COOKIE_PAYLOADS = [
    ("session", "test' OR '1'='1'--", "cookie-sqli"),
    ("prefs", "<script>alert(1)</script>", "cookie-xss"),
    ("file", "../../../../etc/passwd", "cookie-traversal"),
    ("role", "admin", "cookie-tamper"),
]

METHODS_TO_TEST = ["PUT", "DELETE", "TRACE", "OPTIONS", "PATCH"]


ERROR_LEAK_PATTERNS = [
    r"sql syntax",
    r"sqlite",
    r"postgres",
    r"postgresql",
    r"mysql",
    r"mariadb",
    r"sqlalchemy",
    r"prisma",
    r"syntaxerror",
    r"traceback",
    r"stack trace",
    r"exception",
    r"ora-\d+",
    r"odbc",
    r"jdbc",
    r"psycopg",
    r"asyncpg",
    r"warning:",
]


@dataclass
class ProbeResult:
    id: int
    timestamp: str
    category: str
    vector: str
    method: str
    url: str
    path: str
    param_or_field: str | None
    payload_hash: str | None
    payload_preview: str | None
    status: int | str
    elapsed_ms: int
    blocked_or_rejected: bool
    suspicious_allowed: bool
    evidence: list[str]
    marker: str
    audit: dict[str, Any] | None = None
    backend_lookup: dict[str, Any] | None = None


class LinkFormParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: set[str] = set()
        self.forms: list[dict[str, Any]] = []
        self._form: dict[str, Any] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k.lower(): (v or "") for k, v in attrs}
        tag = tag.lower()

        if tag == "a" and attr.get("href"):
            self.links.add(attr["href"])

        if tag == "form":
            self._form = {
                "method": (attr.get("method") or "GET").upper(),
                "action": attr.get("action") or "",
                "inputs": set(),
            }

        if self._form is not None and tag in {"input", "textarea", "select"}:
            name = attr.get("name")
            if name:
                self._form["inputs"].add(name)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "form" and self._form is not None:
            self.forms.append(self._form)
            self._form = None


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def is_safe_local_target(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = parsed.hostname
    if not host:
        return False
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True

    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or ip.is_private
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(host, parsed.port or 80, proto=socket.IPPROTO_TCP)
        for info in infos:
            ip = ipaddress.ip_address(info[4][0])
            if not (ip.is_loopback or ip.is_private):
                return False
        return True
    except OSError:
        return False


def same_origin(url: str, base_url: str) -> bool:
    p = urlparse(url)
    b = urlparse(base_url)
    return p.scheme in {"http", "https"} and p.netloc == b.netloc


def sanitize_preview(value: str, max_len: int = 160) -> str:
    value = value.replace("\r", "\\r").replace("\n", "\\n").replace("\x00", "\\0")
    return value[:max_len]


def payload_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:16]


def http_request(
    method: str,
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = 10,
) -> tuple[int | str, str, int, dict[str, str]]:
    final_headers = {
        "User-Agent": "CyberTrace-local-WAF-probe/1.0",
        "Accept": "text/html,application/json,*/*",
    }
    if headers:
        final_headers.update(headers)
    final_headers.update(cloudflare_access_headers())

    req = Request(url, data=data, method=method, headers=final_headers)
    started = time.perf_counter()

    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read(250_000).decode("utf-8", errors="replace")
            elapsed = int((time.perf_counter() - started) * 1000)
            return int(resp.status), body, elapsed, dict(resp.headers)
    except HTTPError as exc:
        body = exc.read(100_000).decode("utf-8", errors="replace")
        elapsed = int((time.perf_counter() - started) * 1000)
        return int(exc.code), body, elapsed, dict(exc.headers)
    except URLError as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        return "ERR", str(exc.reason), elapsed, {}


def cloudflare_access_headers() -> dict[str, str]:
    """Return optional Cloudflare Access service-token headers.

    Credentials are read only from the process environment and are never part
    of probe results or diagnostic output. A partial configuration is ignored
    so callers can still use the probe for local targets without Access.
    """
    client_id = os.getenv("CF_ACCESS_CLIENT_ID")
    client_secret = os.getenv("CF_ACCESS_CLIENT_SECRET")
    if not client_id or not client_secret:
        return {}
    return {
        "CF-Access-Client-Id": client_id,
        "CF-Access-Client-Secret": client_secret,
    }


def mutate_url(url: str, param: str, value: str, marker: str, *, hpp: bool = False) -> str:
    p = urlparse(url)
    pairs = parse_qsl(p.query, keep_blank_values=True)
    marked_value = f"{value} {marker}"

    if hpp:
        pairs.append((param, "safe"))
        pairs.append((param, marked_value))
    elif not pairs:
        pairs = [(param, marked_value)]
    else:
        found = False
        out = []
        for key, old in pairs:
            if key == param:
                out.append((key, marked_value))
                found = True
            else:
                out.append((key, old))
        if not found:
            out.append((param, marked_value))
        pairs = out

    return urlunparse((p.scheme, p.netloc, p.path, p.params, urlencode(pairs), p.fragment))


def detect_evidence(status: int | str, body: str, headers: dict[str, str], category: str) -> tuple[bool, list[str]]:
    evidence: list[str] = []
    body_lower = body.lower()

    if isinstance(status, int):
        if status in {403, 406, 413, 415, 429}:
            evidence.append(f"blocked_or_rejected_http_{status}")
        elif status in {400, 401, 404, 405, 422}:
            evidence.append(f"app_or_proxy_rejected_http_{status}")
        elif status >= 500:
            evidence.append(f"server_error_http_{status}")

    for pattern in ERROR_LEAK_PATTERNS:
        if re.search(pattern, body_lower):
            evidence.append(f"possible_error_leak:{pattern}")
            break

    if category.startswith("xss") or "xss" in category:
        # Reflection is not always vuln, but unescaped reflection should be reviewed.
        if "<script>alert(1)</script>" in body or "<svg/onload=alert(1)>" in body:
            evidence.append("possible_unescaped_xss_reflection")
        elif html.escape("<script>alert(1)</script>") in body:
            evidence.append("escaped_xss_reflection")

    if "whoami" in body_lower or "uid=" in body_lower or "gid=" in body_lower:
        evidence.append("possible_command_output")

    if "root:x:0:0:" in body_lower or "[extensions]" in body_lower:
        evidence.append("possible_file_disclosure")

    suspicious = False
    if status == 200 and any(
        item.startswith("possible_") for item in evidence
    ):
        suspicious = True

    # These categories are normally expected to block/reject. A 200 needs review.
    if status == 200 and category in {
        "sqli-basic",
        "cmd",
        "traversal",
        "xxe-ish",
        "method-abuse",
        "cookie-sqli",
        "cookie-traversal",
        "form-sqli-basic",
        "form-cmd",
        "form-traversal",
        "json-sqli-basic",
        "json-cmd",
        "json-traversal",
    }:
        suspicious = True
        evidence.append("strong_payload_allowed_review_required")

    return suspicious, evidence


def read_new_audit_events(audit_log: Path, start_pos: int) -> tuple[int, list[dict[str, Any]]]:
    if not audit_log.exists():
        return start_pos, []

    events: list[dict[str, Any]] = []
    with audit_log.open("r", encoding="utf-8", errors="replace") as handle:
        handle.seek(start_pos)
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                if isinstance(event, dict):
                    events.append(event)
            except json.JSONDecodeError:
                continue
        return handle.tell(), events


def summarize_audit(event: dict[str, Any]) -> dict[str, Any]:
    tx = event.get("transaction") if isinstance(event.get("transaction"), dict) else {}
    req = tx.get("request") if isinstance(tx.get("request"), dict) else {}
    messages = tx.get("messages") if isinstance(tx.get("messages"), list) else []

    rule_ids: list[str] = []
    rule_messages: list[str] = []
    tags: list[str] = []
    total_score = None

    for msg in messages:
        if not isinstance(msg, dict):
            continue
        text = str(msg.get("message") or "")
        if text:
            rule_messages.append(text)
            match = re.search(r"Total Score:\s*`?(\d+)`?", text, re.IGNORECASE)
            if match:
                total_score = int(match.group(1))

        details = msg.get("details") if isinstance(msg.get("details"), dict) else {}
        rid = details.get("ruleId")
        if rid is not None:
            rule_ids.append(str(rid))
        raw_tags = details.get("tags")
        if isinstance(raw_tags, list):
            tags.extend(str(t) for t in raw_tags)

    return {
        "transaction_id": str(tx.get("unique_id") or ""),
        "method": req.get("method"),
        "uri": req.get("uri"),
        "host": (req.get("headers") or {}).get("Host") if isinstance(req.get("headers"), dict) else None,
        "client_ip": tx.get("client_ip"),
        "crs_score": total_score if total_score is not None else tx.get("anomaly_score"),
        "rule_ids": list(dict.fromkeys(rule_ids)),
        "messages": list(dict.fromkeys(rule_messages))[:8],
        "tags": list(dict.fromkeys(tags))[:20],
    }


def find_audit_for_marker(events: list[dict[str, Any]], marker: str) -> dict[str, Any] | None:
    for event in reversed(events):
        raw = json.dumps(event, default=str)
        if marker in raw:
            return summarize_audit(event)
    return None


def backend_lookup_via_docker(txid: str, compose_files: list[str], profile: str | None, timeout: int = 45) -> dict[str, Any] | None:
    # Uses backend container's own API_SECRET_KEY so the user does not need to expose secrets on host.
    compose = ["docker", "compose"]
    for f in compose_files:
        compose.extend(["-f", f])
    if profile:
        compose.extend(["--profile", profile])

    py = (
        "import os, urllib.request; "
        "txid=os.environ['TXID']; "
        "secret=os.environ['API_SECRET_KEY']; "
        "req=urllib.request.Request("
        "f'http://127.0.0.1:8000/api/internal/waf-events/{txid}', "
        "headers={'Authorization':'Bearer '+secret}); "
        "print(urllib.request.urlopen(req, timeout=10).read().decode())"
    )

    deadline = time.time() + timeout
    last_error: str | None = None

    while time.time() < deadline:
        cmd = compose + ["exec", "-T", "-e", f"TXID={txid}", "backend", "python", "-c", py]
        try:
            proc = subprocess.run(cmd, text=True, capture_output=True, timeout=20)
            if proc.returncode == 0 and proc.stdout.strip():
                data = json.loads(proc.stdout)
                if data.get("found") is True:
                    return data
                last_error = proc.stdout.strip()
            else:
                last_error = (proc.stderr or proc.stdout).strip()
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(2)

    if last_error:
        return {"found": False, "error": last_error[:500]}
    return {"found": False}


def crawl(base_url: str, common_paths: list[str], max_pages: int, depth: int, timeout: int) -> tuple[set[str], list[dict[str, Any]]]:
    seen: set[str] = set()
    forms: list[dict[str, Any]] = []
    queue: list[tuple[str, int]] = [(urljoin(base_url, p), 0) for p in common_paths]

    while queue and len(seen) < max_pages:
        url, d = queue.pop(0)
        url = url.split("#", 1)[0]
        if url in seen or not same_origin(url, base_url):
            continue

        seen.add(url)
        status, body, _ms, _headers = http_request("GET", url, timeout=timeout)
        if not isinstance(status, int) or status >= 500:
            continue

        parser = LinkFormParser()
        try:
            parser.feed(body)
        except Exception:
            pass

        for form in parser.forms:
            form["page"] = url
            form["action_url"] = urljoin(url, form.get("action") or url)
            form["inputs"] = sorted(form.get("inputs") or [])
            forms.append(form)

        if d < depth:
            for link in parser.links:
                next_url = urljoin(url, link).split("#", 1)[0]
                if same_origin(next_url, base_url) and next_url not in seen:
                    queue.append((next_url, d + 1))

    return seen, forms


def classify_blocked(status: int | str) -> bool:
    return isinstance(status, int) and status in {400, 401, 403, 404, 405, 406, 413, 415, 422, 429}


def add_result(
    results: list[ProbeResult],
    *,
    category: str,
    vector: str,
    method: str,
    url: str,
    param_or_field: str | None,
    payload: str | None,
    status: int | str,
    elapsed_ms: int,
    body: str,
    headers: dict[str, str],
    marker: str,
    audit: dict[str, Any] | None,
    backend_lookup: dict[str, Any] | None,
) -> None:
    suspicious, evidence = detect_evidence(status, body, headers, category)
    parsed = urlparse(url)
    results.append(
        ProbeResult(
            id=len(results) + 1,
            timestamp=now_iso(),
            category=category,
            vector=vector,
            method=method,
            url=url,
            path=parsed.path or "/",
            param_or_field=param_or_field,
            payload_hash=payload_hash(payload) if payload is not None else None,
            payload_preview=sanitize_preview(payload) if payload is not None else None,
            status=status,
            elapsed_ms=elapsed_ms,
            blocked_or_rejected=classify_blocked(status),
            suspicious_allowed=suspicious,
            evidence=evidence,
            marker=marker,
            audit=audit,
            backend_lookup=backend_lookup,
        )
    )


def run() -> int:
    parser = argparse.ArgumentParser(description="Run serious local WAF probes and save JSON evidence.")
    parser.add_argument("--base-url", default="http://localhost:8089", help="WAF-protected target base URL")
    parser.add_argument("--audit-log", default="./logs/modsecurity/demo-target/modsec_audit.jsonl", help="ModSecurity audit JSONL path")
    parser.add_argument("--output", default=None, help="Output JSON path")
    parser.add_argument("--max-pages", type=int, default=80, help="Max pages to crawl")
    parser.add_argument("--depth", type=int, default=2, help="Crawl depth")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout seconds")
    parser.add_argument("--delay", type=float, default=0.03, help="Delay between requests")
    parser.add_argument("--max-tests", type=int, default=1600, help="Max probe requests after crawl")
    parser.add_argument("--seed", type=int, default=1337, help="Shuffle seed")
    parser.add_argument("--allow-non-local", action="store_true", help="Allow non-local targets; only use with permission")
    parser.add_argument("--verify-backend", action="store_true", help="For blocked/audited events, query CyberTrace backend through docker compose exec")
    parser.add_argument("--backend-verify-limit", type=int, default=40, help="Max backend lookups to attempt")
    parser.add_argument("--compose-file", action="append", default=["docker-compose.yml", "docker-compose.demo-target.yml"], help="Compose file(s) for backend lookup")
    parser.add_argument("--compose-profile", default="demo-target", help="Compose profile for backend lookup")
    parser.add_argument("--aggressive", action="store_true", help="Increase payload/path combinations")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    if not args.allow_non_local and not is_safe_local_target(base_url):
        print(f"Refusing to test non-local target without --allow-non-local: {base_url}", file=sys.stderr)
        return 2
    access_id = os.getenv("CF_ACCESS_CLIENT_ID")
    access_secret = os.getenv("CF_ACCESS_CLIENT_SECRET")
    if args.allow_non_local and bool(access_id) != bool(access_secret):
        print(
            "CF_ACCESS_CLIENT_ID and CF_ACCESS_CLIENT_SECRET must be set together.",
            file=sys.stderr,
        )
        return 2

    random.seed(args.seed)
    audit_log = Path(args.audit_log)
    audit_pos = audit_log.stat().st_size if audit_log.exists() else 0

    common_paths = list(DEFAULT_COMMON_PATHS)
    discovered, forms = crawl(base_url, common_paths, args.max_pages, args.depth, args.timeout)
    targets = sorted(discovered | {urljoin(base_url, p) for p in common_paths})
    random.shuffle(targets)

    # Keep health endpoints in scan, but limit them so results are not dominated by healthz.
    health_targets = [u for u in targets if urlparse(u).path in {"/health", "/healthz", "/api/health"}]
    non_health_targets = [u for u in targets if u not in health_targets]
    targets = non_health_targets + health_targets[:3]

    results: list[ProbeResult] = []
    backend_lookups_used = 0

    def maybe_audit_and_backend(marker: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        nonlocal audit_pos, backend_lookups_used
        time.sleep(0.05)
        audit_pos, events = read_new_audit_events(audit_log, audit_pos)
        audit = find_audit_for_marker(events, marker)
        backend = None
        if (
            args.verify_backend
            and audit
            and audit.get("transaction_id")
            and backend_lookups_used < args.backend_verify_limit
        ):
            backend_lookups_used += 1
            backend = backend_lookup_via_docker(
                str(audit["transaction_id"]),
                compose_files=args.compose_file,
                profile=args.compose_profile,
                timeout=45,
            )
        return audit, backend

    def should_stop() -> bool:
        return len(results) >= args.max_tests

    # Baseline clean checks.
    for url in targets[: min(len(targets), 40)]:
        if should_stop():
            break
        marker = f"BASE-{int(time.time())}-{len(results)+1}"
        status, body, ms, headers = http_request("GET", url, timeout=args.timeout)
        add_result(
            results,
            category="baseline",
            vector="clean-get",
            method="GET",
            url=url,
            param_or_field=None,
            payload=None,
            status=status,
            elapsed_ms=ms,
            body=body,
            headers=headers,
            marker=marker,
            audit=None,
            backend_lookup=None,
        )
        time.sleep(args.delay)

    # Query parameter fuzzing.
    categories = list(PAYLOADS.keys())
    if not args.aggressive:
        # Still serious, but keeps runtime reasonable.
        categories = ["sqli-basic", "xss", "cmd", "traversal", "ssti-template", "edge-long"]

    for url in targets:
        if should_stop():
            break
        existing = [k for k, _ in parse_qsl(urlparse(url).query, keep_blank_values=True)]
        params = existing or COMMON_PARAM_NAMES
        params = params[:18 if args.aggressive else 10]

        for category in categories:
            for param in params:
                for payload in PAYLOADS[category]:
                    if should_stop():
                        break
                    marker = f"CT-{category}-{len(results)+1}-{int(time.time())}"
                    attack_url = mutate_url(url, param, payload, marker)
                    status, body, ms, headers = http_request("GET", attack_url, timeout=args.timeout)
                    audit, backend = maybe_audit_and_backend(marker)
                    add_result(
                        results,
                        category=category,
                        vector="query-param",
                        method="GET",
                        url=attack_url,
                        param_or_field=param,
                        payload=payload,
                        status=status,
                        elapsed_ms=ms,
                        body=body,
                        headers=headers,
                        marker=marker,
                        audit=audit,
                        backend_lookup=backend,
                    )
                    time.sleep(args.delay)

                # HTTP parameter pollution.
                if should_stop():
                    break
                marker = f"CT-hpp-{len(results)+1}-{int(time.time())}"
                attack_url = mutate_url(url, param, "' OR '1'='1'--", marker, hpp=True)
                status, body, ms, headers = http_request("GET", attack_url, timeout=args.timeout)
                audit, backend = maybe_audit_and_backend(marker)
                add_result(
                    results,
                    category="hpp-sqli",
                    vector="duplicate-query-param",
                    method="GET",
                    url=attack_url,
                    param_or_field=param,
                    payload="' OR '1'='1'--",
                    status=status,
                    elapsed_ms=ms,
                    body=body,
                    headers=headers,
                    marker=marker,
                    audit=audit,
                    backend_lookup=backend,
                )
                time.sleep(args.delay)

    # Form-derived POST/GET fuzzing.
    if not should_stop():
        guessed_forms = [
            {"method": "POST", "action_url": urljoin(base_url, p), "inputs": ["name", "email", "query", "message", "comment", "password"]}
            for p in [
                "/login",
                "/login/submit",
                "/records/search",
                "/appointments/submit",
                "/comments/submit",
                "/support/submit",
                "/transactions/status",
                "/records/LND-2026-0001/request-copy/submit",
            ]
        ]
        forms_to_test = forms + guessed_forms
        for form in forms_to_test:
            if should_stop():
                break
            method = str(form.get("method") or "POST").upper()
            if method not in {"GET", "POST", "PATCH"}:
                method = "POST"
            action_url = str(form.get("action_url") or base_url)
            fields = list(form.get("inputs") or ["query"])
            fields = fields[:12]

            form_categories = ["sqli-basic", "xss", "cmd", "traversal", "edge-long"]
            for category in form_categories:
                for field in fields:
                    for payload in PAYLOADS[category]:
                        if should_stop():
                            break
                        marker = f"CT-form-{category}-{len(results)+1}-{int(time.time())}"
                        data = {name: "test" for name in fields}
                        data[field] = f"{payload} {marker}"
                        if method == "GET":
                            sep = "&" if "?" in action_url else "?"
                            attack_url = action_url + sep + urlencode(data)
                            status, body, ms, headers = http_request("GET", attack_url, timeout=args.timeout)
                        else:
                            encoded = urlencode(data).encode()
                            status, body, ms, headers = http_request(
                                method,
                                action_url,
                                data=encoded,
                                headers={"Content-Type": "application/x-www-form-urlencoded"},
                                timeout=args.timeout,
                            )
                            attack_url = action_url
                        audit, backend = maybe_audit_and_backend(marker)
                        add_result(
                            results,
                            category=f"form-{category}",
                            vector="form-body",
                            method=method,
                            url=attack_url,
                            param_or_field=field,
                            payload=payload,
                            status=status,
                            elapsed_ms=ms,
                            body=body,
                            headers=headers,
                            marker=marker,
                            audit=audit,
                            backend_lookup=backend,
                        )
                        time.sleep(args.delay)

    # JSON body fuzzing.
    if not should_stop():
        json_targets = [
            urljoin(base_url, p)
            for p in [
                "/api/login",
                "/api/records",
                "/api/records/search",
                "/api/appointments",
                "/api/comments",
                "/api/support",
                "/api/transactions/status",
                "/records/search",
            ]
        ]
        for target in json_targets:
            if should_stop():
                break
            for category in ["sqli-basic", "xss", "cmd", "traversal", "nosql-ish", "edge-long"]:
                for payload in PAYLOADS[category]:
                    if should_stop():
                        break
                    marker = f"CT-json-{category}-{len(results)+1}-{int(time.time())}"
                    body_obj = {
                        "query": f"{payload} {marker}",
                        "id": f"1 {marker}",
                        "name": f"Test {marker}",
                        "email": "probe@example.test",
                        "message": f"{payload} {marker}",
                    }
                    if category == "nosql-ish":
                        try:
                            body_obj["query"] = json.loads(payload)
                        except json.JSONDecodeError:
                            body_obj["query"] = payload
                    data = json.dumps(body_obj).encode()
                    status, body, ms, headers = http_request(
                        "POST",
                        target,
                        data=data,
                        headers={"Content-Type": "application/json"},
                        timeout=args.timeout,
                    )
                    audit, backend = maybe_audit_and_backend(marker)
                    add_result(
                        results,
                        category=f"json-{category}",
                        vector="json-body",
                        method="POST",
                        url=target,
                        param_or_field="query/message",
                        payload=payload,
                        status=status,
                        elapsed_ms=ms,
                        body=body,
                        headers=headers,
                        marker=marker,
                        audit=audit,
                        backend_lookup=backend,
                    )
                    time.sleep(args.delay)

    # Header fuzzing.
    if not should_stop():
        for url in targets[:30]:
            if should_stop():
                break
            for header_name, header_value, category in HEADER_PAYLOADS:
                marker = f"CT-header-{category}-{len(results)+1}-{int(time.time())}"
                value = f"{header_value} {marker}"
                status, body, ms, headers = http_request(
                    "GET",
                    url,
                    headers={header_name: value},
                    timeout=args.timeout,
                )
                audit, backend = maybe_audit_and_backend(marker)
                add_result(
                    results,
                    category=category,
                    vector="header",
                    method="GET",
                    url=url,
                    param_or_field=header_name,
                    payload=header_value,
                    status=status,
                    elapsed_ms=ms,
                    body=body,
                    headers=headers,
                    marker=marker,
                    audit=audit,
                    backend_lookup=backend,
                )
                time.sleep(args.delay)

    # Cookie fuzzing.
    if not should_stop():
        for url in targets[:30]:
            if should_stop():
                break
            for cookie_name, cookie_value, category in COOKIE_PAYLOADS:
                marker = f"CT-cookie-{category}-{len(results)+1}-{int(time.time())}"
                cookie = f"{cookie_name}={quote(cookie_value + ' ' + marker)}"
                status, body, ms, headers = http_request(
                    "GET",
                    url,
                    headers={"Cookie": cookie},
                    timeout=args.timeout,
                )
                audit, backend = maybe_audit_and_backend(marker)
                add_result(
                    results,
                    category=category,
                    vector="cookie",
                    method="GET",
                    url=url,
                    param_or_field=cookie_name,
                    payload=cookie_value,
                    status=status,
                    elapsed_ms=ms,
                    body=body,
                    headers=headers,
                    marker=marker,
                    audit=audit,
                    backend_lookup=backend,
                )
                time.sleep(args.delay)

    # Method abuse.
    if not should_stop():
        for url in targets[:40]:
            if should_stop():
                break
            for method in METHODS_TO_TEST:
                marker = f"CT-method-{method}-{len(results)+1}-{int(time.time())}"
                attack_url = mutate_url(url, "marker", "method-test", marker)
                status, body, ms, headers = http_request(method, attack_url, timeout=args.timeout)
                audit, backend = maybe_audit_and_backend(marker)
                add_result(
                    results,
                    category="method-abuse",
                    vector="http-method",
                    method=method,
                    url=attack_url,
                    param_or_field=None,
                    payload=method,
                    status=status,
                    elapsed_ms=ms,
                    body=body,
                    headers=headers,
                    marker=marker,
                    audit=audit,
                    backend_lookup=backend,
                )
                time.sleep(args.delay)

    # Summaries.
    status_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    suspicious = []
    audited = 0
    backend_found = 0

    for item in results:
        status_counts[str(item.status)] = status_counts.get(str(item.status), 0) + 1
        category_counts[item.category] = category_counts.get(item.category, 0) + 1
        if item.suspicious_allowed:
            suspicious.append(item.id)
        if item.audit:
            audited += 1
        if item.backend_lookup and item.backend_lookup.get("found") is True:
            backend_found += 1

    report = {
        "metadata": {
            "generated_at": now_iso(),
            "base_url": base_url,
            "audit_log": str(audit_log),
            "max_tests": args.max_tests,
            "verify_backend": args.verify_backend,
            "backend_lookups_used": backend_lookups_used,
            "safety": "Local/private targets only unless --allow-non-local is explicitly used.",
        },
        "coverage": {
            "discovered_urls": sorted(discovered),
            "tested_url_count": len(targets),
            "discovered_forms": forms,
            "total_results": len(results),
        },
        "summary": {
            "status_counts": status_counts,
            "category_counts": category_counts,
            "blocked_or_rejected_count": sum(1 for r in results if r.blocked_or_rejected),
            "suspicious_allowed_count": len(suspicious),
            "suspicious_allowed_ids": suspicious[:200],
            "audit_matched_count": audited,
            "backend_found_count": backend_found,
        },
        "results": [asdict(r) for r in results],
        "interpretation": {
            "pass_signals": [
                "403/406/413/415/429 usually means WAF or proxy blocked/rejected.",
                "405 usually means app/proxy rejected the method; acceptable for TRACE/unsafe methods.",
                "CRS audit rule IDs plus score are stronger evidence than HTTP status alone.",
                "backend_lookup.found=true proves CyberTrace ingested the WAF event.",
            ],
            "review_signals": [
                "status=200 with strong_payload_allowed_review_required",
                "possible_error_leak",
                "possible_unescaped_xss_reflection",
                "possible_command_output",
                "possible_file_disclosure",
                "PATCH/unsafe methods returning 200 if the app does not need them.",
            ],
        },
    }

    if args.output:
        output = Path(args.output)
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = Path(f"waf_probe_{stamp}.json")

    output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n=== CyberTrace WAF Probe Summary ===")
    print(f"Target: {base_url}")
    print(f"Results: {len(results)}")
    print(f"Output: {output}")
    print(f"Status counts: {status_counts}")
    print(f"Suspicious allowed: {len(suspicious)}")
    print(f"Audit matched: {audited}")
    if args.verify_backend:
        print(f"Backend found: {backend_found}/{backend_lookups_used} attempted lookups")

    if suspicious:
        print("\nSuspicious allowed IDs to review:")
        print(", ".join(str(x) for x in suspicious[:80]))

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
