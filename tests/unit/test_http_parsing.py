"""
Tests for HTTP request parsing utilities.
"""

import pytest

from web_app.application.http_parsing import parse_http_request_line, ParsedHttpRequest


class TestParseHttpRequestLine:
    """Test cases for parse_http_request_line function."""

    def test_parse_standard_http_request(self):
        """Test parsing a standard HTTP/1.1 request line."""
        http_request = "GET /api/users HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "GET"
        assert result.path == "/api/users"

    def test_parse_post_request(self):
        """Test parsing a POST request."""
        http_request = "POST /login HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "POST"
        assert result.path == "/login"

    def test_parse_request_with_query_string(self):
        """Test parsing a request with query string."""
        http_request = "GET /api/users?id=1&name=test HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "GET"
        assert result.path == "/api/users"

    def test_parse_request_with_full_url(self):
        """Test parsing a request with full URL."""
        http_request = "GET http://example.com/api/data HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "GET"
        assert result.path == "/api/data"

    def test_parse_request_with_full_url_and_port(self):
        """Test parsing a request with full URL and port."""
        http_request = "POST http://example.com:8080/admin HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "POST"
        assert result.path == "/admin"

    def test_parse_request_with_headers(self):
        """Test parsing a full HTTP request with headers."""
        http_request = """GET /search?q=injection HTTP/1.1
Host: example.com
User-Agent: Mozilla/5.0"""
        result = parse_http_request_line(http_request)
        
        assert result.method == "GET"
        assert result.path == "/search"

    def test_parse_request_with_body(self):
        """Test parsing a request with body."""
        http_request = """POST /api/login HTTP/1.1
Host: example.com
Content-Type: application/x-www-form-urlencoded

username=admin&password=test"""
        result = parse_http_request_line(http_request)
        
        assert result.method == "POST"
        assert result.path == "/api/login"

    def test_parse_lowercase_method(self):
        """Test that method is normalized to uppercase."""
        http_request = "get /api/data HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "GET"

    def test_parse_root_path(self):
        """Test parsing a root path request."""
        http_request = "GET / HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "GET"
        assert result.path == "/"

    def test_parse_without_http_version(self):
        """Test parsing without HTTP version."""
        http_request = "DELETE /api/users/1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "DELETE"
        assert result.path == "/api/users/1"

    def test_parse_empty_string(self):
        """Test parsing empty string returns None values."""
        result = parse_http_request_line("")
        
        assert result.method is None
        assert result.path is None

    def test_parse_none(self):
        """Test parsing None returns None values."""
        result = parse_http_request_line(None)
        
        assert result.method is None
        assert result.path is None

    def test_parse_invalid_request(self):
        """Test parsing invalid request returns None values."""
        result = parse_http_request_line("not a valid http request")
        
        assert result.method is None
        assert result.path is None

    def test_parse_full_url_with_query(self):
        """Test parsing full URL with query string."""
        http_request = "GET http://example.com/search?q=test&page=1 HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "GET"
        assert result.path == "/search"

    def test_parse_https_url(self):
        """Test parsing HTTPS URL."""
        http_request = "GET https://secure.example.com/api/data HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "GET"
        assert result.path == "/api/data"

    def test_parse_patch_method(self):
        """Test parsing PATCH method."""
        http_request = "PATCH /api/users/1 HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "PATCH"
        assert result.path == "/api/users/1"

    def test_parse_head_method(self):
        """Test parsing HEAD method."""
        http_request = "HEAD /health HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "HEAD"
        assert result.path == "/health"

    def test_parse_options_method(self):
        """Test parsing OPTIONS method."""
        http_request = "OPTIONS /api HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "OPTIONS"
        assert result.path == "/api"

    def test_parse_connect_authority_form_returns_none(self):
        """Test parsing CONNECT method with authority-form (host:port) returns None for path.
        
        RFC 7230 defines authority-form as: CONNECT example.com:443 HTTP/1.1
        This is used for HTTP tunneling. The URI is just the authority, not a path.
        The parser should explicitly reject this rather than treating it as a path.
        """
        http_request = "CONNECT example.com:443 HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "CONNECT"
        # Authority-form has no path component - explicitly rejected
        assert result.path is None

    def test_parse_connect_with_port_returns_none(self):
        """Test parsing CONNECT method with port number returns None for path."""
        http_request = "CONNECT 192.168.1.1:8080 HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "CONNECT"
        assert result.path is None

    def test_parse_options_asterisk_form(self):
        """Test parsing OPTIONS method with asterisk-form returns * as path.
        
        RFC 7230 defines asterisk-form as: OPTIONS * HTTP/1.1
        This is used to query server capabilities. The parser should return '*' as path.
        """
        http_request = "OPTIONS * HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "OPTIONS"
        assert result.path == "*"

    def test_parse_connect_with_authority_plus_path(self):
        """Test that CONNECT with authority and path is handled.
        
        While unusual, CONNECT with explicit path form like
        'CONNECT example.com:443 /tunnel HTTP/1.1' would have the URI
        captured as 'example.com:443' (everything before the next whitespace),
        which lacks a '/' so it's treated as authority-form and returns None.
        This is conservative/safe behavior.
        """
        http_request = "CONNECT example.com:443 /tunnel HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method == "CONNECT"
        # The URI captured is "example.com:443" (no /), treated as authority-form
        # Returns None as safe/conservative behavior
        assert result.path is None

    def test_parse_unknown_method_returns_none(self):
        """Test that unknown/invalid HTTP methods return None values."""
        http_request = "NOTAMETHOD /api HTTP/1.1"
        result = parse_http_request_line(http_request)
        
        assert result.method is None
        assert result.path is None

    def test_parse_random_text_returns_none(self):
        """Test that random text that doesn't match HTTP format returns None."""
        result = parse_http_request_line("GET")  # Missing path
        
        assert result.method is None
        assert result.path is None

    def test_parse_method_without_space_returns_none(self):
        """Test that malformed request line without space returns None."""
        result = parse_http_request_line("GET/api/users")
        
        assert result.method is None
        assert result.path is None
