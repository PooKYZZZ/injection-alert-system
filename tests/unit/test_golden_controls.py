from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ml_model.evaluation.golden_controls import (
    GoldenOverlapError,
    evaluate_golden_controls,
    find_golden_overlap,
    load_golden_controls,
)
from ml_model.retraining.experiment_contract import canonical_json_sha256


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
    )

    assert result.passed is False
    assert result.mandatory_failures == ["normal-pagination-exact"]
    assert result.cases[0]["predicted_label"] == "SQL Injection"
    assert result.cases[0]["predicted_action"] == "BLOCKED"
    assert result.category_results["sql_injection"]["passed"] is True


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
