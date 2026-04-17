import json
import threading
from io import StringIO
from urllib.error import HTTPError, URLError

import pytest

from scripts.waf_audit_bridge import (
    follow_bridge,
    main,
    normalize_event,
    post_event,
    run_bridge,
)


def test_normalize_event_redacts_headers_and_preserves_waf_fields():
    payload = {
        "transaction_id": "tx-123",
        "timestamp": "2026-03-24T10:00:00Z",
        "source_ip": "203.0.113.10",
        "request_method": "POST",
        "request_path": "/login",
        "query_string": "user=admin",
        "request_headers": {
            "authorization": "Bearer secret",
            "cookie": "sid=abc",
            "user-agent": "curl/8.0",
        },
        "sanitized_body": "A" * 5000,
        "crs_score": 8,
        "crs_rule_ids": ["942100"],
    }

    normalized = normalize_event(payload)

    assert normalized["ingest_source"] == "modsec_audit_bridge"
    assert normalized["transaction_id"] == "tx-123"
    assert normalized["request_headers"]["authorization"] == "[REDACTED]"
    assert normalized["request_headers"]["cookie"] == "[REDACTED]"
    assert normalized["request_headers"]["user-agent"] == "curl/8.0"
    assert len(normalized["sanitized_body"]) == 1024


def test_normalize_event_redacts_sensitive_header_variants():
    payload = {
        "transaction_id": "tx-sensitive",
        "timestamp": "2026-03-24T10:00:00Z",
        "source_ip": "203.0.113.10",
        "request_method": "GET",
        "request_path": "/login",
        "request_headers": {
            "Authorization": "Bearer secret-token",
            "Cookie": "sid=abc",
            "Set-Cookie": "sid=abc",
            "X-Api-Token": "token-value",
            "X-Client-Secret": "secret-value",
            "X-Api-Key": "key-value",
            "X-Credential-Id": "credential-value",
            "User-Agent": "curl/8.0",
        },
        "crs_score": 8,
        "crs_rule_ids": ["942100"],
    }

    normalized = normalize_event(payload)

    assert normalized["request_headers"]["Authorization"] == "[REDACTED]"
    assert normalized["request_headers"]["Cookie"] == "[REDACTED]"
    assert normalized["request_headers"]["Set-Cookie"] == "[REDACTED]"
    assert normalized["request_headers"]["X-Api-Token"] == "[REDACTED]"
    assert normalized["request_headers"]["X-Client-Secret"] == "[REDACTED]"
    assert normalized["request_headers"]["X-Api-Key"] == "[REDACTED]"
    assert normalized["request_headers"]["X-Credential-Id"] == "[REDACTED]"
    assert normalized["request_headers"]["User-Agent"] == "curl/8.0"


def test_normalize_event_supports_modsecurity_style_payload():
    payload = {
        "transaction": {
            "id": "abc123",
            "time": "2026-03-24T10:00:00Z",
            "client_ip": "203.0.113.10",
            "request": {
                "method": "GET",
                "uri": "/login?user=admin",
                "headers": {"user-agent": "curl/8.0"},
                "body": "' OR 1=1 --",
            },
            "messages": [
                {
                    "message": "SQL Injection Attack Detected via libinjection",
                    "details": {
                        "ruleId": "942100",
                        "tags": ["attack-sqli", "paranoia-level/1"],
                    },
                }
            ],
            "anomaly_score": 8,
        }
    }

    normalized = normalize_event(payload)

    assert normalized["transaction_id"] == "abc123"
    assert normalized["request_method"] == "GET"
    assert normalized["request_path"] == "/login"
    assert normalized["query_string"] == "user=admin"
    assert normalized["crs_score"] == 8
    assert normalized["crs_rule_ids"] == ["942100"]
    assert normalized["matched_rule_messages"] == [
        "SQL Injection Attack Detected via libinjection"
    ]
    assert normalized["matched_rule_tags"] == ["attack-sqli", "paranoia-level/1"]


