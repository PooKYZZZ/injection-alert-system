from io import StringIO
import json
from urllib.error import URLError

from scripts.waf_audit_bridge import normalize_event, post_event, run_bridge


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
