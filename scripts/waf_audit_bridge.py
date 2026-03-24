from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import sys
import time
from typing import Any, TextIO
import urllib.error
import urllib.request
from urllib.parse import urljoin
from uuid import uuid4


_SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie"}
_SENSITIVE_SUBSTRINGS = ("token", "secret", "key", "credential")
_MAX_BODY_LENGTH = 1024
_RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
_RETRYABLE_ERRNOS = {61, 111, 10061}


def _redact_headers(headers: dict[str, Any]) -> dict[str, str]:
    sanitized: dict[str, str] = {}
    for key, value in headers.items():
        key_str = str(key)
        lower_key = key_str.lower()
        if lower_key in _SENSITIVE_HEADERS or any(
            part in lower_key for part in _SENSITIVE_SUBSTRINGS
        ):
            sanitized[key_str] = "[REDACTED]"
        else:
            sanitized[key_str] = str(value)
    return sanitized


def _truncate_body(body: str | None) -> str | None:
    if body is None:
        return None
    return body[:_MAX_BODY_LENGTH]


def _split_path_and_query(uri: str) -> tuple[str, str | None]:
    if "?" not in uri:
        return uri, None
    path, query = uri.split("?", 1)
    return path, query or None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_rule_metadata(
    messages: list[dict[str, Any]],
) -> tuple[list[str], list[str], list[str]]:
    rule_ids: list[str] = []
    matched_messages: list[str] = []
    matched_tags: list[str] = []

    for message in messages:
        if not isinstance(message, dict):
            continue

        details = message.get("details")
        if isinstance(details, dict):
            rule_id = details.get("ruleId")
            if rule_id is not None:
                rule_ids.append(str(rule_id))

            tags = details.get("tags")
            if isinstance(tags, list):
                for tag in tags:
                    matched_tags.append(str(tag))

        text = message.get("message")
        if text is not None:
            matched_messages.append(str(text))

    # preserve order, drop duplicates
    dedup_rule_ids = list(dict.fromkeys(rule_ids))
    dedup_messages = list(dict.fromkeys(matched_messages))
    dedup_tags = list(dict.fromkeys(matched_tags))
    return dedup_rule_ids, dedup_messages, dedup_tags


def normalize_event(raw_event: dict[str, Any]) -> dict[str, Any]:
    transaction = raw_event.get("transaction")
    if isinstance(transaction, dict):
        request = transaction.get("request")
        request = request if isinstance(request, dict) else {}
        uri = str(request.get("uri") or request.get("path") or "/")
        request_path, query_string = _split_path_and_query(uri)

        request_headers_raw = request.get("headers")
        request_headers = (
            _redact_headers(request_headers_raw)
            if isinstance(request_headers_raw, dict)
            else {}
        )

        rule_ids, messages, tags = _extract_rule_metadata(
            transaction.get("messages")
            if isinstance(transaction.get("messages"), list)
            else []
        )

        return {
            "ingest_source": "modsec_audit_bridge",
            "transaction_id": str(
                transaction.get("id") or raw_event.get("transaction_id") or uuid4().hex
            ),
            "timestamp": str(
                transaction.get("time") or raw_event.get("timestamp") or _now_iso()
            ),
            "source_ip": str(
                transaction.get("client_ip") or raw_event.get("source_ip") or "unknown"
            ),
            "request_method": str(
                request.get("method") or raw_event.get("request_method") or "GET"
            ),
            "request_path": request_path or "/",
            "query_string": query_string,
            "request_headers": request_headers,
            "sanitized_body": _truncate_body(
                str(request.get("body") or raw_event.get("sanitized_body") or "")
            ),
            "crs_score": int(
                transaction.get("anomaly_score") or raw_event.get("crs_score") or 0
            ),
            "crs_rule_ids": rule_ids or ["unknown-rule"],
            "matched_rule_messages": messages or None,
            "matched_rule_tags": tags or None,
        }

    request_headers_raw = raw_event.get("request_headers")
    request_headers = (
        _redact_headers(request_headers_raw)
        if isinstance(request_headers_raw, dict)
        else {}
    )

    transaction_id = str(raw_event.get("transaction_id") or uuid4().hex)
    request_path = str(raw_event.get("request_path") or "/")

    rule_ids_raw = raw_event.get("crs_rule_ids")
    crs_rule_ids = (
        [str(item) for item in rule_ids_raw] if isinstance(rule_ids_raw, list) else []
    )

    messages_raw = raw_event.get("matched_rule_messages")
    matched_rule_messages = (
        [str(item) for item in messages_raw] if isinstance(messages_raw, list) else None
    )

    tags_raw = raw_event.get("matched_rule_tags")
    matched_rule_tags = (
        [str(item) for item in tags_raw] if isinstance(tags_raw, list) else None
    )

    return {
        "ingest_source": "modsec_audit_bridge",
        "transaction_id": transaction_id,
        "timestamp": str(raw_event.get("timestamp") or _now_iso()),
        "source_ip": str(raw_event.get("source_ip") or "unknown"),
        "request_method": str(raw_event.get("request_method") or "GET"),
        "request_path": request_path,
        "query_string": raw_event.get("query_string"),
        "request_headers": request_headers,
        "sanitized_body": _truncate_body(
            str(raw_event.get("sanitized_body"))
            if raw_event.get("sanitized_body") is not None
            else None
        ),
        "crs_score": int(raw_event.get("crs_score") or 0),
        "crs_rule_ids": crs_rule_ids or ["unknown-rule"],
        "matched_rule_messages": matched_rule_messages,
        "matched_rule_tags": matched_rule_tags,
    }