def test_normalize_event_preserves_real_modsecurity_unique_id_traceability():
    payload = {
        "transaction": {
            "unique_id": "178215467830.418031",
            "time_stamp": "Tue Jun 23 12:34:56 2026",
            "client_ip": "203.0.113.10",
            "request": {
                "method": "GET",
                "uri": "/api/search?q=%27%20OR%201%3D1--&page=1",
                "headers": {"user-agent": "curl/8.0"},
            },
            "messages": [
                {
                    "message": "SQL Injection Attack Detected via libinjection",
                    "details": {"ruleId": "942100", "tags": ["attack-sqli"]},
                },
                {
                    "message": (
                        "Inbound Anomaly Score Exceeded "
                        "(Total Score: 5)"
                    ),
                    "details": {
                        "ruleId": "949110",
                        "tags": ["anomaly-evaluation"],
                    },
                },
            ],
        }
    }

    normalized = normalize_event(payload)

    assert normalized["transaction_id"] == "178215467830.418031"
    assert normalized["source_ip"] == "203.0.113.10"
    assert normalized["request_method"] == "GET"
    assert normalized["request_path"] == "/api/search"
    assert normalized["query_string"] == "q=%27%20OR%201%3D1--&page=1"
    assert normalized["crs_rule_ids"] == ["942100", "949110"]
    assert (
        "SQL Injection Attack Detected via libinjection"
        in normalized["matched_rule_messages"]
    )


def test_normalize_event_preserves_real_modsecurity_json_for_lookup_proof():
    payload = {
        "transaction": {
            "unique_id": "178216021997.058115",
            "time_stamp": "Mon Jun 22 20:30:19 2026",
            "client_ip": "172.21.0.1",
            "request": {
                "method": "GET",
                "uri": "/api/health?id=12%27%20OR%2012%3D12--",
                "headers": {"user-agent": "curl/8.0"},
            },
            "messages": [
                {
                    "message": "SQL Injection Attack Detected via libinjection",
                    "details": {
                        "ruleId": "942100",
                        "tags": ["attack-sqli", "paranoia-level/1"],
                    },
                },
                {
                    "message": "Inbound Anomaly Score Exceeded (Total Score: 5)",
                    "details": {
                        "ruleId": "949110",
                        "tags": ["anomaly-evaluation"],
                    },
                },
            ],
        }
    }

    normalized = normalize_event(payload)

    assert normalized["transaction_id"] == "178216021997.058115"
    assert normalized["timestamp"] == "2026-06-22T20:30:19Z"
    assert normalized["source_ip"] == "172.21.0.1"
    assert normalized["request_path"] == "/api/health"
    assert normalized["query_string"] == "id=12%27%20OR%2012%3D12--"
    assert normalized["crs_score"] == 5
    assert normalized["crs_rule_ids"] == ["942100", "949110"]


def test_normalize_event_deduplicates_rule_ids_messages_and_tags_in_order():
    payload = {
        "transaction": {
            "unique_id": "tx-rules",
            "time_stamp": "Tue Jun 23 12:34:56 2026",
            "request": {"method": "GET", "uri": "/api/search?q=1"},
            "messages": [
                {
                    "message": "SQL Injection Attack Detected via libinjection",
                    "details": {
                        "ruleId": "942100",
                        "tags": ["attack-sqli", "paranoia-level/1"],
                    },
                },
                {
                    "message": "SQL Injection Attack Detected via libinjection",
                    "details": {
                        "ruleId": "942100",
                        "tags": ["attack-sqli"],
                    },
                },
                {
                    "message": "Inbound Anomaly Score Exceeded",
                    "details": {
                        "ruleId": "949110",
                        "tags": ["anomaly-evaluation"],
                    },
                },
            ],
        }
    }

    normalized = normalize_event(payload)

    assert normalized["crs_rule_ids"] == ["942100", "949110"]
    assert normalized["matched_rule_messages"] == [
        "SQL Injection Attack Detected via libinjection",
        "Inbound Anomaly Score Exceeded",
    ]
    assert normalized["matched_rule_tags"] == [
        "attack-sqli",
        "paranoia-level/1",
        "anomaly-evaluation",
    ]


