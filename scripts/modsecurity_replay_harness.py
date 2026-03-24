from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
import urllib.error
import urllib.request
from urllib.parse import unquote, urlsplit
from uuid import uuid4


DEFAULT_HELDOUT_JSON = Path(
    r"G:\Documents\PDDDD\injection-alert-system\data\processed\v3_907k_cleaned\sample_exports\heldout_test_15.json"
)
DEFAULT_QUARANTINE_JSON = Path(
    r"G:\Documents\PDDDD\injection-alert-system\data\processed\v3_907k_cleaned\sample_exports\quarantine_15.json"
)
DEFAULT_REPORT_ROOT = Path("reports/modsecurity-replay")
REPLAY_HEADER_NAME = "X-Replay-Tx"


@dataclass(frozen=True)
class ReplayRow:
    replay_tx: str
    method: str
    path: str
    query_string: str | None
    body: str
    skip_reason: str | None


@dataclass(frozen=True)
class ModSecurityDetection:
    detected: bool
    transaction_id: str | None
    source_ip: str | None
    timestamp: str
    rule_ids: list[str]
    messages: list[str]
    tags: list[str]
    request_headers: dict[str, str]
    raw_event: dict[str, Any] | None


@dataclass(frozen=True)
class ReportRows:
    summary: dict[str, int]
    rows: list[dict[str, Any]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_default_samples(heldout_json: Path, quarantine_json: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in (heldout_json, quarantine_json):
        with path.open("r", encoding="utf-8") as handle:
            parsed = json.load(handle)
            if not isinstance(parsed, list):
                raise ValueError(f"Expected list in {path}")
            rows.extend(item for item in parsed if isinstance(item, dict))
    return rows


def _best_effort_path(raw_path: str) -> tuple[str, str | None]:
    if not raw_path:
        return "", None

    cleaned = raw_path.strip().replace("\\/", "/")
    parsed = urlsplit(cleaned)
    path = parsed.path or cleaned
    query = parsed.query or None

    path = unquote(path)
    if not path.startswith("/"):
        path = f"/{path}"

    return path, query


def normalize_sample_row(row: dict[str, Any], *, replay_tx: str) -> ReplayRow:
    method = str(row.get("request_http_method") or row.get("canonical_method") or "GET")
    method = method.strip().upper() or "GET"

    raw_path = str(
        row.get("request_http_request")
        or row.get("canonical_path")
        or row.get("request_path")
        or ""
    ).strip()
    if not raw_path:
        return ReplayRow(
            replay_tx=replay_tx,
            method=method,
            path="",
            query_string=None,
            body="",
            skip_reason="missing request path",
        )

    path, query_string = _best_effort_path(raw_path)
    if not path:
        return ReplayRow(
            replay_tx=replay_tx,
            method=method,
            path="",
            query_string=None,
            body="",
            skip_reason="invalid request path",
        )

    if any(char.isspace() for char in path) or "{{" in path or "}}" in path:
        return ReplayRow(
            replay_tx=replay_tx,
            method=method,
            path=path,
            query_string=query_string,
            body="",
            skip_reason="unreplayable request path contains template/control characters",
        )

    body = row.get("request_body")
    if body is None:
        body = ""

    return ReplayRow(
        replay_tx=replay_tx,
        method=method,
        path=path,
        query_string=query_string,
        body=str(body),
        skip_reason=None,
    )


def _extract_json_log_payload(line: str) -> dict[str, Any] | None:
    start = line.find("{")
    if start < 0:
        return None
    candidate = line[start:].strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        parsed = None
        # Some log lines can contain trailing non-JSON characters. Recover by
        # trimming from the right until a valid JSON object is found.
        for end in range(len(candidate) - 1, 1, -1):
            snippet = candidate[:end].strip()
            if not snippet.endswith("}"):
                continue
            try:
                parsed = json.loads(snippet)
                break
            except json.JSONDecodeError:
                continue
        if parsed is None:
            return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def detect_modsecurity_events(logs_text: str, *, replay_tx: str) -> ModSecurityDetection:
    for line in logs_text.splitlines():
        payload = _extract_json_log_payload(line)
        if payload is None:
            continue

        transaction = payload.get("transaction")
        if not isinstance(transaction, dict):
            continue

        request = transaction.get("request")
        if not isinstance(request, dict):
            continue

        headers = request.get("headers")
        headers = headers if isinstance(headers, dict) else {}
        headers_norm = {str(k): str(v) for k, v in headers.items()}
        headers_lower = {str(k).lower(): str(v) for k, v in headers.items()}
        replay_header_value = headers_lower.get(REPLAY_HEADER_NAME.lower())
        if replay_header_value != replay_tx:
            continue

        messages_raw = transaction.get("messages")
        messages_raw = messages_raw if isinstance(messages_raw, list) else []

        rule_ids: list[str] = []
        message_texts: list[str] = []
        tags: list[str] = []

        for message in messages_raw:
            if not isinstance(message, dict):
                continue
            message_text = message.get("message")
            if message_text is not None:
                message_texts.append(str(message_text))

            details = message.get("details")
            if isinstance(details, dict):
                rule_id = details.get("ruleId")
                if rule_id is not None:
                    rule_ids.append(str(rule_id))
                details_tags = details.get("tags")
                if isinstance(details_tags, list):
                    tags.extend(str(tag) for tag in details_tags)

        return ModSecurityDetection(
            detected=len(messages_raw) > 0,
            transaction_id=str(transaction.get("unique_id") or transaction.get("id") or replay_tx),
            source_ip=str(transaction.get("client_ip") or "unknown"),
            timestamp=_utc_now(),
            rule_ids=list(dict.fromkeys(rule_ids)),
            messages=list(dict.fromkeys(message_texts)),
            tags=list(dict.fromkeys(tags)),
            request_headers=headers_norm,
            raw_event=payload,
        )

    return ModSecurityDetection(
        detected=False,
        transaction_id=None,
        source_ip=None,
        timestamp=_utc_now(),
        rule_ids=[],
        messages=[],
        tags=[],
        request_headers={},
        raw_event=None,
    )


def build_waf_ingest_payload(replay: ReplayRow, detection: ModSecurityDetection) -> dict[str, Any]:
    if not detection.detected:
        raise ValueError("Cannot build ingest payload without detection evidence")

    return {
        "ingest_source": "modsec_audit_bridge",
        "transaction_id": detection.transaction_id or replay.replay_tx,
        "timestamp": detection.timestamp,
        "source_ip": detection.source_ip or "unknown",
        "request_method": replay.method,
        "request_path": replay.path,
        "query_string": replay.query_string,
        "request_headers": detection.request_headers,
        "sanitized_body": "",
        "crs_score": max(5, len(detection.rule_ids)),
        "crs_rule_ids": detection.rule_ids or ["unknown-rule"],
        "matched_rule_messages": detection.messages or None,
        "matched_rule_tags": detection.tags or None,
    }


def _http_request(
    *,
    method: str,
    url: str,
    headers: dict[str, str],
    body: str,
    timeout: int,
) -> tuple[int, str, dict[str, str]]:
    payload = body.encode("utf-8") if body and method in {"POST", "PUT", "PATCH", "DELETE"} else None
    request = urllib.request.Request(url, data=payload, method=method, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            response_headers = {k: v for k, v in response.headers.items()}
            return int(response.status), response_body, response_headers
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        response_headers = {k: v for k, v in exc.headers.items()}
        return int(exc.code), body_text, response_headers


def _run_compose_logs_since(since_iso: str) -> str:
    result = subprocess.run(
        ["docker", "compose", "logs", "modsecurity", "--since", since_iso],
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout or "") + ("\n" + result.stderr if result.stderr else "")


def _post_ingest_event(payload: dict[str, Any], *, endpoint: str, internal_api_key: str, timeout: int) -> int:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {internal_api_key}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return int(response.status)


def _post_ingest_event_via_backend_compose(payload: dict[str, Any], *, internal_api_key: str, timeout: int) -> int:
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "backend",
        "python",
        "-c",
        (
            "import json,sys,urllib.request,urllib.error; "
            "payload=json.load(sys.stdin); "
            "req=urllib.request.Request("
            "'http://localhost:8000/api/internal/waf-events',"
            "data=json.dumps(payload).encode('utf-8'),"
            "method='POST',"
            "headers={'Content-Type':'application/json','Authorization':'Bearer '+sys.argv[1]}"
            "); "
            "\n"
            "try:\n"
            "  with urllib.request.urlopen(req, timeout=int(sys.argv[2])) as resp:\n"
            "    print(resp.status)\n"
            "except urllib.error.HTTPError as exc:\n"
            "  print(exc.code)\n"
        ),
        internal_api_key,
        str(timeout),
    ]
    result = subprocess.run(
        command,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout or "").strip().splitlines()
    if not output:
        raise RuntimeError(f"backend compose ingest failed: {result.stderr.strip()}")
    try:
        return int(output[-1].strip())
    except ValueError as exc:
        raise RuntimeError(f"unexpected ingest status output: {result.stdout}") from exc


def _lookup_downstream(transaction_id: str, *, endpoint: str, internal_api_key: str, timeout: int) -> tuple[bool, str]:
    request = urllib.request.Request(
        endpoint.rstrip("/") + f"/{transaction_id}",
        method="GET",
        headers={"Authorization": f"Bearer {internal_api_key}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(body)
        found = bool(parsed.get("found"))
        return found, body


def _lookup_downstream_via_backend_compose(
    transaction_id: str,
    *,
    internal_api_key: str,
    timeout: int,
) -> tuple[bool, str]:
    command = [
        "docker",
        "compose",
        "exec",
        "-T",
        "backend",
        "python",
        "-c",
        (
            "import json,sys,urllib.request,urllib.error; "
            "req=urllib.request.Request("
            "'http://localhost:8000/api/internal/waf-events/'+sys.argv[1],"
            "method='GET',"
            "headers={'Authorization':'Bearer '+sys.argv[2]}"
            "); "
            "\n"
            "try:\n"
            "  with urllib.request.urlopen(req, timeout=int(sys.argv[3])) as resp:\n"
            "    print(resp.read().decode('utf-8', errors='replace'))\n"
            "except urllib.error.HTTPError as exc:\n"
            "  body=exc.read().decode('utf-8', errors='replace')\n"
            "  print(body if body else json.dumps({'found': False, 'transaction_id': sys.argv[1]}))\n"
        ),
        transaction_id,
        internal_api_key,
        str(timeout),
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    body = (result.stdout or "").strip()
    if not body:
        raise RuntimeError(f"backend compose lookup failed: {result.stderr.strip()}")
    parsed = json.loads(body)
    return bool(parsed.get("found")), body


def build_report_rows(run_rows: list[dict[str, Any]]) -> ReportRows:
    total = len(run_rows)
    skipped = sum(1 for row in run_rows if row.get("skip_reason"))
    replayed = sum(1 for row in run_rows if not row.get("skip_reason"))
    detected = sum(
        1
        for row in run_rows
        if row.get("response_ok") and row.get("modsec_detected")
    )
    downstream = sum(
        1
        for row in run_rows
        if row.get("response_ok") and row.get("modsec_detected") and row.get("downstream_stored")
    )
    failures = sum(1 for row in run_rows if row.get("failure"))

    return ReportRows(
        summary={
            "total": total,
            "replayed": replayed,
            "skipped": skipped,
            "detected_by_modsec": detected,
            "downstream_stored": downstream,
            "failures": failures,
        },
        rows=run_rows,
    )


def write_reports(
    *,
    output_dir: Path,
    report: ReportRows,
    response_artifacts: dict[str, str],
    modsec_artifacts: dict[str, str],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    responses_dir = output_dir / "responses"
    modsec_dir = output_dir / "modsecurity"
    responses_dir.mkdir(parents=True, exist_ok=True)
    modsec_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / "report.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "summary": report.summary,
                "rows": report.rows,
            },
            handle,
            indent=2,
        )

    csv_fieldnames = [
        "row_index",
        "replay_tx",
        "response_status",
        "response_ok",
        "modsec_detected",
        "downstream_stored",
        "skip_reason",
        "failure",
    ]
    with (output_dir / "report.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fieldnames)
        writer.writeheader()
        for row in report.rows:
            writer.writerow({key: row.get(key) for key in csv_fieldnames})

    for replay_tx, content in response_artifacts.items():
        (responses_dir / f"{replay_tx}.txt").write_text(content, encoding="utf-8")

    for replay_tx, content in modsec_artifacts.items():
        (modsec_dir / f"{replay_tx}.log").write_text(content, encoding="utf-8")

    summary_lines = [
        f"total: {report.summary['total']}",
        f"replayed: {report.summary['replayed']}",
        f"skipped: {report.summary['skipped']}",
        f"detected_by_modsec: {report.summary['detected_by_modsec']}",
        f"downstream_stored: {report.summary['downstream_stored']}",
        f"failures: {report.summary['failures']}",
    ]
    (output_dir / "summary.txt").write_text("\n".join(summary_lines) + "\n", encoding="utf-8")


def run_replay_harness(
    *,
    heldout_json: Path,
    quarantine_json: Path,
    modsec_base_url: str,
    ingest_endpoint: str,
    lookup_endpoint: str,
    internal_api_key: str,
    timeout_seconds: int,
    pause_after_request_seconds: float,
    report_root: Path,
) -> tuple[Path, ReportRows]:
    all_rows = load_default_samples(heldout_json, quarantine_json)
    selected_rows = all_rows[:30]

    run_timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = report_root / run_timestamp

    run_rows: list[dict[str, Any]] = []
    response_artifacts: dict[str, str] = {}
    modsec_artifacts: dict[str, str] = {}

    for index, row in enumerate(selected_rows, start=1):
        replay_tx = f"replay-{index:02d}-{uuid4().hex[:12]}"
        replay = normalize_sample_row(row, replay_tx=replay_tx)

        if replay.skip_reason:
            run_rows.append(
                {
                    "row_index": index,
                    "replay_tx": replay_tx,
                    "response_status": None,
                    "response_ok": False,
                    "modsec_detected": False,
                    "downstream_stored": False,
                    "skip_reason": replay.skip_reason,
                    "failure": None,
                }
            )
            continue

        url = modsec_base_url.rstrip("/") + replay.path
        if replay.query_string:
            url = f"{url}?{replay.query_string}"

        since_iso = _utc_now()
        headers = {
            "User-Agent": "modsecurity-replay-harness/1.0",
            REPLAY_HEADER_NAME: replay_tx,
            "Accept": "*/*",
        }
        if replay.body and replay.method in {"POST", "PUT", "PATCH", "DELETE"}:
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        response_status: int | None = None
        response_ok = False
        failure: str | None = None
        downstream_stored = False

        try:
            status, response_body, response_headers = _http_request(
                method=replay.method,
                url=url,
                headers=headers,
                body=replay.body,
                timeout=timeout_seconds,
            )
            response_status = status
            response_ok = True
            response_artifacts[replay_tx] = (
                f"url={url}\n"
                f"status={status}\n"
                f"headers={json.dumps(response_headers, indent=2)}\n"
                f"body=\n{response_body}\n"
            )
        except Exception as exc:  # noqa: BLE001
            failure = str(exc)
            response_artifacts[replay_tx] = f"url={url}\nerror={exc}\n"

        if pause_after_request_seconds > 0:
            time.sleep(pause_after_request_seconds)

        logs_text = _run_compose_logs_since(since_iso)
        detection = detect_modsecurity_events(logs_text, replay_tx=replay_tx)
        modsec_artifacts[replay_tx] = logs_text

        if response_ok and detection.detected:
            try:
                ingest_payload = build_waf_ingest_payload(replay, detection)
                try:
                    ingest_status = _post_ingest_event(
                        ingest_payload,
                        endpoint=ingest_endpoint,
                        internal_api_key=internal_api_key,
                        timeout=timeout_seconds,
                    )
                except Exception:
                    ingest_status = _post_ingest_event_via_backend_compose(
                        ingest_payload,
                        internal_api_key=internal_api_key,
                        timeout=timeout_seconds,
                    )

                if 200 <= ingest_status < 300:
                    try:
                        found, lookup_raw = _lookup_downstream(
                            ingest_payload["transaction_id"],
                            endpoint=lookup_endpoint,
                            internal_api_key=internal_api_key,
                            timeout=timeout_seconds,
                        )
                    except Exception:
                        found, lookup_raw = _lookup_downstream_via_backend_compose(
                            ingest_payload["transaction_id"],
                            internal_api_key=internal_api_key,
                            timeout=timeout_seconds,
                        )
                    downstream_stored = found
                    modsec_artifacts[replay_tx] += f"\n\nlookup_response=\n{lookup_raw}\n"
                else:
                    failure = f"waf ingest returned status={ingest_status}"
            except Exception as exc:  # noqa: BLE001
                if failure:
                    failure = f"{failure}; ingest_or_lookup_error={exc}"
                else:
                    failure = f"ingest_or_lookup_error={exc}"

        run_rows.append(
            {
                "row_index": index,
                "replay_tx": replay_tx,
                "response_status": response_status,
                "response_ok": response_ok,
                "modsec_detected": detection.detected,
                "downstream_stored": downstream_stored,
                "skip_reason": None,
                "failure": failure,
            }
        )

    report = build_report_rows(run_rows)
    write_reports(
        output_dir=output_dir,
        report=report,
        response_artifacts=response_artifacts,
        modsec_artifacts=modsec_artifacts,
    )

    return output_dir, report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Replay 30 sample HTTP rows through host-exposed ModSecurity and prove detection + downstream storage."
    )
    parser.add_argument("--heldout-json", type=Path, default=DEFAULT_HELDOUT_JSON)
    parser.add_argument("--quarantine-json", type=Path, default=DEFAULT_QUARANTINE_JSON)
    parser.add_argument("--modsec-base-url", default="http://localhost:8088")
    parser.add_argument(
        "--ingest-endpoint",
        default="http://localhost:8088/api/internal/waf-events",
    )
    parser.add_argument(
        "--lookup-endpoint",
        default="http://localhost:8088/api/internal/waf-events",
    )
    parser.add_argument(
        "--internal-api-key",
        default=None,
        help="Defaults to API_SECRET_KEY from environment.",
    )
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--pause-after-request", type=float, default=0.3)
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    args = parser.parse_args()

    internal_api_key = args.internal_api_key
    if not internal_api_key:
        internal_api_key = str(
            (Path(".env").read_text(encoding="utf-8") if Path(".env").exists() else "")
        )
        if "API_SECRET_KEY=" in internal_api_key:
            for line in internal_api_key.splitlines():
                if line.startswith("API_SECRET_KEY="):
                    internal_api_key = line.split("=", 1)[1].strip()
                    break
        else:
            internal_api_key = ""

    if not internal_api_key:
        print("internal API key is required via --internal-api-key or .env API_SECRET_KEY", file=sys.stderr)
        return 2

    output_dir, report = run_replay_harness(
        heldout_json=args.heldout_json,
        quarantine_json=args.quarantine_json,
        modsec_base_url=args.modsec_base_url,
        ingest_endpoint=args.ingest_endpoint,
        lookup_endpoint=args.lookup_endpoint,
        internal_api_key=internal_api_key,
        timeout_seconds=max(1, args.timeout),
        pause_after_request_seconds=max(0.0, args.pause_after_request),
        report_root=args.report_root,
    )

    summary = report.summary
    print(f"report_dir={output_dir}")
    print(f"total={summary['total']}")
    print(f"replayed={summary['replayed']}")
    print(f"skipped={summary['skipped']}")
    print(f"detected_by_modsec={summary['detected_by_modsec']}")
    print(f"downstream_stored={summary['downstream_stored']}")
    print(f"failures={summary['failures']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())