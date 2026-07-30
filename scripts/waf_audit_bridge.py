from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, TextIO
from urllib.parse import parse_qs, urljoin, urlsplit, urlunsplit
from uuid import uuid4

from web_app.domain.source_address import (
    SourceProvenance,
    canonicalize_source_ip,
)

_SENSITIVE_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "proxy-authorization",
    "cf-access-jwt-assertion",
}
_SENSITIVE_SUBSTRINGS = ("token", "secret", "key", "credential", "jwt", "assertion")
_MAX_BODY_LENGTH = 1024
_RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
_RETRYABLE_ERRNOS = {61, 111, 10061}
_MAX_RETRY_DELAY_SECONDS = 60.0
_TOTAL_SCORE_RE = re.compile(r"Total Score:\s*`?(\d+)`?", re.IGNORECASE)
_SOURCE_PROVENANCE_MODES = {
    "direct_remote_addr",
    "cloudflare_connecting_ip",
}
_TRUTHY = {"1", "true", "yes", "on"}
_LOOPBACKS = {"127.0.0.1", "::1"}


def _safe_log_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:1024]
    if isinstance(value, dict):
        return {
            str(key): (
                "[REDACTED]"
                if str(key).lower() in _SENSITIVE_HEADERS
                or any(part in str(key).lower() for part in _SENSITIVE_SUBSTRINGS)
                else _safe_log_value(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_safe_log_value(item) for item in value]
    try:
        return str(value)[:1024]
    except Exception:  # noqa: BLE001
        return f"<unprintable {type(value).__name__}>"


def _log_event(
    event: str,
    message: str,
    level: str = "INFO",
    stream: TextIO | None = None,
    **fields: Any,
) -> None:
    payload = {
        **_safe_log_value(fields),
        "timestamp": _now_iso(),
        "level": str(level).upper(),
        "event": str(event)[:128],
        "message": str(message)[:1024],
        "service": "cybertrace-waf-bridge",
        "component": "modsecurity-bridge",
        "environment": os.getenv("APP_ENV", "development"),
    }
    print(
        json.dumps(payload, default=str, separators=(",", ":")),
        file=stream or sys.stdout,
        flush=True,
    )


def _redact_endpoint(endpoint: str) -> str:
    try:
        parsed = urlsplit(endpoint)
        if parsed.username is None and parsed.password is None:
            return endpoint
        hostname = parsed.hostname or ""
        if parsed.port is not None:
            hostname = f"{hostname}:{parsed.port}"
        return urlunsplit(
            (parsed.scheme, f"[REDACTED]@{hostname}", parsed.path, parsed.query, "")
        )
    except Exception:  # noqa: BLE001
        return "[REDACTED]"


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


def normalize_timestamp(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None

    timestamp = str(value).strip()

    try:
        parsed = datetime.strptime(timestamp, "%a %b %d %H:%M:%S %Y")
        return parsed.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        pass

    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        _log_event(
            "bridge.source_timestamp_invalid",
            "Source event timestamp is invalid; canonical value is null",
            level="WARNING",
        )
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("source timestamp must include an explicit timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _source_evidence(
    *,
    client_ip: Any,
    request_headers: dict[str, Any],
    provenance_mode: str,
) -> tuple[str | None, str, bool | None]:
    canonical_client_ip = canonicalize_source_ip(client_ip)
    if provenance_mode == "direct_remote_addr":
        return (
            canonical_client_ip,
            SourceProvenance.DIRECT_REMOTE_ADDR.value,
            None,
        )
    if provenance_mode != "cloudflare_connecting_ip":
        raise ValueError("unsupported source provenance mode")

    return (
        canonical_client_ip,
        SourceProvenance.CLOUDFLARE_CONNECTING_IP.value,
        True if canonical_client_ip is not None else None,
    )


def _http_error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read(500)
    except Exception:  # noqa: BLE001
        return ""

    if isinstance(body, bytes):
        return body.decode("utf-8", errors="replace")
    return str(body)


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


def _coerce_score(value: Any) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _extract_total_score(messages: list[str]) -> int | None:
    for message in messages:
        match = _TOTAL_SCORE_RE.search(message)
        if match:
            return int(match.group(1))
    return None


def _resolve_crs_score(
    *,
    transaction: dict[str, Any] | None,
    raw_event: dict[str, Any],
    matched_messages: list[str] | None,
) -> int:
    if transaction is not None:
        transaction_score = _coerce_score(transaction.get("anomaly_score"))
        if transaction_score is not None:
            return transaction_score

    raw_score = _coerce_score(raw_event.get("crs_score"))
    if raw_score is not None:
        return raw_score

    message_score = _extract_total_score(matched_messages or [])
    if message_score is not None:
        return message_score

    return 0


def _internal_probe_filter_enabled() -> bool:
    enabled = os.getenv("WAF_BRIDGE_IGNORE_INTERNAL_PROBES", "false").strip().lower()
    if enabled not in _TRUTHY:
        return False
    if os.getenv("APP_ENV", "development").strip().lower() != "testing":
        raise RuntimeError(
            "WAF_BRIDGE_IGNORE_INTERNAL_PROBES is restricted to APP_ENV=testing"
        )
    return True


def _internal_probe_event(raw_event: dict[str, Any]) -> bool:
    """Return whether a ModSecurity record came from the local WAF probe.

    Block 2 probes deliberately traverse the WAF so activation is verified,
    but they are control-plane traffic rather than user traffic. In the
    disposable Block 3 topology they share the audit volume with real
    ingress, so forwarding them would recursively create PR7 recommendations.
    The controller header is intentionally not trusted: request headers are
    client-controlled. The probe port and loopback/query marker are derived
    from the controlled local topology instead.
    """
    if not _internal_probe_filter_enabled():
        return False

    transaction = raw_event.get("transaction")
    if not isinstance(transaction, dict):
        return False
    probe_port = os.getenv("WAF_BRIDGE_PROBE_PORT", "8081").strip()
    if str(transaction.get("host_port") or "") == probe_port:
        return True

    client_ip = canonicalize_source_ip(transaction.get("client_ip"))
    if client_ip not in _LOOPBACKS:
        return False

    request = transaction.get("request")
    if not isinstance(request, dict):
        return False
    uri = str(request.get("uri") or request.get("path") or "")
    return "pr7_probe_id" in parse_qs(urlsplit(uri).query, keep_blank_values=True)


def normalize_event(
    raw_event: dict[str, Any],
    *,
    provenance_mode: str = "direct_remote_addr",
) -> dict[str, Any]:
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
        source_ip, source_provenance, cf_matches = _source_evidence(
            client_ip=transaction.get("client_ip") or raw_event.get("source_ip"),
            request_headers=request_headers_raw
            if isinstance(request_headers_raw, dict)
            else {},
            provenance_mode=provenance_mode,
        )

        rule_ids, messages, tags = _extract_rule_metadata(
            transaction.get("messages")
            if isinstance(transaction.get("messages"), list)
            else []
        )

        return {
            "ingest_source": "modsec_audit_bridge",
            "transaction_id": str(
                transaction.get("unique_id")
                or transaction.get("id")
                or raw_event.get("transaction_id")
                or uuid4().hex
            ),
            "timestamp": normalize_timestamp(
                transaction.get("time")
                or transaction.get("time_stamp")
                or raw_event.get("timestamp")
            ),
            "source_ip": source_ip,
            "source_provenance": source_provenance,
            "cf_connecting_ip_matches_client_ip": cf_matches,
            "request_method": str(
                request.get("method") or raw_event.get("request_method") or "GET"
            ),
            "request_path": request_path or "/",
            "query_string": query_string,
            "request_headers": request_headers,
            "sanitized_body": _truncate_body(
                str(request.get("body") or raw_event.get("sanitized_body") or "")
            ),
            "crs_score": _resolve_crs_score(
                transaction=transaction,
                raw_event=raw_event,
                matched_messages=messages,
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
    source_ip, source_provenance, cf_matches = _source_evidence(
        client_ip=raw_event.get("source_ip"),
        request_headers=request_headers_raw
        if isinstance(request_headers_raw, dict)
        else {},
        provenance_mode=(
            "direct_remote_addr"
            if provenance_mode == "cloudflare_connecting_ip"
            else provenance_mode
        ),
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
        "timestamp": normalize_timestamp(raw_event.get("timestamp")),
        "source_ip": source_ip,
        "source_provenance": source_provenance,
        "cf_connecting_ip_matches_client_ip": cf_matches,
        "request_method": str(raw_event.get("request_method") or "GET"),
        "request_path": request_path,
        "query_string": raw_event.get("query_string"),
        "request_headers": request_headers,
        "sanitized_body": _truncate_body(
            str(raw_event.get("sanitized_body"))
            if raw_event.get("sanitized_body") is not None
            else None
        ),
        "crs_score": _resolve_crs_score(
            transaction=None,
            raw_event=raw_event,
            matched_messages=matched_rule_messages,
        ),
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
    audit_evidence: bool = False,
) -> int:
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_secret}",
    }
    if audit_evidence:
        headers["X-CyberTrace-WAF-Audit"] = "modsecurity"
        audit_key = os.getenv("WAF_AUDIT_EVIDENCE_KEY")
        if audit_key:
            headers["X-CyberTrace-WAF-Audit-Key"] = audit_key
    request = urllib.request.Request(
        endpoint,
        data=data,
        method="POST",
        headers=headers,
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

    if (
        isinstance(reason, OSError)
        and getattr(reason, "errno", None) in _RETRYABLE_ERRNOS
    ):
        return True

    if isinstance(reason, str) and "connection refused" in reason.lower():
        return True

    return False


def _retry_delay(
    *,
    attempt: int,
    base_delay_seconds: float,
    retry_after: str | None = None,
) -> float:
    fallback = base_delay_seconds * (2 ** max(0, attempt - 1))
    if retry_after:
        stripped = retry_after.strip()
        try:
            delay = float(int(stripped))
            if delay >= 0:
                return min(delay, _MAX_RETRY_DELAY_SECONDS)
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(stripped)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = (retry_at - datetime.now(timezone.utc)).total_seconds()
                if delay >= 0:
                    return min(delay, _MAX_RETRY_DELAY_SECONDS)
            except (TypeError, ValueError, OverflowError):
                pass
    return min(max(0.0, fallback), _MAX_RETRY_DELAY_SECONDS)


def _post_event_with_retry(
    payload: dict[str, Any],
    *,
    endpoint: str,
    api_secret: str,
    timeout: int,
    max_retries: int,
    retry_delay_seconds: float,
    audit_evidence: bool = False,
) -> int:
    attempts = max_retries + 1

    for attempt in range(1, attempts + 1):
        try:
            post_kwargs = {}
            if audit_evidence:
                post_kwargs["audit_evidence"] = True
            status = post_event(
                payload,
                endpoint=endpoint,
                api_secret=api_secret,
                timeout=timeout,
                **post_kwargs,
            )

            if status in _RETRYABLE_STATUS_CODES and attempt < attempts:
                _log_event(
                    "bridge.retry",
                    "Bridge post will be retried",
                    level="WARNING",
                    attempt=attempt,
                    attempts=attempts,
                    status_code=status,
                    transaction_id=payload.get("transaction_id"),
                )
                time.sleep(retry_delay_seconds)
                continue

            return status
        except urllib.error.HTTPError as exc:
            status_code = exc.code
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            exc.close()
            if status_code in _RETRYABLE_STATUS_CODES and attempt < attempts:
                delay = _retry_delay(
                    attempt=attempt,
                    base_delay_seconds=retry_delay_seconds,
                    retry_after=retry_after,
                )
                _log_event(
                    "bridge.retry",
                    "Bridge post will be retried",
                    level="WARNING",
                    attempt=attempt,
                    attempts=attempts,
                    status_code=status_code,
                    transaction_id=payload.get("transaction_id"),
                    error_type=type(exc).__name__,
                    error_message="Retryable bridge HTTP response",
                    retry_delay_seconds=delay,
                )
                time.sleep(delay)
                continue
            raise
        except Exception as exc:  # noqa: BLE001
            if _is_retryable_exception(exc) and attempt < attempts:
                delay = _retry_delay(
                    attempt=attempt,
                    base_delay_seconds=retry_delay_seconds,
                )
                _log_event(
                    "bridge.retry",
                    "Bridge post will be retried",
                    level="WARNING",
                    attempt=attempt,
                    attempts=attempts,
                    transaction_id=payload.get("transaction_id"),
                    error_type=type(exc).__name__,
                    error_message="Transient bridge post failure",
                    retry_delay_seconds=delay,
                )
                time.sleep(delay)
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
    provenance_mode: str = "direct_remote_addr",
) -> tuple[int, int, int]:
    total = 0
    success = 0
    failed = 0

    for raw_line in input_stream:
        line = raw_line.strip()
        if not line:
            continue

        total += 1
        transaction_id = "unknown"
        try:
            event = json.loads(line)
            if not isinstance(event, dict):
                raise ValueError("event line must be a JSON object")
            if _internal_probe_event(event):
                _log_event(
                    "bridge.internal_probe_skipped",
                    "Internal WAF probe event skipped from external ingest",
                    transaction_id=str(
                        (event.get("transaction") or {}).get("unique_id")
                        if isinstance(event.get("transaction"), dict)
                        else "unknown"
                    ),
                )
                continue
            payload = normalize_event(event, provenance_mode=provenance_mode)
            transaction_id = str(payload.get("transaction_id") or "unknown")
            audit_evidence = (
                provenance_mode == "cloudflare_connecting_ip"
                and isinstance(event.get("transaction"), dict)
            )
            status = _post_event_with_retry(
                payload,
                endpoint=endpoint,
                api_secret=api_secret,
                timeout=timeout,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                audit_evidence=audit_evidence,
            )
            if 200 <= status < 300:
                success += 1
                _log_event(
                    "bridge.post.completed",
                    "Bridge event posted",
                    status_code=status,
                    transaction_id=transaction_id,
                    crs_score=payload.get("crs_score"),
                    crs_rule_ids=payload.get("crs_rule_ids"),
                    cf_connecting_ip_matches_client_ip=payload.get(
                        "cf_connecting_ip_matches_client_ip"
                    ),
                )
            else:
                failed += 1
                _log_event(
                    "bridge.post.failed",
                    "Bridge event post failed",
                    level="ERROR",
                    status_code=status,
                    transaction_id=transaction_id,
                )
        except urllib.error.HTTPError as exc:
            failed += 1
            _log_event(
                "bridge.post.failed",
                "Bridge event post failed",
                level="ERROR",
                status_code=exc.code,
                transaction_id=transaction_id,
                error_type=type(exc).__name__,
                error_message="Bridge HTTP request failed",
            )
        except Exception as exc:  # noqa: BLE001
            failed += 1
            _log_event(
                "bridge.post.failed",
                "Bridge event processing failed",
                level="ERROR",
                transaction_id=transaction_id,
                error_type=type(exc).__name__,
                error_message="Bridge event processing failed",
            )

    return total, success, failed


def _process_event_line(
    line: str,
    *,
    endpoint: str,
    api_secret: str,
    timeout: int,
    max_retries: int,
    retry_delay_seconds: float,
    provenance_mode: str,
    seen_transaction_ids: set[str] | None = None,
) -> tuple[bool, bool]:
    transaction_id = "unknown"
    try:
        event = json.loads(line)
        if not isinstance(event, dict):
            raise ValueError("event line must be a JSON object")

        if _internal_probe_event(event):
            _log_event(
                "bridge.internal_probe_skipped",
                "Internal WAF probe event skipped from external ingest",
                transaction_id=str(
                    (event.get("transaction") or {}).get("unique_id")
                    if isinstance(event.get("transaction"), dict)
                    else "unknown"
                ),
            )
            return True, False

        payload = normalize_event(event, provenance_mode=provenance_mode)
        transaction_id = str(payload.get("transaction_id") or "")
        audit_evidence = (
            provenance_mode == "cloudflare_connecting_ip"
            and isinstance(event.get("transaction"), dict)
        )
        if seen_transaction_ids is not None and transaction_id in seen_transaction_ids:
            _log_event(
                "bridge.duplicate_skipped",
                "Duplicate bridge event skipped",
                transaction_id=transaction_id,
            )
            return True, False

        status = _post_event_with_retry(
            payload,
            endpoint=endpoint,
            api_secret=api_secret,
            timeout=timeout,
            max_retries=max_retries,
            retry_delay_seconds=retry_delay_seconds,
            audit_evidence=audit_evidence,
        )
        if 200 <= status < 300:
            if seen_transaction_ids is not None:
                seen_transaction_ids.add(transaction_id)
            _log_event(
                "bridge.post.completed",
                "Bridge event posted",
                status_code=status,
                transaction_id=transaction_id,
                crs_score=payload.get("crs_score"),
                crs_rule_ids=payload.get("crs_rule_ids"),
                cf_connecting_ip_matches_client_ip=payload.get(
                    "cf_connecting_ip_matches_client_ip"
                ),
            )
            return True, True

        _log_event(
            "bridge.post.failed",
            "Bridge event post failed",
            level="ERROR",
            status_code=status,
            transaction_id=transaction_id,
        )
        return False, False
    except urllib.error.HTTPError as exc:
        _log_event(
            "bridge.post.failed",
            "Bridge event post failed",
            level="ERROR",
            status_code=exc.code,
            transaction_id=transaction_id,
            error_type=type(exc).__name__,
            error_message="Bridge HTTP request failed",
        )
        return False, False
    except Exception as exc:  # noqa: BLE001
        _log_event(
            "bridge.post.failed",
            "Bridge event processing failed",
            level="ERROR",
            transaction_id=transaction_id,
            error_type=type(exc).__name__,
            error_message="Bridge event processing failed",
        )
        return False, False


def follow_bridge(
    *,
    input_path: str | os.PathLike[str],
    endpoint: str,
    api_secret: str,
    timeout: int,
    max_retries: int = 20,
    retry_delay_seconds: float = 2.0,
    poll_interval_seconds: float = 1.0,
    stop_event: threading.Event | None = None,
    idle_timeout_seconds: float | None = None,
    start_at_end: bool = True,
    provenance_mode: str = "direct_remote_addr",
) -> tuple[int, int, int]:
    total = 0
    success = 0
    failed = 0
    seen_transaction_ids: set[str] = set()
    last_activity = time.monotonic()
    stop_signal = stop_event or threading.Event()
    current_position = 0
    first_open = True
    logged_following = False

    while not stop_signal.is_set():
        with open(Path(input_path), "r", encoding="utf-8") as handle:
            if first_open and start_at_end:
                handle.seek(0, os.SEEK_END)
                current_position = handle.tell()
            else:
                handle.seek(current_position)
            first_open = False
            if not logged_following:
                _log_event(
                    "bridge.following",
                    "Bridge is following audit log",
                    input_path=str(input_path),
                )
                logged_following = True

            while not stop_signal.is_set():
                position = current_position
                try:
                    position = handle.tell()
                    raw_line = handle.readline()
                except OSError:
                    current_position = position
                    _log_event(
                        "bridge.read_error",
                        "Bridge audit log read failed; reopening",
                        level="WARNING",
                        input_path=str(input_path),
                        error_type="OSError",
                        error_message="Audit log read failed",
                    )
                    time.sleep(poll_interval_seconds)
                    break
                if not raw_line:
                    if (
                        idle_timeout_seconds is not None
                        and time.monotonic() - last_activity >= idle_timeout_seconds
                    ):
                        stop_signal.set()
                        break
                    time.sleep(poll_interval_seconds)
                    continue
                if not raw_line.endswith("\n"):
                    handle.seek(position)
                    current_position = position
                    time.sleep(poll_interval_seconds)
                    continue

                current_position = handle.tell()

                last_activity = time.monotonic()
                line = raw_line.strip()
                if not line:
                    continue

                total += 1
                line_ok, posted = _process_event_line(
                    line,
                    endpoint=endpoint,
                    api_secret=api_secret,
                    timeout=timeout,
                    max_retries=max_retries,
                    retry_delay_seconds=retry_delay_seconds,
                    provenance_mode=provenance_mode,
                    seen_transaction_ids=seen_transaction_ids,
                )
                if posted:
                    success += 1
                elif not line_ok:
                    failed += 1

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
        "--follow",
        action="store_true",
        help="Keep watching a JSONL audit log file for appended events",
    )
    parser.add_argument(
        "--from-start",
        action="store_true",
        help=(
            "With --follow, process existing lines before watching for appended events"
        ),
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
        "--waf-ingest-api-key",
        default=None,
        help="WAF submission key (defaults to WAF_INGEST_API_KEY env var)",
    )
    args = parser.parse_args()

    api_secret = args.waf_ingest_api_key or os.getenv("WAF_INGEST_API_KEY")
    if not api_secret:
        _log_event(
            "bridge.configuration_failed",
            "WAF ingest API key is required",
            level="ERROR",
            stream=sys.stderr,
            reason="missing_waf_ingest_api_key",
        )
        return 2

    provenance_mode = os.getenv(
        "WAF_SOURCE_PROVENANCE_MODE", "direct_remote_addr"
    )
    if provenance_mode not in _SOURCE_PROVENANCE_MODES:
        _log_event(
            "bridge.configuration_failed",
            "WAF source provenance mode is invalid",
            level="ERROR",
            stream=sys.stderr,
            reason="invalid_source_provenance_mode",
        )
        return 2

    endpoint = _build_endpoint(args.endpoint)
    _log_event(
        "bridge.started",
        "Bridge started",
        input_path=args.input,
        endpoint=_redact_endpoint(endpoint),
        follow=args.follow,
    )

    if args.follow:
        if args.input == "-":
            _log_event(
                "bridge.configuration_failed",
                "--follow requires --input to be a file path",
                level="ERROR",
                stream=sys.stderr,
                reason="follow_requires_file_input",
                input="-",
            )
            return 2
        total, success, failed = follow_bridge(
            input_path=args.input,
            endpoint=endpoint,
            api_secret=api_secret,
            timeout=args.timeout,
            max_retries=max(0, args.max_retries),
            retry_delay_seconds=max(0.0, args.retry_delay),
            start_at_end=not args.from_start,
            provenance_mode=provenance_mode,
        )
    elif args.input == "-":
        total, success, failed = run_bridge(
            input_stream=sys.stdin,
            endpoint=endpoint,
            api_secret=api_secret,
            timeout=args.timeout,
            max_retries=max(0, args.max_retries),
            retry_delay_seconds=max(0.0, args.retry_delay),
            provenance_mode=provenance_mode,
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
                provenance_mode=provenance_mode,
            )

    _log_event(
        "bridge.summary",
        "Bridge run completed",
        total=total,
        success=success,
        failed=failed,
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