def test_normalize_event_converts_modsecurity_time_stamp_to_iso_utc():
    payload = {
        "transaction": {
            "unique_id": "178215610797.683846",
            "time_stamp": "Mon Jun 22 19:21:47 2026",
            "client_ip": "203.0.113.10",
            "request": {
                "method": "GET",
                "uri": "/api/search?q=%27%20OR%201%3D1--",
            },
            "messages": [
                {
                    "message": "SQL Injection Attack Detected via libinjection",
                    "details": {"ruleId": "942100"},
                },
                {
                    "message": "Inbound Anomaly Score Exceeded (Total Score: 5)",
                    "details": {"ruleId": "949110"},
                },
            ],
        }
    }

    normalized = normalize_event(payload)

    assert normalized["transaction_id"] == "178215610797.683846"
    assert normalized["timestamp"] == "2026-06-22T19:21:47Z"
    assert normalized["crs_rule_ids"] == ["942100", "949110"]


def test_normalize_event_extracts_crs_score_from_total_score_message_when_missing():
    payload = {
        "transaction": {
            "unique_id": "178215610797.683846",
            "time_stamp": "Mon Jun 22 19:21:47 2026",
            "client_ip": "198.51.100.10",
            "request": {
                "method": "GET",
                "uri": "/api/health?id=10%27%20OR%2010%3D10--",
            },
            "messages": [
                {
                    "message": "SQL Injection Attack Detected via libinjection",
                    "details": {"ruleId": "942100", "tags": ["attack-sqli"]},
                },
                {
                    "message": "Inbound Anomaly Score Exceeded (Total Score: 5)",
                    "details": {"ruleId": "949110", "tags": ["anomaly-evaluation"]},
                },
            ],
        }
    }

    normalized = normalize_event(payload)

    assert normalized["crs_score"] == 5


def test_normalize_event_prefers_explicit_anomaly_score_over_total_score_message():
    payload = {
        "transaction": {
            "unique_id": "tx-score-explicit",
            "time_stamp": "Mon Jun 22 19:21:47 2026",
            "anomaly_score": 15,
            "request": {"method": "GET", "uri": "/api/health?id=1"},
            "messages": [
                {
                    "message": "Inbound Anomaly Score Exceeded (Total Score: 5)",
                    "details": {"ruleId": "949110"},
                }
            ],
        }
    }

    normalized = normalize_event(payload)

    assert normalized["crs_score"] == 15


def test_normalize_event_prefers_raw_crs_score_over_total_score_message():
    payload = {
        "crs_score": 10,
        "transaction": {
            "unique_id": "tx-score-raw",
            "time_stamp": "Mon Jun 22 19:21:47 2026",
            "request": {"method": "GET", "uri": "/api/health?id=1"},
            "messages": [
                {
                    "message": "Inbound Anomaly Score Exceeded (Total Score: 5)",
                    "details": {"ruleId": "949110"},
                }
            ],
        },
    }

    normalized = normalize_event(payload)

    assert normalized["crs_score"] == 10


@pytest.mark.parametrize(
    ("message", "expected_score"),
    [
        ("Inbound Anomaly Score Exceeded (Total Score: 5)", 5),
        ("Inbound Anomaly Score Exceeded (Total Score: `5`)", 5),
        ("Inbound Anomaly Score Exceeded (Total Score: 15)", 15),
        ("Score maybe 5", 0),
        ("rule 949110", 0),
        ("CAPEC/1000/152/248/66", 0),
    ],
)
def test_normalize_event_crs_score_format_variants(message, expected_score):
    payload = {
        "transaction": {
            "unique_id": f"tx-score-format-{expected_score}",
            "time_stamp": "Mon Jun 22 19:21:47 2026",
            "request": {"method": "GET", "uri": "/api/health"},
            "messages": [
                {
                    "message": message,
                    "details": {"ruleId": "949110"},
                }
            ],
        }
    }

    normalized = normalize_event(payload)

    assert normalized["crs_score"] == expected_score


