from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ml_model.evaluation.golden_controls import (
    GoldenControlError,
    GoldenOverlapError,
    evaluate_golden_controls,
    find_golden_overlap,
    load_golden_controls,
)
from ml_model.preprocessing.request_similarity import canonicalize_similarity_text
from ml_model.retraining.experiment_contract import canonical_json_sha256

THRESHOLDS = {"low": 0.50, "high": 0.80, "critical": 0.90}
ACTIONS = {
    "normal": "ALLOWED",
    "low": "ALLOWED",
    "medium": "THROTTLED",
    "high": "BLOCKED",
    "critical": "BLOCKED",
}


def _write_locked_golden(tmp_path: Path, cases: list[dict]) -> Path:
    cases_path = tmp_path / "golden_cases.jsonl"
    cases_path.write_bytes(
        b"".join(
            (json.dumps(case, sort_keys=True, separators=(",", ":")) + "\n").encode()
            for case in cases
        )
    )
    manifest = {
        "manifest_version": "golden-manifest.v1",
        "golden_version": "golden-v1",
        "cases_file": cases_path.name,
        "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        "case_count": len(cases),
    }
    manifest["manifest_sha256"] = canonical_json_sha256(manifest)
    manifest_path = tmp_path / "golden_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def _case(case_id: str, text: str, label: str, action: str, category: str) -> dict:
    return {
        "case_id": case_id,
        "model_input_text": text,
        "expected_label": label,
        "expected_action": action,
        "category": category,
        "source_type": "controlled_fixture",
        "rationale": "bounded control",
        "reviewer": "experiment-owner",
        "golden_version": "golden-v1",
        "locked_at": "2026-08-06T00:00:00Z",
    }


def _target_case(
    case_id: str,
    text: str,
    label: str,
    action: str,
    category: str,
    *,
    request_path: str = "/records/search",
    route_scope: str = "target_route",
) -> dict:
    case = _case(case_id, text, label, action, category)
    case.update(
        {
            "golden_version": "golden-v2",
            "request_method": "GET",
            "request_path": request_path,
            "route_scope": route_scope,
        }
    )
    return case


def _write_target_locked_golden(tmp_path: Path, cases: list[dict]) -> Path:
    cases_path = tmp_path / "golden_cases.jsonl"
    cases_path.write_bytes(
        b"".join(
            (json.dumps(case, sort_keys=True, separators=(",", ":")) + "\n").encode()
            for case in cases
        )
    )
    manifest = {
        "manifest_version": "golden-manifest.v1",
        "golden_version": "golden-v2",
        "cases_file": cases_path.name,
        "cases_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
        "case_count": len(cases),
        "target_method": "GET",
        "target_route": "/records/search",
        "target_case_count": sum(
            case.get("route_scope") == "target_route" for case in cases
        ),
    }
    manifest["manifest_sha256"] = canonical_json_sha256(manifest)
    manifest_path = tmp_path / "golden_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def test_loader_validates_manifest_and_exact_pagination_control(tmp_path: Path):
    manifest_path = _write_locked_golden(
        tmp_path,
        [
            _case(
                "normal-pagination-exact",
                "GET /api/users?page=1&limit=10",
                "Normal",
                "ALLOWED",
                "normal_pagination",
            )
        ],
    )

    controls = load_golden_controls(manifest_path)

    assert controls.golden_version == "golden-v1"
    assert controls.cases[0].model_input_text == "GET /api/users?page=1&limit=10"


