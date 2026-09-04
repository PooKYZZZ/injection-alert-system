from pathlib import Path

from scripts.search_records_followup_catalog import (
    KNOWN_CODE_SEEDS,
    SAFE_NORMAL_QUERY,
    build_code_expansion_catalog,
    build_normal_catalog,
    validate_followup_catalog,
)

ROOT = Path(__file__).resolve().parents[2]
KNOWN_CODE_FIXTURE = (
    ROOT / "scripts" / "fixtures" / "search_records_known_code_seeds.json"
)
BASE_CATALOG = ROOT / "scripts" / "fixtures" / "search_records_attack_catalog.json"


def test_code_expansion_has_100_unique_search_route_cases() -> None:
    catalog = build_code_expansion_catalog(
        known_code_path=KNOWN_CODE_FIXTURE,
        base_catalog_path=BASE_CATALOG,
    )
    assert len(catalog["cases"]) == 100
    assert {case["family"] for case in catalog["cases"]} == {"code_injection"}
    assert {case["expected_label"] for case in catalog["cases"]} == {
        "Code Injection"
    }
    assert len({case["wire_query"] for case in catalog["cases"]}) == 100
    assert {case["seed_id"] for case in catalog["cases"]} == set(KNOWN_CODE_SEEDS)
    assert all(case["route_path"] == "/records/search" for case in catalog["cases"])
    assert all(case["method"] == "GET" for case in catalog["cases"])
    assert all(case["expected_waf"] == "RECORD_OR_BLOCK" for case in catalog["cases"])


def test_normal_catalog_has_50_benign_search_queries() -> None:
    catalog = build_normal_catalog()
    assert len(catalog["cases"]) == 50
    assert {case["family"] for case in catalog["cases"]} == {"normal_traffic"}
    assert {case["expected_label"] for case in catalog["cases"]} == {"Normal"}
    assert all(
        SAFE_NORMAL_QUERY.fullmatch(case["payload"]) for case in catalog["cases"]
    )
    assert all(case["expected_waf"] == "ALLOW_EXPECTED" for case in catalog["cases"])


def test_generated_followup_catalogs_validate_from_disk() -> None:
    code_path = (
        ROOT / "scripts" / "fixtures" / "search_records_code_expansion_catalog.json"
    )
    normal_path = ROOT / "scripts" / "fixtures" / "search_records_normal_baseline.json"
    assert len(validate_followup_catalog(code_path)["cases"]) == 100
    assert len(validate_followup_catalog(normal_path)["cases"]) == 50