def test_normalize_event_crs_score_ignores_rule_ids_ips_ports_years_and_tags():
    payload = {
        "transaction": {
            "unique_id": "tx-score-false-positive",
            "time_stamp": "Mon Jun 22 19:21:47 2026",
            "request": {"method": "GET", "uri": "/api/health"},
            "messages": [
                {
                    "message": (
                        "Matched rule 942100 then 949110 from 172.21.0.1:8088 "
                        "during year 2026 with CAPEC/1000/152/248/66"
                    ),
                    "details": {
                        "ruleId": "949110",
                        "tags": ["CAPEC/1000/152/248/66"],
                    },
                }
            ],
        }
    }

    normalized = normalize_event(payload)

    assert normalized["crs_score"] == 0


def test_normalize_event_defaults_crs_score_to_zero_when_absent():
    payload = {
        "transaction": {
            "unique_id": "tx-score-default",
            "time_stamp": "Mon Jun 22 19:21:47 2026",
            "request": {"method": "GET", "uri": "/api/health"},
            "messages": [
                {
                    "message": "SQL Injection Attack Detected via libinjection",
                    "details": {"ruleId": "942100"},
                }
            ],
        }
    }

    normalized = normalize_event(payload)

    assert normalized["crs_score"] == 0


def test_normalize_event_preserves_existing_iso_timestamp():
    payload = {
        "transaction": {
            "unique_id": "tx-iso",
            "time": "2026-06-22T19:21:47Z",
            "request": {"method": "GET", "uri": "/health"},
        }
    }

    normalized = normalize_event(payload)

    assert normalized["timestamp"] == "2026-06-22T19:21:47Z"


def test_post_event_sets_bearer_token_and_posts_json(monkeypatch):
    captured = {}

    class _FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def _fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        captured["content_type"] = request.get_header("Content-type")
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeResponse()

    monkeypatch.setattr(
        "scripts.waf_audit_bridge.urllib.request.urlopen", _fake_urlopen
    )

    status = post_event(
        {"transaction_id": "tx-1"},
        endpoint="http://backend:8000/api/internal/waf-events",
        api_secret="test-secret",
        timeout=5,
    )

    assert status == 200
    assert captured["url"] == "http://backend:8000/api/internal/waf-events"
    assert captured["auth"] == "Bearer test-secret"
    assert captured["content_type"] == "application/json"
    assert captured["body"]["transaction_id"] == "tx-1"
    assert captured["timeout"] == 5


def test_run_bridge_reads_json_lines_and_counts_successes(monkeypatch):
    lines = StringIO(
        "\n".join(
            [
                json.dumps(
                    {
                        "transaction_id": "tx-1",
                        "timestamp": "2026-03-24T10:00:00Z",
                        "source_ip": "203.0.113.10",
                        "request_method": "GET",
                        "request_path": "/login",
                        "crs_score": 8,
                        "crs_rule_ids": ["942100"],
                    }
                )
            ]
        )
    )

    def _fake_post(payload, endpoint, api_secret, timeout):
        return 200

    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _fake_post)

    totals = run_bridge(
        input_stream=lines,
        endpoint="http://backend:8000/api/internal/waf-events",
        api_secret="test-secret",
        timeout=10,
    )

    assert totals == (1, 1, 0)


