import json
from pathlib import Path

import pytest

from scripts.panel_attack_catalog import (
    DEFAULT_CATALOG,
    DEFAULT_FIXTURES,
    apply_variant,
    expand_catalog,
    load_fixture_requests,
    render_markdown,
)


def test_checked_in_catalog_expands_all_cases_without_duplicate_hashes():
    rows = expand_catalog(catalog_path=DEFAULT_CATALOG, fixtures_path=DEFAULT_FIXTURES)

    assert len(rows) == 28
    assert len({row["case_id"] for row in rows}) == len(rows)
    assert all(len(row["input_sha256"]) == 64 for row in rows)
    assert {row["family"] for row in rows} == {
        "normal",
        "sql_injection",
        "code_injection",
        "other_attacks",
    }
    assert {row["http_request"].split(None, 1)[0] for row in rows} <= {"GET", "POST"}


def test_catalog_preserves_identity_fixture_requests():
    fixtures = load_fixture_requests(DEFAULT_FIXTURES)
    rows = expand_catalog(catalog_path=DEFAULT_CATALOG, fixtures_path=DEFAULT_FIXTURES)

    identity_rows = [row for row in rows if row["variant"] == "identity"]
    for row in identity_rows:
        assert row["http_request"] == fixtures[row["source_fixture_id"]]


@pytest.mark.parametrize(
    "variant",
    [
        "append_benign_query",
        "query_case",
        "encoded_spaces",
        "lower_header_names",
        "crlf",
    ],
)
def test_non_identity_variants_are_deterministic(variant):
    request = "GET /search?q=One%20Two HTTP/1.1\nHost: localhost\n"

    first = apply_variant(request, variant)
    second = apply_variant(request, variant)

    assert first == second
    assert first


def test_json_key_order_updates_body_content_length():
    request = (
        'POST /render HTTP/1.1\nHost: localhost\nContent-Length: 7\n\n{"z":1,"a":2}'
    )

    transformed = apply_variant(request, "json_key_order")

    assert "Content-Length: 13" in transformed
    assert transformed.endswith('{"a":2,"z":1}')


def test_rendered_catalog_contains_metadata_but_not_fixture_request_text():
    rendered = render_markdown(DEFAULT_CATALOG)

    assert "panelist-local-v1" in rendered
    assert "SQL-001" in rendered
    assert "offline_only" in rendered
    assert "GET /login?id=1%20OR%201=1-- HTTP/1.1" not in rendered


def test_catalog_rejects_unknown_fixture_reference(tmp_path: Path):
    catalog = json.loads(DEFAULT_CATALOG.read_text(encoding="utf-8"))
    catalog["cases"][0]["source_fixture_id"] = "missing-fixture"
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")

    with pytest.raises(ValueError, match="unknown fixture"):
        expand_catalog(catalog_path=catalog_path, fixtures_path=DEFAULT_FIXTURES)
