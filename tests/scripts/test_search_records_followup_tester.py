import hashlib
import json
from pathlib import Path
from urllib.parse import quote_plus

import pytest

from scripts.search_records_followup_tester import (
    _load_cases,
    _row_with_provenance,
)

ROOT = Path(__file__).resolve().parents[2]
CODE_CATALOG = (
    ROOT / "scripts" / "fixtures" / "search_records_code_expansion_catalog.json"
)


def test_followup_loader_can_select_code_family_without_other_routes() -> None:
    catalog, cases = _load_cases(CODE_CATALOG, "code_injection")
    assert catalog["route"] == {
        "method": "GET",
        "path": "/records/search",
        "query_parameter": "query",
    }
    assert len(cases) == 100
    assert all(case["family"] == "code_injection" for case in cases)
    assert all(
        case["request_uri"].startswith("/records/search?query=") for case in cases
    )


def test_followup_loader_allows_the_bounded_round_two_batch(tmp_path: Path) -> None:
    catalog = json.loads(CODE_CATALOG.read_text(encoding="utf-8"))
    first = catalog["cases"]
    cases = []
    for index in range(2):
        for original in first:
            case = dict(original)
            case_id = f"SR-CODE-RUN2-{index}-{original['case_id']}"
            payload = f"{original['payload']} /*batch-{index}*/"
            wire_query = quote_plus(payload, safe="")
            case.update(
                {
                    "case_id": case_id,
                    "payload": payload,
                    "wire_query": wire_query,
                    "request_uri": f"/records/search?query={wire_query}",
                    "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
                    "wire_sha256": hashlib.sha256(wire_query.encode()).hexdigest(),
                }
            )
            cases.append(case)
    synthetic = dict(
        catalog, cases=cases, safety=dict(catalog["safety"], maximum_cases=200)
    )
    path = tmp_path / "two-hundred.json"
    path.write_text(json.dumps(synthetic), encoding="utf-8")
    _, selected = _load_cases(path, "code_injection")
    assert len(selected) == 200


def test_followup_loader_rejects_more_than_one_bounded_run(tmp_path: Path) -> None:
    catalog = json.loads(CODE_CATALOG.read_text(encoding="utf-8"))
    extra = dict(catalog["cases"][0])
    payload = "(__import__('math').sqrt(4)) extra"
    wire_query = quote_plus(payload, safe="")
    extra.update(
        {
            "case_id": "SR-CODE-EXP-101",
            "payload": payload,
            "wire_query": wire_query,
            "request_uri": f"/records/search?query={wire_query}",
            "payload_sha256": hashlib.sha256(payload.encode()).hexdigest(),
            "wire_sha256": hashlib.sha256(wire_query.encode()).hexdigest(),
        }
    )
    catalog["cases"].append(extra)
    path = tmp_path / "too-many.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    with pytest.raises(ValueError, match="exceeds its declared case limit"):
        _load_cases(path, None)


def test_result_row_retains_seed_provenance_and_expected_waf() -> None:
    case = {
        "case_id": "SR-CODE-EXP-TEST",
        "seed_id": "SR-CODE-021",
        "source_seed_payload": "__import__('math').sqrt(4)",
        "family": "code_injection",
        "variant": "expansion",
        "mutation": "wrapper_variation",
        "description": "test",
        "ground_truth_status": "proposed_code_expansion",
        "replay_policy": "local_search_records_only",
        "payload": "(__import__('math').sqrt(4))",
        "wire_query": "%28__import__%28%27math%27%29.sqrt%284%29%29",
        "payload_sha256": "ignored-by-test",
        "wire_sha256": "ignored-by-test",
        "request_uri": "/records/search?query=ignored",
        "expected_label": "Code Injection",
        "expected_waf": "RECORD_OR_BLOCK",
        "is_seed": False,
    }
    audit = {
        "transaction": {
            "unique_id": "tx-followup-test",
            "request": {"uri": case["request_uri"]},
            "messages": [],
        }
    }
    lookup = {
        "found": True,
        "status": "COMPLETED",
        "prediction": "Code Injection",
        "confidence": 0.91,
        "confidence_level": "CRITICAL",
        "action_taken": "BLOCKED",
        "alert_id": 1,
    }
    row = _row_with_provenance(
        case,
        run_id="followup-test",
        environment="test",
        origin="http://demo-target-modsecurity:8080",
        status=403,
        duration_ms=1.0,
        request_error=None,
        audit_event=audit,
        lookup=lookup,
        lookup_error=None,
        catalog_version="search-records-code-expansion-v1",
    )
    assert row["source_seed_payload"] == "__import__('math').sqrt(4)"
    assert row["expected_waf"] == "RECORD_OR_BLOCK"
    assert row["predicted_label"] == "Code Injection"
    assert row["classification_correct"] == "True"