def test_evaluator_reports_predictions_and_fails_mandatory_control(tmp_path: Path):
    manifest_path = _write_locked_golden(
        tmp_path,
        [
            _case(
                "normal-pagination-exact",
                "GET /api/users?page=1&limit=10",
                "Normal",
                "ALLOWED",
                "normal_pagination",
            ),
            _case(
                "sql-control",
                "GET /items?id=1 UNION SELECT password FROM users",
                "SQL Injection",
                "BLOCKED",
                "sql_injection",
            ),
        ],
    )

    result = evaluate_golden_controls(
        load_golden_controls(manifest_path),
        lambda text: {
            "label": "SQL Injection",
            "confidence": 0.95,
        },
        confidence_thresholds=THRESHOLDS,
        response_actions=ACTIONS,
    )

    assert result.passed is False
    assert result.mandatory_failures == ["normal-pagination-exact"]
    assert result.cases[0]["predicted_label"] == "SQL Injection"
    assert result.cases[0]["predicted_action"] == "BLOCKED"
    assert result.category_results["sql_injection"]["passed"] is True


def test_evaluator_reports_declared_manifest_hash(tmp_path: Path):
    manifest_path = _write_locked_golden(
        tmp_path,
        [
            _case(
                "normal-pagination-exact",
                "GET /api/users?page=1&limit=10",
                "Normal",
                "ALLOWED",
                "normal_pagination",
            )
        ],
    )
    controls = load_golden_controls(manifest_path)

    result = evaluate_golden_controls(
        controls,
        lambda text: {"label": "Normal", "confidence": 0.99},
        confidence_thresholds=THRESHOLDS,
        response_actions=ACTIONS,
    )

    assert result.to_dict()["manifest_sha256"] == controls.manifest["manifest_sha256"]


def test_evaluator_uses_contract_thresholds_and_actions(tmp_path: Path):
    controls = load_golden_controls(
        _write_locked_golden(
            tmp_path,
            [
                _case(
                    "sql-control",
                    "GET /items?id=1 UNION SELECT password FROM users",
                    "SQL Injection",
                    "THROTTLED",
                    "sql_injection",
                )
            ],
        )
    )

    result = evaluate_golden_controls(
        controls,
        lambda text: {"label": "SQL Injection", "confidence": 0.75},
        confidence_thresholds={"low": 0.40, "high": 0.70, "critical": 0.95},
        response_actions={
            "normal": "ALLOWED",
            "low": "ALLOWED",
            "medium": "THROTTLED",
            "high": "THROTTLED",
            "critical": "BLOCKED",
        },
    )

    assert result.passed is True
    assert result.cases[0]["predicted_action"] == "THROTTLED"


def test_evaluator_ignores_untrusted_model_supplied_confidence_tier(tmp_path: Path):
    controls = load_golden_controls(
        _write_locked_golden(
            tmp_path,
            [
                _case(
                    "sql-control",
                    "GET /items?id=1 UNION SELECT password FROM users",
                    "SQL Injection",
                    "THROTTLED",
                    "sql_injection",
                )
            ],
        )
    )

    result = evaluate_golden_controls(
        controls,
        lambda text: {
            "label": "SQL Injection",
            "confidence": 0.75,
            "confidence_tier": "CRITICAL",
        },
        confidence_thresholds=THRESHOLDS,
        response_actions=ACTIONS,
    )

    assert result.passed is True
    assert result.cases[0]["confidence_tier"] == "MEDIUM"
    assert result.cases[0]["predicted_action"] == "THROTTLED"


def test_golden_overlap_rejects_exact_and_near_duplicate_text(tmp_path: Path):
    controls = load_golden_controls(
        _write_locked_golden(
            tmp_path,
            [
                _case(
                    "normal-pagination-exact",
                    "GET /api/users?page=1&limit=10",
                    "Normal",
                    "ALLOWED",
                    "normal_pagination",
                )
            ],
        )
    )

    overlaps = find_golden_overlap(
        controls,
        [
            {
                "sample_id": "exact",
                "model_input_text": "GET /api/users?page=1&limit=10",
            },
            {"sample_id": "near", "model_input_text": "GET /api/users?page=1&limit=11"},
        ],
        near_duplicate_threshold=0.90,
    )

    assert [row["sample_id"] for row in overlaps] == ["exact", "near"]
    try:
        controls.assert_no_overlap(
            [
                {
                    "sample_id": "exact",
                    "model_input_text": "GET /api/users?page=1&limit=10",
                }
            ]
        )
    except GoldenOverlapError:
        pass
    else:
        raise AssertionError("golden overlap was not rejected")


