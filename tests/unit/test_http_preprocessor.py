"""Unit tests for http_preprocessor module.

These tests verify that the HTTP preprocessing logic correctly canonicalizes
raw HTTP requests into the format expected by the ML model during training.
"""

import pytest

from web_app.application.http_preprocessor import (
    canonicalize_text,
    parse_raw_http,
    preprocess_http_request,
)


class TestCanonicalizeText:
    """Tests for the canonicalize_text function."""

    def test_url_decoding(self):
        """URL-encoded characters should be decoded."""
        assert canonicalize_text("%2F%2E%2E") == "/.."
        assert canonicalize_text("hello%20world") == "hello world"
        assert canonicalize_text("%3Cscript%3E") == "<script>"

    def test_html_unescape(self):
        """HTML entities should be unescaped."""
        assert canonicalize_text("&") == "&"
        assert canonicalize_text("<script>") == "<script>"
        assert canonicalize_text("&#x27;") == "'"

    def test_unicode_normalization(self):
        """Unicode should be NFKC normalized."""
        # Full-width characters normalize to their standard equivalents
        assert canonicalize_text("\uff02hello\uff02") == '"hello"'
        # Superscript digits normalize
        assert canonicalize_text("m\u00b2") == "m2"  # m² -> m2

    def test_null_byte_stripping(self):
        """Null bytes should be stripped."""
        assert canonicalize_text("hello\x00world") == "helloworld"
        assert canonicalize_text("\x00test") == "test"

    def test_whitespace_collapse(self):
        """Multiple whitespace should be collapsed to single spaces."""
        assert canonicalize_text("hello   world") == "hello world"
        assert canonicalize_text("a\n\tb\nc") == "a b c"
        assert canonicalize_text("  leading and trailing  ") == "leading and trailing"

    def test_lowercase(self):
        """Text should be lowercased."""
        assert canonicalize_text("HELLO WORLD") == "hello world"
        assert canonicalize_text("Content-Type") == "content-type"

    def test_combined_transformations(self):
        """Multiple transformations should be applied in sequence."""
        # URL decode first, then HTML unescape, then normalize, etc.
        result = canonicalize_text("GET%20/api?test=1&foo=2")
        assert result == "get /api?test=1&foo=2"

    def test_empty_string(self):
        """Empty string returns empty string."""
        assert canonicalize_text("") == ""

    def test_non_string_input(self):
        """Non-string input returns empty string."""
        assert canonicalize_text(None) == ""
        assert canonicalize_text(123) == ""


class TestParseRawHttp:
    """Tests for the parse_raw_http function."""

    def test_basic_get_request(self):
        """Basic GET request parsing."""
        raw = "GET /path HTTP/1.1\r\nHost: localhost\r\n\r\n"
        method, path, body = parse_raw_http(raw)
        assert method == "GET"
        assert path == "/path"
        assert body == ""

    def test_post_with_body(self):
        """POST request with body."""
        raw = "POST /login HTTP/1.1\r\nHost: localhost\r\n\r\nusername=admin&password=test"
        method, path, body = parse_raw_http(raw)
        assert method == "POST"
        assert path == "/login"
        assert body == "username=admin&password=test"

    def test_query_string_in_path(self):
        """Query strings are preserved in path."""
        raw = "GET /search?q=1&page=2 HTTP/1.1\r\n\r\n"
        method, path, body = parse_raw_http(raw)
        assert method == "GET"
        assert path == "/search?q=1&page=2"

    def test_strips_http_version(self):
        """HTTP version suffix should be stripped."""
        raw = "GET /api HTTP/1.0\r\n\r\n"
        method, path, body = parse_raw_http(raw)
        assert method == "GET"
        assert path == "/api"

    def test_crlf_handling(self):
        """Various CRLF line endings should be handled."""
        raw = "GET /test HTTP/1.1\r\nHeader: value\r\n\r\n"
        method, path, body = parse_raw_http(raw)
        assert method == "GET"
        assert path == "/test"

    def test_body_extraction(self):
        """Body after double newline is extracted."""
        raw = "POST /api HTTP/1.1\r\nContent-Type: text/plain\r\n\r\nHello World"
        method, path, body = parse_raw_http(raw)
        assert body == "Hello World"

    def test_empty_body(self):
        """Request without body."""
        raw = "DELETE /resource/1 HTTP/1.1\r\nHost: api.example.com\r\n\r\n"
        method, path, body = parse_raw_http(raw)
        assert method == "DELETE"
        assert path == "/resource/1"
        assert body == ""

    def test_empty_input(self):
        """Empty input returns empty strings."""
        assert parse_raw_http("") == ("", "", "")
        assert parse_raw_http(None) == ("", "", "")
        assert parse_raw_http("   ") == ("", "", "")

    def test_malformed_request_line(self):
        """Malformed request line still splits when both method and path exist."""
        raw = "not a valid request"
        method, path, body = parse_raw_http(raw)
        assert method == "not"
        assert path == "a valid request"
        assert body == ""

    def test_method_only_returns_empty_parts(self):
        """Request lines missing a path should fail safely."""
        assert parse_raw_http("GET") == ("", "", "")

    def test_blank_path_returns_empty_parts(self):
        """Blank path after trimming should fail safely."""
        assert parse_raw_http("GET   HTTP/1.1") == ("", "", "")

    def test_only_headers_no_body(self):
        """Request with headers but no body marker."""
        raw = "GET /no-body HTTP/1.1\r\nHost: localhost\r\n"
        method, path, body = parse_raw_http(raw)
        assert method == "GET"
        assert path == "/no-body"
        assert body == ""