def post_event(
    payload: dict[str, Any],
    *,
    endpoint: str,
    api_secret: str,
    timeout: int,
) -> int:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_secret}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return int(response.status)


def _is_retryable_exception(exc: Exception) -> bool:
    if not isinstance(exc, urllib.error.URLError):
        return False

    reason = exc.reason
    if isinstance(reason, ConnectionRefusedError):
        return True

    if isinstance(reason, TimeoutError):
        return True

    if isinstance(reason, OSError) and getattr(reason, "errno", None) in _RETRYABLE_ERRNOS:
        return True

    if isinstance(reason, str) and "connection refused" in reason.lower():
        return True

    return False


def _post_event_with_retry(
    payload: dict[str, Any],
    *,
    endpoint: str,
    api_secret: str,
    timeout: int,
    max_retries: int,
    retry_delay_seconds: float,
) -> int:
    attempts = max_retries + 1

    for attempt in range(1, attempts + 1):
        try:
            status = post_event(
                payload,
                endpoint=endpoint,
                api_secret=api_secret,
                timeout=timeout,
            )

            if status in _RETRYABLE_STATUS_CODES and attempt < attempts:
                print(
                    "bridge retry: "
                    f"attempt={attempt}/{attempts} status={status} "
                    f"transaction_id={payload.get('transaction_id')}"
                )
                time.sleep(retry_delay_seconds)
                continue

            return status
        except Exception as exc:  # noqa: BLE001
            if _is_retryable_exception(exc) and attempt < attempts:
                print(
                    "bridge retry: "
                    f"attempt={attempt}/{attempts} error={exc} "
                    f"transaction_id={payload.get('transaction_id')}"
                )
                time.sleep(retry_delay_seconds)
                continue

            raise


def run_bridge(
    *,
    input_stream: TextIO,
    endpoint: str,
    api_secret: str,
    timeout: int,
    max_retries: int = 20,
    retry_delay_seconds: float = 2.0,
) -> tuple[int, int, int]:
    total = 0
    success = 0
    failed = 0

    for raw_line in input_stream:
        line = raw_line.strip()
        if not line:
            continue

        total += 1
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("event line must be a JSON object")
            payload = normalize_event(event)
            status = _post_event_with_retry(
                payload,
                endpoint=endpoint,
                api_secret=api_secret,
                timeout=timeout,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
            )
            if 200 <= status < 300:
                success += 1
            else:
                failed += 1
                print(
                    f"bridge failure: status={status} transaction_id={payload.get('transaction_id')}"
                )
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"bridge failure: {exc}")

    return total, success, failed


def _build_endpoint(args_endpoint: str | None) -> str:
    if args_endpoint:
        return args_endpoint

    explicit = os.getenv("WAF_INGEST_ENDPOINT")
    if explicit:
        return explicit

    base = os.getenv("FASTAPI_BASE_URL", "http://backend:8000")
    return urljoin(base.rstrip("/") + "/", "api/internal/waf-events")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Forward WAF audit JSON-lines events to FastAPI internal ingest"
    )
    parser.add_argument(
        "--input", default="-", help="Input JSONL file path or '-' for stdin"
    )
    parser.add_argument(
        "--endpoint", default=None, help="Internal FastAPI WAF ingest endpoint"
    )
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout seconds")
    parser.add_argument(
        "--max-retries",
        type=int,
        default=20,
        help="Retries for transient connection/5xx errors",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=2.0,
        help="Delay between retries in seconds",
    )
    parser.add_argument(
        "--api-secret",
        default=None,
        help="Internal API secret (defaults to API_SECRET_KEY env var)",
    )
    args = parser.parse_args()

    api_secret = args.api_secret or os.getenv("API_SECRET_KEY")
    if not api_secret:
        print(
            "API secret is required via --api-secret or API_SECRET_KEY", file=sys.stderr
        )
        return 2

    endpoint = _build_endpoint(args.endpoint)

    if args.input == "-":
        total, success, failed = run_bridge(
            input_stream=sys.stdin,
            endpoint=endpoint,
            api_secret=api_secret,
            timeout=args.timeout,
            max_retries=max(0, args.max_retries),
            retry_delay_seconds=max(0.0, args.retry_delay),
        )
    else:
        with open(args.input, "r", encoding="utf-8") as handle:
            total, success, failed = run_bridge(
                input_stream=handle,
                endpoint=endpoint,
                api_secret=api_secret,
                timeout=args.timeout,
                max_retries=max(0, args.max_retries),
                retry_delay_seconds=max(0.0, args.retry_delay),
            )

    print(f"bridge summary: total={total} success={success} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
