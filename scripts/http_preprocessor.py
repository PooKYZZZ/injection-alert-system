"""
http_preprocessor.py

Converts a raw HTTP request string into the exact `combined_payload` format
that the model was trained on (matching clean_907k.py canonicalization).

Drop this into your backend and call `preprocess_http_request(raw_http)`
BEFORE passing text to the tokenizer in /api/predict.
"""

import re
import html
import unicodedata
import urllib.parse


# ── Canonicalization (must match clean_907k.py exactly) ──────────────────────

def canonicalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = urllib.parse.unquote(text)           # %2F -> /,  %2e%2e -> ..
    text = html.unescape(text)                  # &amp; -> &
    text = unicodedata.normalize("NFKC", text)  # unicode normalization
    text = text.replace("\x00", "")             # strip null bytes
    text = " ".join(text.split()).lower()        # collapse whitespace + lowercase
    return text


# ── Raw HTTP parser ───────────────────────────────────────────────────────────

def parse_raw_http(raw_http: str) -> tuple[str, str, str]:
    """
    Parse a raw HTTP request string into (method, path, body).
    Strips HTTP version string so path is clean — matching SR-BH log format.
    """
    if not raw_http or not isinstance(raw_http, str):
        return "", "", ""

    text = raw_http.replace("\r\n", "\n").replace("\r", "\n")

    if "\n\n" in text:
        header_section, body = text.split("\n\n", 1)
    else:
        header_section = text
        body = ""

    lines = header_section.strip().splitlines()
    if not lines:
        return "", "", ""

    # Strip "HTTP/1.1" from end of request line BEFORE splitting
    # Without this: "GET /path?q=x HTTP/1.1" -> path = "/path?q=x HTTP/1.1"
    request_line = lines[0].strip()
    request_line = re.sub(r"\s+HTTP/[\d.]+\s*$", "", request_line, flags=re.IGNORECASE)

    parts = request_line.split(" ", 1)
    method = parts[0] if len(parts) >= 1 else ""
    path   = parts[1] if len(parts) >= 2 else ""

    return method, path, body.strip()


# ── Public API ────────────────────────────────────────────────────────────────

def preprocess_http_request(raw_http: str) -> str:
    """
    Convert a raw HTTP request string into the combined_payload format
    used during model training. Call this in /api/predict before tokenizing.

    Args:
        raw_http: Full raw HTTP request string

    Returns:
        Canonicalized string matching training format
        e.g. "get /search?q=1' union select * from users--"
    """
    method, path, body = parse_raw_http(raw_http)

    canonical_method = canonicalize_text(method)
    canonical_path   = canonicalize_text(path)
    canonical_body   = canonicalize_text(body)

    combined = f"{canonical_method} {canonical_path} {canonical_body}"
    combined = " ".join(combined.split())  # final whitespace collapse

    return combined


# ── Verification test ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        ("SQLi - Union Select",
         "GET /search?q=1' UNION SELECT username,password FROM users-- HTTP/1.1\r\n"
         "Host: localhost\r\nUser-Agent: Mozilla/5.0\r\n\r\n"),

        ("SQLi - Auth bypass (POST body)",
         "POST /login HTTP/1.1\r\nHost: localhost\r\n"
         "Content-Type: application/x-www-form-urlencoded\r\n\r\n"
         "username=admin' OR '1'='1&password=test"),

        ("Path Traversal - URL encoded",
         "GET /files/%2e%2e%2f%2e%2e%2fetc%2fshadow HTTP/1.1\r\n"
         "Host: localhost\r\n\r\n"),

        ("Normal - Add to cart",
         "POST /api/cart/items HTTP/1.1\r\nHost: localhost\r\n"
         "Content-Type: application/json\r\n\r\n"
         '{"product_id": 123, "quantity": 2}'),

        ("Normal - GET products",
         "GET /products?page=1&limit=20 HTTP/1.1\r\n"
         "Host: localhost\r\nAccept: application/json\r\n\r\n"),

        ("OS Command - Pipe",
         "POST /api/report HTTP/1.1\r\nHost: localhost\r\n"
         "Content-Type: application/json\r\n\r\n"
         '{"target": "localhost | cat /etc/shadow"}'),

        ("SQLi - Time-based blind",
         "GET /products?id=1 AND SLEEP(5) HTTP/1.1\r\n"
         "Host: localhost\r\nUser-Agent: Mozilla/5.0\r\n\r\n"),

        ("Code Injection - PHP",
         "GET /api/echo?text=<?php system($_GET['cmd']); ?>&cmd=whoami HTTP/1.1\r\n"
         "Host: localhost\r\n\r\n"),
    ]

    print("=" * 72)
    print("http_preprocessor — output verification")
    print("=" * 72)

    for name, raw in test_cases:
        result = preprocess_http_request(raw)
        raw_preview = raw.replace("\r\n", " | ")[:70]
        print(f"\n  [{name}]")
        print(f"  RAW : {raw_preview!r}")
        print(f"  OUT : {result!r}")

    print("\n" + "=" * 72)
    print("Good output = lowercase, no HTTP/1.1, no Host:/User-Agent: noise")
    print("=" * 72)