def test_run_bridge_ignores_empty_lines(monkeypatch):
    lines = StringIO("\n  \n")

    def _fake_post(payload, endpoint, api_secret, timeout):
        raise AssertionError("empty lines should not be posted")

    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _fake_post)

    totals = run_bridge(
        input_stream=lines,
        endpoint="http://backend:8000/api/internal/waf-events",
        api_secret="test-secret",
        timeout=10,
    )

    assert totals == (0, 0, 0)


def test_run_bridge_counts_malformed_json_and_keeps_processing(monkeypatch):
    lines = StringIO(
        "{bad json}\n"
        + json.dumps(
            {
                "transaction_id": "tx-after-bad-json",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "request_method": "GET",
                "request_path": "/login",
                "crs_score": 8,
                "crs_rule_ids": ["942100"],
            }
        )
        + "\n"
    )
    posted = []

    def _fake_post(payload, endpoint, api_secret, timeout):
        posted.append(payload)
        return 200

    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _fake_post)

    totals = run_bridge(
        input_stream=lines,
        endpoint="http://backend:8000/api/internal/waf-events",
        api_secret="test-secret",
        timeout=10,
    )

    assert totals == (2, 1, 1)
    assert [payload["transaction_id"] for payload in posted] == ["tx-after-bad-json"]


def test_run_bridge_success_log_contains_transaction_id_and_rule_ids(
    monkeypatch, capsys
):
    lines = StringIO(
        json.dumps(
            {
                "transaction_id": "tx-log-success",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "request_method": "GET",
                "request_path": "/login",
                "crs_score": 8,
                "crs_rule_ids": ["942100", "949110"],
            }
        )
    )

    def _fake_post(payload, endpoint, api_secret, timeout):
        return 200

    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _fake_post)

    totals = run_bridge(
        input_stream=lines,
        endpoint="http://backend:8000/api/internal/waf-events",
        api_secret="test-secret",
        timeout=10,
    )

    output = capsys.readouterr().out
    assert totals == (1, 1, 0)
    assert "transaction_id=tx-log-success" in output
    assert "rule_ids=['942100', '949110']" in output
    assert "Authorization" not in output
    assert "Cookie" not in output
    assert "raw-body-should-not-log" not in output
    assert "API_SECRET_KEY" not in output
    assert "DATABASE_URL" not in output


def test_follow_bridge_posts_appended_line(monkeypatch, tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text("", encoding="utf-8")
    posted = []
    stop_event = threading.Event()

    def _fake_post(payload, endpoint, api_secret, timeout):
        posted.append(payload)
        stop_event.set()
        return 200

    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _fake_post)

    worker = threading.Thread(
        target=follow_bridge,
        kwargs={
            "input_path": audit_log,
            "endpoint": "http://backend:8000/api/internal/waf-events",
            "api_secret": "test-secret",
            "timeout": 10,
            "poll_interval_seconds": 0.01,
            "stop_event": stop_event,
        },
    )
    worker.start()
    try:
        with audit_log.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "transaction_id": "tx-live",
                        "timestamp": "2026-03-24T10:00:00Z",
                        "source_ip": "203.0.113.10",
                        "request_method": "GET",
                        "request_path": "/live",
                        "crs_score": 8,
                        "crs_rule_ids": ["942100"],
                    }
                )
                + "\n"
            )

        worker.join(timeout=1)
    finally:
        stop_event.set()
        worker.join(timeout=1)

    assert [payload["transaction_id"] for payload in posted] == ["tx-live"]


