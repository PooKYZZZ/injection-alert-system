from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

import pytest

from scripts.search_records_attack_catalog import (
    EXPECTED_LABELS,
    ROUTE_PATH,
    build_cases,
    build_catalog,
    load_catalog,
)


def test_seed_catalog_has_ten_cases_per_family() -> None:
    catalog = build_catalog("seeds")
    assert len(catalog["cases"]) == 30
    assert Counter(case["family"] for case in catalog["cases"]) == {
        "sql_injection": 10,
        "code_injection": 10,
        "general_attack": 10,
    }
    assert all(case["is_seed"] for case in catalog["cases"])


def test_full_catalog_has_fifty_cases_per_family() -> None:
    catalog = build_catalog("full")
    assert len(catalog["cases"]) == 150
    assert Counter(case["family"] for case in catalog["cases"]) == {
        "sql_injection": 50,
        "code_injection": 50,
        "general_attack": 50,
    }


def test_full_catalog_has_unique_cases_and_wire_values() -> None:
    cases = build_cases("full")
    assert len({case.case_id for case in cases}) == 150
    assert len({case.wire_query for case in cases}) == 150
    for case in cases:
        assert case.request_uri == f"{ROUTE_PATH}?query={case.wire_query}"
        assert case.expected_label == EXPECTED_LABELS[case.family]
        assert (
            case.payload_sha256
            == hashlib.sha256(case.payload.encode("utf-8")).hexdigest()
        )


def test_each_seed_has_five_meaningful_variants() -> None:
    cases = build_cases("full")
    for seed_id in {case.seed_id for case in cases}:
        seed_cases = [case for case in cases if case.seed_id == seed_id]
        assert {case.variant for case in seed_cases} == {
            "seed",
            "spacing",
            "case",
            "delimiter",
            "obfuscation",
        }
        assert len({case.payload for case in seed_cases}) == 5


def test_code_seeds_are_inert_and_do_not_include_file_or_network_actions() -> None:
    code_cases = [
        case.payload for case in build_cases("seeds") if case.family == "code_injection"
    ]
    joined = "\n".join(code_cases).lower()
    for forbidden in ("curl", "wget", "os.system", "/etc/passwd", "rm -rf"):
        assert forbidden not in joined


def test_checked_in_catalogue_round_trips() -> None:
    path = Path("scripts/fixtures/search_records_attack_catalog.json")
    catalog = load_catalog(path)
    assert len(catalog["cases"]) == 150
    assert catalog["route"] == {
        "method": "GET",
        "path": "/records/search",
        "query_parameter": "query",
    }


def test_catalogue_rejects_non_search_route(tmp_path: Path) -> None:
    catalog = build_catalog("seeds")
    catalog["route"]["path"] = "/dashboard"
    path = tmp_path / "invalid.json"
    path.write_text(__import__("json").dumps(catalog), encoding="utf-8")
    with pytest.raises(ValueError, match="records/search"):
        load_catalog(path)