class TestPreprocessHttpRequest:
    """Tests for the main preprocess_http_request function."""

    def test_sqli_union_select(self):
        """SQL injection - Union Select attack."""
        raw = (
            "GET /search?q=1' UNION SELECT username,password FROM users-- HTTP/1.1\r\n"
            "Host: localhost\r\nUser-Agent: Mozilla/5.0\r\n\r\n"
        )
        result = preprocess_http_request(raw)
        assert result == "get /search?q=1' union select username,password from users--"

    def test_normal_post_request(self):
        """Normal POST request with JSON body."""
        raw = (
            "POST /api/cart/items HTTP/1.1\r\n"
            "Host: localhost\r\n"
            "Content-Type: application/json\r\n\r\n"
            '{"product_id": 123, "quantity": 2}'
        )
        result = preprocess_http_request(raw)
        assert result == 'post /api/cart/items {"product_id": 123, "quantity": 2}'

    def test_normal_get_request(self):
        """Normal GET request."""
        raw = "GET /products?page=1&limit=20 HTTP/1.1\r\nHost: localhost\r\n\r\n"
        result = preprocess_http_request(raw)
        assert result == "get /products?page=1&limit=20"

    def test_path_traversal_encoded(self):
        """Path traversal with URL encoding."""
        raw = (
            "GET /files/%2e%2e%2f%2e%2e%2fetc%2fshadow HTTP/1.1\r\n"
            "Host: localhost\r\n\r\n"
        )
        result = preprocess_http_request(raw)
        assert result == "get /files/../../etc/shadow"

    def test_sql_injection_auth_bypass(self):
        """SQL injection - Auth bypass via POST body."""
        raw = (
            "POST /login HTTP/1.1\r\n"
            "Host: localhost\r\n"
            "Content-Type: application/x-www-form-urlencoded\r\n\r\n"
            "username=admin' OR '1'='1&password=test"
        )
        result = preprocess_http_request(raw)
        assert result == "post /login username=admin' or '1'='1&password=test"

    def test_os_command_injection(self):
        """OS command injection via pipe."""
        raw = (
            "POST /api/report HTTP/1.1\r\n"
            "Host: localhost\r\n"
            "Content-Type: application/json\r\n\r\n"
            '{"target": "localhost | cat /etc/shadow"}'
        )
        result = preprocess_http_request(raw)
        assert result == 'post /api/report {"target": "localhost | cat /etc/shadow"}'

    def test_lowercase_output(self):
        """Output should be fully lowercase."""
        raw = "POST /API/ENDPOINT HTTP/1.1\r\nHost: EXAMPLE.COM\r\n\r\nDATA"
        result = preprocess_http_request(raw)
        assert result == "post /api/endpoint data"
        assert result.islower()

    def test_no_headers_in_output(self):
        """Headers should not appear in the output."""
        raw = (
            "GET /test HTTP/1.1\r\n"
            "Host: important.com\r\n"
            "User-Agent: Mozilla/5.0\r\n"
            "Authorization: secret-token\r\n\r\n"
        )
        result = preprocess_http_request(raw)
        # Should only contain method and path
        assert "Host" not in result
        assert "User-Agent" not in result
        assert "Authorization" not in result
        assert "important.com" not in result

    def test_no_http_version_in_output(self):
        """HTTP version should be stripped."""
        raw = "GET /versioned HTTP/1.1\r\n\r\n"
        result = preprocess_http_request(raw)
        assert "HTTP" not in result
        assert "1.1" not in result

    def test_malformed_input_returns_empty(self):
        """Malformed input returns empty string (safe failure)."""
        assert preprocess_http_request("") == ""
        assert preprocess_http_request(None) == ""
        assert preprocess_http_request("not http at all") == "not http at all"

    def test_method_only_input_returns_empty(self):
        """Method-only inputs should fail safely before model inference."""
        assert preprocess_http_request("GET") == ""

    def test_blank_path_input_returns_empty(self):
        """Blank request paths should fail safely before model inference."""
        assert preprocess_http_request("GET   HTTP/1.1") == ""

    def test_preserves_sql_operators(self):
        """SQL operators like quotes and dashes are preserved."""
        raw = "GET /?id=1' OR '1'='1 HTTP/1.1\r\n\r\n"
        result = preprocess_http_request(raw)
        # Quotes and special chars should be preserved
        assert "'" in result
        assert "or" in result
        # But normalized/lower-cased
        assert "OR" not in result

    def test_whitespace_normalized(self):
        """Multiple whitespace collapsed to single space."""
        raw = "GET   /multiple   spaces   HTTP/1.1\r\n\r\nbody"
        result = preprocess_http_request(raw)
        # No triple spaces
        assert "   " not in result
        assert "get /multiple spaces body" == result
