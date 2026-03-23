"""
Unit tests for HTTP request parsing - additional edge cases.

Tests cover:
- Valid parsing (additional cases)
- Escaped newlines (\\n)
- Malformed input
"""

import pytest

from web_app.application.http_parsing import parse_http_request_line, ParsedHttpRequest


class TestHttpParserEscapedNewlines:
    """Test cases for escaped newline handling in HTTP parser."""

    def test_escaped_newline_literal(self):
        """Test parsing HTTP request with escaped newline literal."""
        http_request = "GET /api\\ntest HTTP/1.1"
        result = parse_http_request_line(http_request)

        assert result.method == "GET"
        assert result.path == "/api"

    def test_escaped_newline_in_string(self):
        """Test parsing with escaped newline in multiline string representation."""
        http_request = "POST /login\\nHost: example.com\\n\\ndata"
        result = parse_http_request_line(http_request)

        assert result.method == "POST"
        assert result.path == "/login"

    def test_mixed_escaped_and_real_newlines(self):
        """Test parsing with mix of escaped and real newlines."""
        http_request = "GET /search\\nq=test\\nUser-Agent: curl"
        result = parse_http_request_line(http_request)

        assert result.method == "GET"
        assert result.path == "/search"

    def test_multiple_escaped_newlines(self):
        """Test parsing with multiple escaped newline sequences."""
        http_request = "DELETE /api/users/1\\n\\n\\n"
        result = parse_http_request_line(http_request)

        assert result.method == "DELETE"
        assert result.path == "/api/users/1"

    def test_escaped_newline_with_tab(self):
        """Test parsing with escaped newline and tab characters."""
        http_request = "PUT /api\\n\\tdata HTTP/1.1"
        result = parse_http_request_line(http_request)

        assert result.method == "PUT"
        assert result.path == "/api"


class TestHttpParserMalformedInput:
    """Test cases for malformed input handling."""

    def test_only_whitespace(self):
        """Test parsing whitespace-only input."""
        result = parse_http_request_line("   \t  \n  ")

        assert result.method is None
        assert result.path is None

    def test_single_word(self):
        """Test parsing single word without space."""
        result = parse_http_request_line("GET")

        assert result.method is None
        assert result.path is None

    def test_method_only_with_space(self):
        """Test parsing method followed by space but no path."""
        result = parse_http_request_line("GET ")

        assert result.method is None
        assert result.path is None

    def test_path_with_special_chars(self):
        """Test parsing path with special characters."""
        http_request = "GET /api/users?id=1&name=test HTTP/1.1"
        result = parse_http_request_line(http_request)

        assert result.method == "GET"
        assert result.path == "/api/users"

    def test_path_with_fragment(self):
        """Test parsing path with URL fragment."""
        http_request = "GET /docs#section1 HTTP/1.1"
        result = parse_http_request_line(http_request)

        assert result.method == "GET"
        assert result.path == "/docs"

    def test_multiple_spaces_between_method_and_path(self):
        """Test parsing with multiple spaces."""
        http_request = "GET    /api HTTP/1.1"
        result = parse_http_request_line(http_request)

        assert result.method == "GET"
        assert result.path == "/api"

    def test_trailing_spaces(self):
        """Test parsing with trailing spaces."""
        http_request = "GET /api HTTP/1.1   "
        result = parse_http_request_line(http_request)

        assert result.method == "GET"
        assert result.path == "/api"

    def test_empty_path(self):
        """Test parsing with empty path (just slash)."""
        http_request = "GET / HTTP/1.1"
        result = parse_http_request_line(http_request)

        assert result.method == "GET"
        assert result.path == "/"

    def test_http_version_2(self):
        """Test parsing with HTTP/2."""
        http_request = "GET /api HTTP/2"
        result = parse_http_request_line(http_request)

        assert result.method == "GET"
        assert result.path == "/api"


class TestHttpParserValidParsing:
    """Additional test cases for valid parsing."""

    def test_trace_method(self):
        """Test parsing TRACE method."""
        http_request = "TRACE /trace HTTP/1.1"
        result = parse_http_request_line(http_request)

        assert result.method == "TRACE"
        assert result.path == "/trace"

    def test_head_method(self):
        """Test parsing HEAD method."""
        http_request = "HEAD /status HTTP/1.1"
        result = parse_http_request_line(http_request)

        assert result.method == "HEAD"
        assert result.path == "/status"

    def test_all_standard_methods(self):
        """Test all standard HTTP methods."""
        methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS", "TRACE"]
        for method in methods:
            http_request = f"{method} /test HTTP/1.1"
            result = parse_http_request_line(http_request)
            assert result.method == method
            assert result.path == "/test"

    def test_absolute_https_url(self):
        """Test parsing HTTPS URL."""
        http_request = "GET https://secure.example.com/api/data HTTP/1.1"
        result = parse_http_request_line(http_request)

        assert result.method == "GET"
        assert result.path == "/api/data"

    def test_json_body_in_request(self):
        """Test parsing request with JSON body."""
        http_request = """POST /api/users HTTP/1.1
Content-Type: application/json

{"name": "test"}"""
        result = parse_http_request_line(http_request)

        assert result.method == "POST"
        assert result.path == "/api/users"


class TestHttpParserEdgeCases:
    """Edge case tests for HTTP parser."""

    def test_unicode_in_path(self):
        """Test parsing path with unicode characters."""
        http_request = "GET /api/用户 HTTP/1.1"
        result = parse_http_request_line(http_request)

        assert result.method == "GET"
        assert result.path == "/api/用户"

    def test_very_long_path(self):
        """Test parsing very long path."""
        long_path = "/" + "a" * 1000
        http_request = f"GET {long_path} HTTP/1.1"
        result = parse_http_request_line(http_request)

        assert result.method == "GET"
        assert len(result.path) == 1001

    def test_real_newline_parsing(self):
        """Test parsing with real newlines."""
        http_request = "GET /api HTTP/1.1\nHost: example.com\nAccept: */*"
        result = parse_http_request_line(http_request)

        assert result.method == "GET"
        assert result.path == "/api"

    def test_empty_input(self):
        """Test empty input returns None."""
        result = parse_http_request_line("")

        assert result.method is None
        assert result.path is None
