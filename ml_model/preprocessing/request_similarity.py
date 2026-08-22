"""Comparison-only canonicalization shared by contamination and golden checks."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from ml_model.preprocessing.model_input import canonicalize_text


def canonicalize_similarity_text(value: str) -> str:
    """Canonicalize request text without changing the serving model-input contract.

    Query parameters are sorted as decoded key/value pairs, preserving blank
    values and repeated parameters.  This representation is used only for
    duplicate and near-duplicate comparisons.
    """

    normalized = canonicalize_text(value)
    parts = normalized.split(maxsplit=1)
    if len(parts) != 2:
        return normalized
    method, target = parts
    try:
        parsed = urlsplit(target)
    except ValueError:
        # Comparison canonicalization must remain total for already-frozen
        # model-input text. Malformed targets are compared in their normalized
        # form; this does not alter serving text or weaken dataset validation.
        return normalized
    if not parsed.query:
        return normalized
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    canonical_query = urlencode(sorted(query_pairs), doseq=True)
    canonical_target = urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, canonical_query, parsed.fragment)
    )
    return f"{method} {canonical_target}"