def test_follow_bridge_waits_for_partial_line_completion(monkeypatch, tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text("", encoding="utf-8")
    posted = []
    stop_event = threading.Event()

    def _fake_post(payload, endpoint, api_secret, timeout):
        posted.append(payload)
        stop_event.set()
        return 200

    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _fake_post)

    worker = threading.Thread(
        target=follow_bridge,
        kwargs={
            "input_path": audit_log,
            "endpoint": "http://backend:8000/api/internal/waf-events",
            "api_secret": "test-secret",
            "timeout": 10,
            "poll_interval_seconds": 0.01,
            "stop_event": stop_event,
        },
    )
    worker.start()
    try:
        event = json.dumps(
            {
                "transaction_id": "tx-partial",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "request_method": "GET",
                "request_path": "/partial",
                "crs_score": 8,
                "crs_rule_ids": ["942100"],
            }
        )
        with audit_log.open("a", encoding="utf-8") as handle:
            handle.write(event)
            handle.flush()

        stop_event.wait(0.05)
        assert posted == []

        with audit_log.open("a", encoding="utf-8") as handle:
            handle.write("\n")

        worker.join(timeout=1)
    finally:
        stop_event.set()
        worker.join(timeout=1)

    assert [payload["transaction_id"] for payload in posted] == ["tx-partial"]


def test_follow_bridge_does_not_exit_at_eof_until_stopped(tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text("", encoding="utf-8")
    stop_event = threading.Event()
    result = {}

    worker = threading.Thread(
        target=lambda: result.setdefault(
            "totals",
            follow_bridge(
                input_path=audit_log,
                endpoint="http://backend:8000/api/internal/waf-events",
                api_secret="test-secret",
                timeout=10,
                poll_interval_seconds=0.01,
                stop_event=stop_event,
            ),
        )
    )
    worker.start()
    try:
        stop_event.wait(0.05)
        assert worker.is_alive()
    finally:
        stop_event.set()
        worker.join(timeout=1)

    assert result["totals"] == (0, 0, 0)


def test_follow_bridge_reopens_after_transient_readline_oserror(
    monkeypatch, tmp_path, capsys
):
    audit_log = tmp_path / "modsec_audit.jsonl"
    first_event = {
        "transaction_id": "tx-before-error",
        "timestamp": "2026-03-24T10:00:00Z",
        "source_ip": "203.0.113.10",
        "request_method": "GET",
        "request_path": "/before",
        "request_headers": {"Authorization": "Bearer should-not-leak"},
        "sanitized_body": "raw-body-should-not-leak",
        "crs_score": 8,
        "crs_rule_ids": ["942100"],
    }
    second_event = {
        "transaction_id": "tx-after-error",
        "timestamp": "2026-03-24T10:00:01Z",
        "source_ip": "203.0.113.11",
        "request_method": "GET",
        "request_path": "/after",
        "request_headers": {"Cookie": "sid=should-not-leak"},
        "sanitized_body": "second-body-should-not-leak",
        "crs_score": 5,
        "crs_rule_ids": ["949110"],
    }
    audit_log.write_text(
        json.dumps(first_event) + "\n" + json.dumps(second_event) + "\n",
        encoding="utf-8",
    )

    posted = []
    stop_event = threading.Event()

    def _fake_post(payload, endpoint, api_secret, timeout):
        posted.append(payload)
        if payload["transaction_id"] == "tx-after-error":
            stop_event.set()
        return 200

    class _ReadlineFailureWrapper:
        def __init__(self, wrapped):
            self._wrapped = wrapped
            self._readline_calls = 0

        def __enter__(self):
            self._wrapped.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb):
            return self._wrapped.__exit__(exc_type, exc, tb)

        def tell(self):
            return self._wrapped.tell()

        def seek(self, offset, whence=0):
            return self._wrapped.seek(offset, whence)

        def readline(self):
            self._readline_calls += 1
            if self._readline_calls == 2:
                raise OSError(5, "Input/output error")
            return self._wrapped.readline()

    real_open = open
    open_count = 0

    def _fake_open(*args, **kwargs):
        nonlocal open_count
        open_count += 1
        handle = real_open(*args, **kwargs)
        if open_count == 1:
            return _ReadlineFailureWrapper(handle)
        return handle

    monkeypatch.setattr("builtins.open", _fake_open)
    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _fake_post)

    totals = follow_bridge(
        input_path=audit_log,
        endpoint="http://backend:8000/api/internal/waf-events",
        api_secret="test-secret",
        timeout=10,
        poll_interval_seconds=0.01,
        retry_delay_seconds=0.01,
        stop_event=stop_event,
        start_at_end=False,
    )

    output = capsys.readouterr().out

    assert [payload["transaction_id"] for payload in posted] == [
        "tx-before-error",
        "tx-after-error",
    ]
    assert totals[1] == 2
    assert open_count >= 2
    assert "bridge warning: read_error" in output
    assert str(audit_log) in output
    assert "OSError" in output
    assert "Bearer should-not-leak" not in output
    assert "sid=should-not-leak" not in output
    assert "raw-body-should-not-leak" not in output
    assert "second-body-should-not-leak" not in output
    assert "API_SECRET_KEY" not in output
    assert "DATABASE_URL" not in output


