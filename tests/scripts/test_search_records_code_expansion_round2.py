import json
import tempfile
from pathlib import Path

from scripts.search_records_code_expansion_round2 import (
    ROUND2_CASE_COUNT,
    ROUND2_CATALOG_VERSION,
    ROUND2_SEED_COUNT,
    build_round2_catalog,
    build_seed_snapshot,
    validate_round2_catalog,
)

ROOT = Path(__file__).resolve().parents[2]
ROUND_ONE_REPORT = (
    ROOT / "output" / "attack-tests" / "search-records-followup-results-20260903.json"
)
BASE_CATALOG = ROOT / "scripts" / "fixtures" / "search_records_attack_catalog.json"


def test_round_two_snapshot_preserves_70_positive_rows() -> None:
    snapshot = build_seed_snapshot(ROUND_ONE_REPORT)
    assert snapshot["seed_count"] == ROUND2_SEED_COUNT
    assert len(snapshot["cases"]) == ROUND2_SEED_COUNT
    assert len({entry["case"]["case_id"] for entry in snapshot["cases"]}) == 70
    assert all(
        entry["observed_result"]["predicted_label"] == "Code Injection"
        for entry in snapshot["cases"]
    )


def test_round_two_catalog_has_200_unique_local_search_cases() -> None:
    snapshot = build_seed_snapshot(ROUND_ONE_REPORT)
    # Build from a temporary snapshot so the test exercises the same fixture shape
    # that the CLI writes without depending on an ignored generated file.
    with tempfile.TemporaryDirectory() as directory:
        seed_path = Path(directory) / "seeds.json"
        seed_path.write_text(json.dumps(snapshot), encoding="utf-8")
        catalog = build_round2_catalog(
            seed_path=seed_path,
            base_catalog_path=BASE_CATALOG,
        )
    assert catalog["catalog_version"] == ROUND2_CATALOG_VERSION
    assert len(catalog["cases"]) == ROUND2_CASE_COUNT
    assert len({case["payload"] for case in catalog["cases"]}) == ROUND2_CASE_COUNT
    assert len({case["wire_query"] for case in catalog["cases"]}) == ROUND2_CASE_COUNT
    assert {case["expected_label"] for case in catalog["cases"]} == {"Code Injection"}
    assert {case["route_path"] for case in catalog["cases"]} == {"/records/search"}
    assert len({case["seed_id"] for case in catalog["cases"]}) == ROUND2_SEED_COUNT


def test_round_two_catalog_validates_from_disk(tmp_path: Path) -> None:
    snapshot = build_seed_snapshot(ROUND_ONE_REPORT)
    seed_path = tmp_path / "seeds.json"
    catalog_path = tmp_path / "catalog.json"
    seed_path.write_text(json.dumps(snapshot), encoding="utf-8")
    catalog = build_round2_catalog(seed_path=seed_path, base_catalog_path=BASE_CATALOG)
    catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
    assert len(validate_round2_catalog(catalog_path)["cases"]) == ROUND2_CASE_COUNT
