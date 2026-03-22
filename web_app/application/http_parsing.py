"""
web_app/application/http_parsing.py

HTTP request parsing utilities for extracting structured request metadata
from raw HTTP request strings.

This module provides parsing for the first line of an HTTP request to extract:
- HTTP method (GET, POST, PUT, DELETE, etc.)
- Request path/URI

The parser handles various HTTP request formats including:
- Standard HTTP/1.1: "GET /path HTTP/1.1"
- HTTP/1.0: "POST /api/data HTTP/1.0"
- Relative URI: "GET /users?id=1"
- Full URL: "GET http://example.com/path HTTP/1.1"

Parsing is done with safe fallbacks - if parsing fails, None values are returned.

---

Field Distinction:

- `http_request`: Raw forensic source of truth — never modified by this parser.
  This is the complete HTTP request string as received, stored verbatim.

- `request_method`, `request_path`: Analytics-friendly structured fields derived
  from the raw request. Method is uppercased. Path strips query string.

Request-Target Forms (RFC 9112):

- origin-form: "/path?query" — NORMAL case, fully supported
- absolute-form: "https://host/path" — SUPPORTED, path is extracted
- authority-form: "host:port" — CONNECT method only. EXPLICITLY REJECTED (returns None)
- asterisk-form: "*" — OPTIONS method only. Returns "*" as path

The parser is a CONSERVATIVE extractor, not a smart repair tool. Invalid or
ambiguous inputs return None rather than attempting auto-correction.
"""

from dataclasses import dataclass
from typing import Optional
import re

# Valid HTTP methods (case-insensitive check later)
VALID_HTTP_METHODS = frozenset(
    {
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "PATCH",
        "HEAD",
        "OPTIONS",
        "TRACE",
        "CONNECT",
        "COPY",
        "LOCK",
        "MKCOL",
        "MOVE",
        "PROPFIND",
        "PROPPATCH",
        "UNLOCK",
        "SEARCH",
        "ACL",
        "BIND",
        "REBIND",
        "UNBIND",
        "DELETE",
        "PURGE",
        "LINK",
        "UNLINK",
        "VIEW",
    }
)

# Regex to match the first line of an HTTP request
# Captures: method, uri/path, optional HTTP version
HTTP_REQUEST_LINE_PATTERN = re.compile(
    r"^(?P<method>[A-Za-z]+)"  # HTTP method (GET, POST, etc.)
    r"\s+"
    r"(?P<uri>[^\s]+)"  # URI or path (everything until next whitespace)
    r"(?:\s+HTTP/[\d.]+)?",  # Optional HTTP version
    re.IGNORECASE,
)


@dataclass
class ParsedHttpRequest:
    """Parsed HTTP request metadata from a raw request string."""

    method: Optional[str] = None
    path: Optional[str] = None


def parse_http_request_line(http_request: str) -> ParsedHttpRequest:
    """
    Parse the first line of an HTTP request to extract method and path.

    Args:
        http_request: Raw HTTP request string (may include headers/body)

    Returns:
        ParsedHttpRequest with method and path, or None values if parsing fails.

    Examples:
        >>> parse_http_request_line("GET /api/users HTTP/1.1")
        ParsedHttpRequest(method='GET', path='/api/users')

        >>> parse_http_request_line("POST /login HTTP/1.1\\nHost: example.com\\n\\nusername=admin")
        ParsedHttpRequest(method='POST', path='/login')

        >>> parse_http_request_line("invalid request")
        ParsedHttpRequest(method=None, path=None)
    """
    if not http_request:
        return ParsedHttpRequest(method=None, path=None)

    # Get the first line only — handle both real newlines (\n) and escaped literals (\\n)
    if "\n" in http_request:
        first_line = http_request.split("\n")[0].strip()
    elif "\\n" in http_request:
        first_line = http_request.split("\\n")[0].strip()
    else:
        first_line = http_request.strip()
    if not first_line:
        return ParsedHttpRequest(method=None, path=None)

    # Try to match the HTTP request line pattern
    match = HTTP_REQUEST_LINE_PATTERN.match(first_line)
    if not match:
        return ParsedHttpRequest(method=None, path=None)

    method = match.group("method")
    uri = match.group("uri")

    if not method or not uri:
        return ParsedHttpRequest(method=None, path=None)

    # Normalize method to uppercase
    method = method.upper()

    # Validate that method is a known HTTP method
    # This prevents matching arbitrary text like "NOT a valid http request"
    if method not in VALID_HTTP_METHODS:
        return ParsedHttpRequest(method=None, path=None)

    # Extract path from URI - handle full URLs by extracting path portion
    # Pass method to handle authority-form (CONNECT) and asterisk-form (OPTIONS *)
    path = _extract_path_from_uri(uri, method=method)

    return ParsedHttpRequest(method=method, path=path)


def _extract_path_from_uri(uri: str, method: str = "GET") -> Optional[str]:
    """
    Extract the path portion from a URI.

    Handles:
    - Full URLs: http://example.com/path -> /path
    - Full URLs with port: http://example.com:8080/path -> /path
    - Full URLs with query: http://example.com/path?id=1 -> /path
    - Relative paths: /path -> /path
    - Relative paths with query: /path?id=1 -> /path
    - Authority-form (CONNECT): host:port -> None (explicitly rejected)
    - Asterisk-form (OPTIONS *): * -> * (returned as-is for analytics)

    Returns:
        The path portion of the URI, or None for unsupported forms.
    """
    if not uri:
        return None

    # Check for asterisk-form (OPTIONS method only): "*"
    if method == "OPTIONS" and uri == "*":
        # Asterisk-form: used with OPTIONS * to query server capabilities
        return "*"

    # Check for authority-form (CONNECT method only): "host:port" or "host"
    # This has no path component - explicitly reject
    # Must check this AFTER absolute-form check since absolute-form URLs contain "://"
    is_authority_form = (
        method == "CONNECT"
        and "://" not in uri  # Not an absolute URL
        and "/" not in uri  # No path component
    )
    if is_authority_form:
        # Authority-form: just host[:port], no path
        # This is explicitly rejected - don't treat as path
        return None

    # Check if it's a full URL (starts with http:// or https://)
    if uri.startswith("http://") or uri.startswith("https://"):
        # Find the path portion after host
        # Format: http[s]://host[:port]/path[?query][#fragment]
        rest = uri.split("://", 1)[1]  # Everything after http://
        if "/" in rest:
            path_part = rest.split("/", 1)[1]  # Everything after host
            # Remove query string and fragment
            if "?" in path_part:
                path_part = path_part.split("?")[0]
            if "#" in path_part:
                path_part = path_part.split("#")[0]
            # Ensure path starts with /
            return (
                "/" + path_part
                if path_part and not path_part.startswith("/")
                else (path_part if path_part else "/")
            )
        else:
            # No path, just host - return root
            return "/"

    # It's already a relative URI - handle query string
    if "?" in uri:
        path = uri.split("?")[0]
    elif "#" in uri:
        path = uri.split("#")[0]
    else:
        path = uri

    # Ensure path starts with /
    return "/" + path if path and not path.startswith("/") else path
