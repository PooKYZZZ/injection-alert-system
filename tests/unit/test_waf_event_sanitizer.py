from web_app.application.waf_event_sanitizer import (
    redact_sensitive_text,
    sanitize_waf_event,
)


def test_masks_sensitive_headers():
    payload = {
        "request_headers": {
            "authorization": "Bearer secret",
            "cookie": "sessionid=abc",
            "user-agent": "curl/8.0",
        },
        "sanitized_body": "password=hunter2",
    }

    result = sanitize_waf_event(payload)

    assert result["request_headers"]["authorization"] == "[REDACTED]"
    assert result["request_headers"]["cookie"] == "[REDACTED]"
    assert result["request_headers"]["user-agent"] == "curl/8.0"


def test_truncates_oversized_body_excerpt():
    payload = {"sanitized_body": "A" * 5000}

    result = sanitize_waf_event(payload)

    assert len(result["sanitized_body"]) <= 1024


def test_preserves_non_sensitive_fields():
    payload = {
        "transaction_id": "tx-123",
        "source_ip": "203.0.113.10",
        "request_method": "GET",
        "request_path": "/login",
        "crs_score": 8,
        "crs_rule_ids": ["942100"],
    }

    result = sanitize_waf_event(payload)

    assert result["transaction_id"] == "tx-123"
    assert result["source_ip"] == "203.0.113.10"
    assert result["crs_score"] == 8


def test_masks_set_cookie_header():
    payload = {
        "request_headers": {
            "set-cookie": "session=xyz; Path=/",
            "host": "example.com",
        },
    }

    result = sanitize_waf_event(payload)

    assert result["request_headers"]["set-cookie"] == "[REDACTED]"
    assert result["request_headers"]["host"] == "example.com"


def test_handles_missing_request_headers():
    payload = {
        "transaction_id": "tx-123",
        "source_ip": "203.0.113.10",
        "request_method": "GET",
        "request_path": "/login",
        "crs_score": 5,
        "crs_rule_ids": ["942100"],
    }

    result = sanitize_waf_event(payload)

    assert "request_headers" not in result or result.get("request_headers") is None


def test_handles_missing_sanitized_body():
    payload = {
        "transaction_id": "tx-123",
        "source_ip": "203.0.113.10",
        "request_method": "GET",
        "request_path": "/login",
        "crs_score": 5,
        "crs_rule_ids": ["942100"],
    }

    result = sanitize_waf_event(payload)

    assert "sanitized_body" not in result or result.get("sanitized_body") is None


def test_redacts_form_body_secrets():
    result = redact_sensitive_text("password=hunter2&token=abc123")

    assert "password=%5BREDACTED%5D" in result
    assert "token=%5BREDACTED%5D" in result
    assert "hunter2" not in result
    assert "abc123" not in result


def test_redacts_json_body_secrets():
    result = redact_sensitive_text('{"password":"hunter2","api_key":"abc123"}')

    assert '"password": "[REDACTED]"' in result
    assert '"api_key": "[REDACTED]"' in result
    assert "hunter2" not in result
    assert "abc123" not in result


def test_redacts_authorization_header_text():
    result = redact_sensitive_text("Authorization: Bearer abc")

    assert result == "Authorization: [REDACTED]"
    assert "Bearer abc" not in result


def test_redacts_cookie_header_text():
    result = redact_sensitive_text("Cookie: session=abc")

    assert result == "Cookie: [REDACTED]"
    assert "session=abc" not in result