def test_main_follow_from_start_passes_start_at_end_false(monkeypatch, tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text("", encoding="utf-8")
    captured = {}

    def _fake_follow_bridge(**kwargs):
        captured.update(kwargs)
        return (0, 0, 0)

    monkeypatch.setenv("API_SECRET_KEY", "test-secret")
    monkeypatch.setattr("scripts.waf_audit_bridge.follow_bridge", _fake_follow_bridge)
    monkeypatch.setattr(
        "sys.argv",
        [
            "waf_audit_bridge.py",
            "--input",
            str(audit_log),
            "--follow",
            "--from-start",
            "--endpoint",
            "http://backend:8000/api/internal/waf-events",
        ],
    )

    assert main() == 0
    assert captured["input_path"] == str(audit_log)
    assert captured["start_at_end"] is False


def test_follow_bridge_from_start_processes_existing_lines(monkeypatch, tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        json.dumps(
            {
                "transaction_id": "tx-from-start",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "request_method": "GET",
                "request_path": "/from-start",
                "crs_score": 8,
                "crs_rule_ids": ["942100"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    posted = []

    def _fake_post(payload, endpoint, api_secret, timeout):
        posted.append(payload)
        return 200

    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _fake_post)

    totals = follow_bridge(
        input_path=audit_log,
        endpoint="http://backend:8000/api/internal/waf-events",
        api_secret="test-secret",
        timeout=10,
        poll_interval_seconds=0,
        idle_timeout_seconds=0.01,
        start_at_end=False,
    )

    assert totals == (1, 1, 0)
    assert [payload["transaction_id"] for payload in posted] == ["tx-from-start"]


def test_follow_bridge_skips_malformed_json(monkeypatch, tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text("{bad json}\n", encoding="utf-8")
    posted = []
    stop_event = threading.Event()

    def _fake_post(payload, endpoint, api_secret, timeout):
        posted.append(payload)
        return 200

    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _fake_post)

    totals = follow_bridge(
        input_path=audit_log,
        endpoint="http://backend:8000/api/internal/waf-events",
        api_secret="test-secret",
        timeout=10,
        poll_interval_seconds=0,
        stop_event=stop_event,
        idle_timeout_seconds=0.01,
        start_at_end=False,
    )

    assert posted == []
    assert totals == (1, 0, 1)


def test_follow_bridge_skips_duplicate_transaction_id(monkeypatch, tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    event = {
        "transaction_id": "tx-dupe",
        "timestamp": "2026-03-24T10:00:00Z",
        "source_ip": "203.0.113.10",
        "request_method": "GET",
        "request_path": "/dupe",
        "crs_score": 8,
        "crs_rule_ids": ["942100"],
    }
    audit_log.write_text(
        json.dumps(event) + "\n" + json.dumps(event) + "\n", encoding="utf-8"
    )
    posted = []

    def _fake_post(payload, endpoint, api_secret, timeout):
        posted.append(payload)
        return 200

    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _fake_post)

    totals = follow_bridge(
        input_path=audit_log,
        endpoint="http://backend:8000/api/internal/waf-events",
        api_secret="test-secret",
        timeout=10,
        poll_interval_seconds=0,
        idle_timeout_seconds=0.01,
        start_at_end=False,
    )

    assert [payload["transaction_id"] for payload in posted] == ["tx-dupe"]
    assert totals == (2, 1, 0)


def test_run_bridge_retries_transient_connection_failure(monkeypatch):
    lines = StringIO(
        json.dumps(
            {
                "transaction_id": "tx-retry",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "request_method": "GET",
                "request_path": "/login",
                "crs_score": 8,
                "crs_rule_ids": ["942100"],
            }
        )
    )

    attempts = {"count": 0}

    def _flaky_post(payload, endpoint, api_secret, timeout):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise URLError(ConnectionRefusedError("connection refused"))
        return 200

    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _flaky_post)
    totals = run_bridge(
        input_stream=lines,
        endpoint="http://backend:8000/api/internal/waf-events",
        api_secret="test-secret",
        timeout=10,
        max_retries=2,
        retry_delay_seconds=0,
    )

    assert attempts["count"] == 2
    assert totals == (1, 1, 0)


def test_follow_bridge_logs_http_error_status_without_response_body(
    monkeypatch, tmp_path, capsys
):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        json.dumps(
            {
                "transaction_id": "tx-422",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "request_method": "GET",
                "request_path": "/login",
                "crs_score": 8,
                "crs_rule_ids": ["942100"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def _fake_post(payload, endpoint, api_secret, timeout):
        raise HTTPError(
            url=endpoint,
            code=422,
            msg="Unprocessable Content",
            hdrs=None,
            fp=StringIO('{"detail":"timestamp validation failed"}'),
        )

    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _fake_post)

    totals = follow_bridge(
        input_path=audit_log,
        endpoint="http://backend:8000/api/internal/waf-events",
        api_secret="test-secret",
        timeout=10,
        poll_interval_seconds=0,
        idle_timeout_seconds=0.01,
        start_at_end=False,
    )

    output = capsys.readouterr().out
    assert totals == (1, 0, 1)
    assert "bridge failure: status=422 transaction_id=tx-422" in output
    assert "timestamp validation failed" not in output


def test_follow_bridge_http_error_log_does_not_leak_secrets_or_body(
    monkeypatch, tmp_path, capsys
):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        json.dumps(
            {
                "transaction_id": "tx-log-safe",
                "timestamp": "2026-03-24T10:00:00Z",
                "source_ip": "203.0.113.10",
                "request_method": "POST",
                "request_path": "/login",
                "request_headers": {
                    "Authorization": "Bearer live-auth-secret",
                    "Cookie": "session=live-cookie",
                },
                "sanitized_body": "raw-body-should-not-log",
                "crs_score": 8,
                "crs_rule_ids": ["942100"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    def _fake_post(payload, endpoint, api_secret, timeout):
        raise HTTPError(
            url=endpoint,
            code=422,
            msg="Unprocessable Content",
            hdrs=None,
            fp=StringIO(
                '{"detail":"API_SECRET_KEY=bridge-secret '
                'Authorization: Bearer live-auth-secret '
                'Cookie: session=live-cookie '
                'raw-body-should-not-log"}'
            ),
        )

    monkeypatch.setattr("scripts.waf_audit_bridge.post_event", _fake_post)

    totals = follow_bridge(
        input_path=audit_log,
        endpoint="http://backend:8000/api/internal/waf-events",
        api_secret="bridge-secret",
        timeout=10,
        poll_interval_seconds=0,
        idle_timeout_seconds=0.01,
        start_at_end=False,
    )

    output = capsys.readouterr().out
    assert totals == (1, 0, 1)
    assert "transaction_id=tx-log-safe" in output
    assert "bridge-secret" not in output
    assert "live-auth-secret" not in output
    assert "session=live-cookie" not in output
    assert "raw-body-should-not-log" not in output
