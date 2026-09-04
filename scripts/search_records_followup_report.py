"""Combine preserved Search Records evidence with follow-up test results.

The report separates immutable baseline evidence from newly observed outcomes:
the original SQL cases, original confirmed code seeds, code-expansion successes
and failures, and benign normal-traffic outcomes. Result files are local
runtime evidence; this module does not alter model artifacts or policy values.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from scripts.search_records_followup_catalog import (
    CODE_CATALOG_VERSION,
    NORMAL_CATALOG_VERSION,
    ROUTE_PATH,
    validate_followup_catalog,
)

EXPECTED_ROUTE = {"method": "GET", "path": ROUTE_PATH, "query_parameter": "query"}
REQUIRED_RESULT_FIELDS = {
    "case_id",
    "family",
    "payload",
    "expected_label",
    "predicted_label",
    "classification_correct",
    "confidence",
    "confidence_level",
    "transaction_id",
    "bridge_found",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read JSON file: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _read_result_report(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = _read_json(path)
    metadata = payload.get("metadata")
    rows = payload.get("rows")
    if not isinstance(metadata, dict) or not isinstance(rows, list):
        raise ValueError(f"result report must contain metadata and rows: {path}")
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"result row {index} is not an object: {path}")
        missing = REQUIRED_RESULT_FIELDS - row.keys()
        if missing:
            raise ValueError(
                f"result row {index} is missing {sorted(missing)}: {path}"
            )
    if metadata.get("route_path") != ROUTE_PATH or metadata.get("method") != "GET":
        raise ValueError(f"result report is outside Search Records: {path}")
    return metadata, rows


def _read_baseline(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if payload.get("route") != EXPECTED_ROUTE:
        raise ValueError(f"baseline is outside Search Records: {path}")
    for key in (
        "original_sql_injection_cases",
        "original_code_injection_cases",
        "original_code_injection_positive_cases",
        "original_seed_cases",
    ):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"baseline is missing {key}: {path}")
    if len(payload["original_sql_injection_cases"]) != 50:
        raise ValueError("preserved SQL baseline must contain 50 cases")
    if len(payload["original_code_injection_cases"]) != 50:
        raise ValueError("preserved code baseline must contain 50 cases")
    if len(payload["original_code_injection_positive_cases"]) != 12:
        raise ValueError("preserved code baseline must contain 12 cases")
    return payload


def _ensure_catalog_count(path: Path, expected: int, version: str) -> None:
    catalog = validate_followup_catalog(path)
    if catalog.get("catalog_version") != version:
        raise ValueError(f"unexpected catalogue version: {path}")
    if len(catalog["cases"]) != expected:
        raise ValueError(f"catalogue must contain {expected} cases: {path}")


def _catalog_case_map(path: Path) -> dict[str, dict[str, Any]]:
    catalog = validate_followup_catalog(path)
    return {str(case["case_id"]): case for case in catalog["cases"]}


def _status_rows(rows: Iterable[dict[str, Any]], correct: bool) -> list[dict[str, Any]]:
    expected = "True" if correct else "False"
    return [row for row in rows if row.get("classification_correct") == expected]


def _label_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row.get("predicted_label") or "<missing>" for row in rows)
    return dict(sorted(counts.items()))


def _confidence_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row.get("confidence_level") or "<missing>" for row in rows)
    return dict(sorted(counts.items()))


def _mutation_summary(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("mutation") or "<missing>")].append(row)
    summary: dict[str, dict[str, Any]] = {}
    for mutation, mutation_rows in sorted(grouped.items()):
        correct = len(_status_rows(mutation_rows, True))
        summary[mutation] = {
            "tested": len(mutation_rows),
            "correct": correct,
            "accuracy_percent": round(100 * correct / len(mutation_rows), 2),
            "predicted_labels": _label_counts(mutation_rows),
        }
    return summary


def _correlation_summary(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    rows = list(rows)
    return {
        "tested": len(rows),
        "requests_executed": sum(
            row.get("request_executed") == "True" for row in rows
        ),
        "audit_correlated": sum(bool(row.get("transaction_id")) for row in rows),
        "bridge_correlated": sum(row.get("bridge_found") == "True" for row in rows),
        "terminal_predictions": sum(
            bool(row.get("predicted_label")) and bool(row.get("confidence"))
            for row in rows
        ),
    }


def _validate_result_family(
    rows: list[dict[str, Any]],
    *,
    family: str,
    expected_label: str,
    catalog_cases: dict[str, dict[str, Any]],
) -> None:
    seen_ids: set[str] = set()
    for row in rows:
        case_id = str(row.get("case_id") or "")
        if case_id in seen_ids:
            raise ValueError(f"result repeats case ID: {case_id}")
        case = catalog_cases.get(case_id)
        if case is None:
            raise ValueError(f"result case is absent from catalogue: {case_id}")
        if row.get("family") != family:
            raise ValueError(f"result contains an unexpected family: {case_id}")
        if row.get("expected_label") != expected_label:
            raise ValueError(
                f"result has an unexpected expected label: {case_id}"
            )
        if row.get("route_path") != ROUTE_PATH or row.get("method") != "GET":
            raise ValueError(f"result case is outside Search Records: {case_id}")
        for key in (
            "payload",
            "wire_query",
            "seed_id",
            "mutation",
            "expected_label",
        ):
            if str(row.get(key) or "") != str(case.get(key) or ""):
                raise ValueError(f"result does not match catalogue {key}: {case_id}")
        if family == "code_injection" and str(
            row.get("source_seed_payload") or ""
        ) != str(case.get("source_seed_payload") or ""):
            raise ValueError(f"result does not match catalogue source seed: {case_id}")
        seen_ids.add(case_id)


def build_report(
    *,
    baseline_path: Path,
    code_catalog_path: Path,
    normal_catalog_path: Path,
    code_report_path: Path,
    normal_report_path: Path,
) -> dict[str, Any]:
    baseline = _read_baseline(baseline_path)
    _ensure_catalog_count(code_catalog_path, 100, CODE_CATALOG_VERSION)
    _ensure_catalog_count(normal_catalog_path, 50, NORMAL_CATALOG_VERSION)
    code_catalog_cases = _catalog_case_map(code_catalog_path)
    normal_catalog_cases = _catalog_case_map(normal_catalog_path)
    code_metadata, code_rows = _read_result_report(code_report_path)
    normal_metadata, normal_rows = _read_result_report(normal_report_path)
    if code_metadata.get("catalog_version") != CODE_CATALOG_VERSION:
        raise ValueError("code result does not match code expansion catalogue")
    if normal_metadata.get("catalog_version") != NORMAL_CATALOG_VERSION:
        raise ValueError("normal result does not match normal catalogue")
    _validate_result_family(
        code_rows,
        family="code_injection",
        expected_label="Code Injection",
        catalog_cases=code_catalog_cases,
    )
    _validate_result_family(
        normal_rows,
        family="normal_traffic",
        expected_label="Normal",
        catalog_cases=normal_catalog_cases,
    )
    if len(code_rows) != 100:
        raise ValueError(
            f"code expansion report must contain 100 rows, found {len(code_rows)}"
        )
    if len(normal_rows) != 50:
        raise ValueError(
            f"normal baseline report must contain 50 rows, found {len(normal_rows)}"
        )

    code_correct = _status_rows(code_rows, True)
    code_misclassified = _status_rows(code_rows, False)
    normal_correct = _status_rows(normal_rows, True)
    normal_false_positives = _status_rows(normal_rows, False)
    original_code_correct = baseline["original_code_injection_positive_cases"]
    original_code_count = len(original_code_correct)
    original_full_code_count = len(baseline["original_code_injection_cases"])
    combined_catalog_count = 50 + len(code_rows)
    combined_correct = original_code_count + len(code_correct)

    summary = {
        "route": EXPECTED_ROUTE,
        "baseline": {
            "original_sql_injection_cases": 50,
            "original_confirmed_code_injection_cases": original_code_count,
            "original_seed_cases": len(baseline["original_seed_cases"]),
            "original_full_code_cases": original_full_code_count,
            "original_full_code_accuracy_percent": round(
                100 * original_code_count / original_full_code_count, 2
            ),
        },
        "code_expansion": {
            "new_variations_tested": len(code_rows),
            "new_correctly_classified": len(code_correct),
            "new_accuracy_percent": round(100 * len(code_correct) / len(code_rows), 2),
            "new_predicted_label_counts": _label_counts(code_rows),
            "misclassified_predicted_label_counts": _label_counts(code_misclassified),
            "confidence_level_counts": _confidence_counts(code_rows),
            "mutation_summary": _mutation_summary(code_rows),
            "correlation": _correlation_summary(code_rows),
        },
        "combined_original_50_plus_new_100": {
            "tested": combined_catalog_count,
            "correct": combined_correct,
            "accuracy_percent": round(
                100 * combined_correct / combined_catalog_count, 2
            ),
        },
        "confirmed_seed_plus_new_variations": {
            "tested": original_code_count + len(code_rows),
            "correct": combined_correct,
            "accuracy_percent": round(
                100 * combined_correct / (original_code_count + len(code_rows)), 2
            ),
        },
        "normal_traffic": {
            "tested": len(normal_rows),
            "correctly_classified_normal": len(normal_correct),
            "accuracy_percent": round(100 * len(normal_correct) / len(normal_rows), 2),
            "false_positive_count": len(normal_false_positives),
            "false_positive_predicted_label_counts": _label_counts(
                normal_false_positives
            ),
            "false_positive_confidence_level_counts": _confidence_counts(
                normal_false_positives
            ),
            "confidence_level_counts": _confidence_counts(normal_rows),
            "correlation": _correlation_summary(normal_rows),
        },
    }
    return {
        "schema_version": 1,
        "report_type": "search_records_followup_results",
        "preservation_note": (
            "Baseline groups are copied from the original result files before "
            "follow-up traffic was generated. New groups preserve every observed "
            "code and normal result, including unsuccessful classifications."
        ),
        "source_files": {
            "baseline": str(baseline_path),
            "code_catalog": str(code_catalog_path),
            "normal_catalog": str(normal_catalog_path),
            "code_report": str(code_report_path),
            "normal_report": str(normal_report_path),
        },
        "summary": summary,
        "groups": {
            "known_sql_injection_cases": baseline["original_sql_injection_cases"],
            "original_known_code_injection_cases": original_code_correct,
            "original_seed_cases": baseline["original_seed_cases"],
            "expanded_known_code_injection_cases": code_correct,
            "misclassified_code_injection_cases": code_misclassified,
            "known_normal_traffic": normal_correct,
            "normal_false_positives": normal_false_positives,
        },
    }


def _table_rows(rows: Iterable[dict[str, Any]]) -> list[str]:
    lines = []
    for row in rows:
        payload = (
            str(row.get("payload", "")).replace("|", "\\|").replace("\n", "\\n")
        )
        lines.append(
            "| {case_id} | {seed_id} | {mutation} | {payload} | {predicted_label} | "
            "{confidence} | {confidence_level} | {correct} |".format(
                case_id=row.get("case_id", ""),
                seed_id=row.get("seed_id", ""),
                mutation=row.get("mutation", ""),
                payload=payload,
                predicted_label=row.get("predicted_label", ""),
                confidence=row.get("confidence", ""),
                confidence_level=row.get("confidence_level", ""),
                correct=row.get("classification_correct", ""),
            )
        )
    return lines


def to_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    code = summary["code_expansion"]
    normal = summary["normal_traffic"]
    baseline_summary = summary["baseline"]
    combined = summary["combined_original_50_plus_new_100"]
    lines = [
        "# Search Records follow-up results",
        "",
        "Scope: local demo portal GET /records/search?query=... only.",
        "All rows retain exact payloads in the JSON report.",
        "",
        "## Summary",
        "",
        "- Preserved SQL baseline: "
        f"{baseline_summary['original_sql_injection_cases']} cases.",
        "- Preserved original Code Injection positives: "
        f"{baseline_summary['original_confirmed_code_injection_cases']} cases.",
        "- New Code Injection variations: "
        f"{code['new_correctly_classified']}/{code['new_variations_tested']} "
        f"correct ({code['new_accuracy_percent']}%).",
        "- Combined original 50 + new 100 Code Injection catalogue: "
        f"{combined['correct']}/{combined['tested']} correct "
        f"({combined['accuracy_percent']}%).",
        "- Normal traffic: "
        f"{normal['correctly_classified_normal']}/{normal['tested']} correct "
        f"({normal['accuracy_percent']}%); "
        f"false positives={normal['false_positive_count']}.",
        "",
        "## Code-expansion predicted labels",
        "",
        "JSON values are stored in the report alongside the exact rows.",
        json.dumps(code["new_predicted_label_counts"], indent=2, sort_keys=True),
        "",
        "## Code-expansion mutation summary",
        "",
        "| Mutation | Tested | Correct | Accuracy |",
        "| --- | ---: | ---: | ---: |",
    ]
    for mutation, values in code["mutation_summary"].items():
        lines.append(
            f"| {mutation} | {values['tested']} | {values['correct']} | "
            f"{values['accuracy_percent']}% |"
        )
    lines.extend(
        [
            "",
            "## Misclassified Code Injection cases",
            "",
            "| Case | Seed | Mutation | Exact payload | Predicted | Confidence | "
            "Tier | Correct |",
            "| --- | --- | --- | --- | --- | ---: | --- | --- |",
        ]
    )
    lines.extend(_table_rows(report["groups"]["misclassified_code_injection_cases"]))
    lines.extend(
        [
            "",
            "## Known normal traffic",
            "",
            "| Case | Exact query | Predicted | Confidence | Tier | Correct |",
            "| --- | --- | --- | ---: | --- | --- |",
        ]
    )
    for row in report["groups"]["known_normal_traffic"]:
        lines.append(
            f"| {row['case_id']} | {row['payload']} | {row['predicted_label']} | "
            f"{row['confidence']} | {row['confidence_level']} | "
            f"{row['classification_correct']} |"
        )
    lines.extend(
        [
            "",
            "## Normal false positives",
            "",
            "| Case | Exact query | Predicted | Confidence | Tier |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for row in report["groups"]["normal_false_positives"]:
        lines.append(
            f"| {row['case_id']} | {row['payload']} | {row['predicted_label']} | "
            f"{row['confidence']} | {row['confidence_level']} |"
        )
    return "\n".join(lines) + "\n"


def write_report(
    report: dict[str, Any], *, json_path: Path, markdown_path: Path
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(to_markdown(report), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Combine preserved and follow-up Search Records results."
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--code-catalog", type=Path, required=True)
    parser.add_argument("--normal-catalog", type=Path, required=True)
    parser.add_argument("--code-report", type=Path, required=True)
    parser.add_argument("--normal-report", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(
        baseline_path=args.baseline,
        code_catalog_path=args.code_catalog,
        normal_catalog_path=args.normal_catalog,
        code_report_path=args.code_report,
        normal_report_path=args.normal_report,
    )
    write_report(report, json_path=args.output_json, markdown_path=args.output_markdown)
    code = report["summary"]["code_expansion"]
    normal = report["summary"]["normal_traffic"]
    print(
        f"code={code['new_correctly_classified']}/{code['new_variations_tested']} "
        f"normal={normal['correctly_classified_normal']}/{normal['tested']} "
        f"false_positives={normal['false_positive_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
