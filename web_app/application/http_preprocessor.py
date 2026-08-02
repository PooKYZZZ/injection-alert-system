"""
web_app/application/http_preprocessor.py

Model-serving preprocessing: converts raw HTTP request text into the
canonicalized format expected by the ML model during training.

This module is for MODEL INPUT PREPROCESSING ONLY.

It is NOT the authoritative parser for security/persistence logic.
That role belongs to web_app.application.http_parsing (request_method,
request_path, raw http_request persistence).

Canonicalization matches the training pipeline (clean_907k.py) to reduce
training-serving skew at inference time.

---

Separation of Concerns:

- http_parsing.py: Security/persistence parsing for structured metadata
  (request_method, request_path) and raw forensic evidence (http_request).

- http_preprocessor.py: ML-serving preprocessing for model input text
  normalization (URL decode, HTML unescape, Unicode normalization,
  whitespace collapse, lowercase).

---

Design Rules:

1. Preprocessing is internal to the inference path only.
2. Raw http_request is always persisted verbatim — never preprocessed.
3. request_method and request_path come from http_parsing.py only.
4. Preprocessed text does NOT become an API response field.
5. The preprocessor fails safely on malformed input (returns empty string).
"""

import html
from hashlib import sha256
import re
import unicodedata
import urllib.parse


def canonicalize_text(text: str) -> str:
    """
    Canonicalize a text fragment to match training pipeline normalization.

    Applies (in order):
    - URL decode (%2F -> /, %2e%2e -> ..)
    - HTML unescape (& -> &)
    - NFKC Unicode normalization
    - Null byte stripping
    - Whitespace collapse
    - Lowercase

    Args:
        text: Input text to canonicalize

    Returns:
        Canonicalized lowercase text with normalized whitespace
    """
    if not isinstance(text, str):
        return ""
    text = urllib.parse.unquote(text)
    text = html.unescape(text)
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\x00", "")
    text = " ".join(text.split()).lower()
    return text


def parse_raw_http(raw_http: str) -> tuple[str, str, str]:
    """
    Parse a raw HTTP request string into (method, path, body).

    Strips the HTTP version suffix so path is clean — matching the
    ModSecurity/SR-BH log format seen during training.

    Args:
        raw_http: Full raw HTTP request string

    Returns:
        Tuple of (method, path, body). Empty strings if parsing fails.
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

    # Strip "HTTP/1.1" suffix before splitting on space
    # Without this: "GET /path?q=x HTTP/1.1" -> path = "/path?q=x HTTP/1.1"
    request_line = lines[0].strip()
    request_line = re.sub(r"\s+HTTP/[\d.]+\s*$", "", request_line, flags=re.IGNORECASE)

    parts = request_line.split(" ", 1)
    if len(parts) < 2:
        return "", "", ""

    method = parts[0].strip()
    path = parts[1].strip()
    if not method or not path:
        return "", "", ""

    return method, path, body.strip()


def preprocess_http_request(raw_http: str) -> str:
    """
    Convert a raw HTTP request string into the combined_payload format
    used during model training.

    This function is called in the inference path before tokenizing.
    It does NOT affect persistence — raw http_request is always stored verbatim.

    Args:
        raw_http: Full raw HTTP request string

    Returns:
        Canonicalized string matching training format.
        Example: "get /search?q=1' union select * from users--"

    Note:
        Malformed input returns empty string (safe failure — model will
        predict on empty input which produces a baseline "Normal" result).
    """
    method, path, body = parse_raw_http(raw_http)
    if not method or not path:
        return ""

    canonical_method = canonicalize_text(method)
    canonical_path = canonicalize_text(path)
    canonical_body = canonicalize_text(body)

    combined = f"{canonical_method} {canonical_path} {canonical_body}"
    combined = " ".join(combined.split())  # final whitespace collapse

    return combined


def prepare_model_input(raw_http: str) -> tuple[str, str, str]:
    """Return the exact model input, its hash, and preprocessing version.

    The raw fallback preserves the legacy payload-only prediction path while
    making its provenance explicit instead of pretending it was normalized.
    """
    preprocessed = preprocess_http_request(raw_http)
    if preprocessed:
        model_input = preprocessed
        preprocessing_version = "http-preprocessor-v1"
    else:
        model_input = raw_http if isinstance(raw_http, str) else ""
        preprocessing_version = "http-preprocessor-v1-raw-fallback"
    model_input_hash = sha256(model_input.encode("utf-8")).hexdigest()
    return model_input, model_input_hash, preprocessing_version