def test_similarity_canonicalizes_query_order_blank_repeated_and_encoded_values():
    first = "GET /api/search?alpha=one%20two&empty=&tag=a&tag=b"
    reordered = "GET /api/search?tag=b&alpha=one+two&tag=a&empty="

    assert canonicalize_similarity_text(first) == canonicalize_similarity_text(
        reordered
    )
    assert canonicalize_similarity_text(first) != canonicalize_similarity_text(
        "GET /api/search?alpha=other&empty=&tag=a&tag=b"
    )
    assert canonicalize_similarity_text(first) != canonicalize_similarity_text(
        "GET /api/other?alpha=one%20two&empty=&tag=a&tag=b"
    )


def test_similarity_is_total_for_malformed_url_targets():
    malformed = "GET /[invalid-ipv6]?query=value"

    assert canonicalize_similarity_text(malformed) == "get /[invalid-ipv6]?query=value"


def test_golden_overlap_uses_canonical_query_order(tmp_path: Path):
    controls = load_golden_controls(
        _write_locked_golden(
            tmp_path,
            [
                _case(
                    "search-control",
                    "GET /api/search?alpha=one%20two&empty=&tag=a&tag=b",
                    "Normal",
                    "ALLOWED",
                    "normal_search",
                )
            ],
        )
    )

    overlaps = find_golden_overlap(
        controls,
        [
            {
                "sample_id": "reordered-search",
                "model_input_text": (
                    "GET /api/search?tag=b&alpha=one+two&tag=a&empty="
                ),
            }
        ],
    )

    assert overlaps[0]["matches"][0]["similarity"] == 1.0


def test_checked_in_golden_v2_targets_records_search_and_preserves_legacy_regression():
    root = Path(__file__).resolve().parents[2]
    controls = load_golden_controls(
        root
        / "data/experiments/retraining_20_day_v1/golden/golden-v2/golden_manifest.json"
    )

    target_cases = [
        case for case in controls.cases if case.get("route_scope") == "target_route"
    ]
    legacy_cases = [
        case
        for case in controls.cases
        if case.get("route_scope") == "legacy_regression"
    ]

    assert controls.golden_version == "golden-v2"
    assert controls.manifest["target_method"] == "GET"
    assert controls.manifest["target_route"] == "/records/search"
    assert controls.manifest["target_case_count"] == 28
    assert len(target_cases) == 28
    assert all(case["request_method"] == "GET" for case in target_cases)
    assert all(case["request_path"] == "/records/search" for case in target_cases)
    assert not any("/api/users" in case.model_input_text for case in target_cases)
    assert len(legacy_cases) == 1
    assert legacy_cases[0].model_input_text == "GET /api/users?page=1&limit=10"


def test_target_golden_requires_route_metadata(tmp_path: Path):
    case = _case(
        "normal-search",
        "GET /records/search?query=Maple",
        "Normal",
        "ALLOWED",
        "normal_search",
    )
    case["golden_version"] = "golden-v2"
    case["route_scope"] = "target_route"

    with pytest.raises(GoldenControlError, match="route metadata"):
        load_golden_controls(_write_target_locked_golden(tmp_path, [case]))


def test_target_golden_rejects_case_outside_declared_route(tmp_path: Path):
    case = _target_case(
        "wrong-route",
        "GET /api/users?page=1&limit=10",
        "Normal",
        "ALLOWED",
        "legacy_regression",
        request_path="/api/users",
    )

    with pytest.raises(GoldenControlError, match="does not match target route"):
        load_golden_controls(_write_target_locked_golden(tmp_path, [case]))
