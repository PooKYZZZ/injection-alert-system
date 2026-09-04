"""Build a deterministic, metadata-rich panel attack catalogue.

The checked-in catalogue contains case metadata and references to the existing
approved fixture file.  Expanded requests are written only when the caller
explicitly supplies an output path; generated request text is intended for
local offline scoring and is not a production or public-network runner.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = REPO_ROOT / "scripts" / "fixtures" / "panel_attack_catalog.json"
DEFAULT_FIXTURES = REPO_ROOT / "scripts" / "fixtures" / "attack_dataset_samples.json"
ALLOWED_LABELS = {"SQL Injection", "Code Injection", "Other Attacks", "Normal"}
ALLOWED_FAMILIES = {"normal", "sql_injection", "code_injection", "other_attacks"}
ALLOWED_HTTP_METHODS = {"GET", "POST"}
ALLOWED_VARIANTS = {
    "identity",
    "append_benign_query",
    "query_case",
    "encoded_spaces",
    "lower_header_names",
    "json_key_order",
    "crlf",
}


@dataclass(frozen=True, slots=True)
class CatalogCase:
    case_id: str
    case_version: int
    source_fixture_id: str
    family: str
    variant: str
    description: str
    expected_label: str
    ground_truth_status: str
    expected_waf: str
    replay_policy: str
    selection_tags: tuple[str, ...]


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read JSON file: {path}") from exc


def load_fixture_requests(path: Path = DEFAULT_FIXTURES) -> dict[str, str]:
    payload = _load_json(path)
    if not isinstance(payload, list):
        raise ValueError(f"fixture file must contain a JSON array: {path}")

    fixtures: dict[str, str] = {}
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"fixture row {index} is not an object")
        fixture_id = item.get("id")
        request = item.get("combined_payload")
        if not isinstance(fixture_id, str) or not fixture_id.strip():
            raise ValueError(f"fixture row {index} is missing id")
        if not isinstance(request, str) or not request.strip():
            raise ValueError(f"fixture {fixture_id!r} is missing combined_payload")
        if fixture_id in fixtures:
            raise ValueError(f"duplicate fixture id: {fixture_id}")
        fixtures[fixture_id] = request
    return fixtures


def load_catalog(path: Path = DEFAULT_CATALOG) -> tuple[str, list[CatalogCase]]:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"catalog must contain a JSON object: {path}")

    catalog_version = payload.get("catalog_version")
    raw_cases = payload.get("cases")
    if not isinstance(catalog_version, str) or not catalog_version.strip():
        raise ValueError("catalog_version must be a non-empty string")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("catalog cases must be a non-empty array")

    cases: list[CatalogCase] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_cases, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"catalog case {index} is not an object")
        required_strings = (
            "case_id",
            "source_fixture_id",
            "family",
            "variant",
            "description",
            "expected_label",
            "ground_truth_status",
            "expected_waf",
            "replay_policy",
        )
        if any(
            not isinstance(item.get(key), str) or not item[key].strip()
            for key in required_strings
        ):
            raise ValueError(f"catalog case {index} has missing string metadata")

        case_id = item["case_id"].strip()
        if case_id in seen_ids:
            raise ValueError(f"duplicate case id: {case_id}")
        seen_ids.add(case_id)

        case_version = item.get("case_version", 1)
        if not isinstance(case_version, int) or case_version < 1:
            raise ValueError(f"catalog case {case_id} has invalid case_version")
        if item["family"] not in ALLOWED_FAMILIES:
            raise ValueError(f"catalog case {case_id} has unsupported family")
        if item["variant"] not in ALLOWED_VARIANTS:
            raise ValueError(f"catalog case {case_id} has unsupported variant")
        if item["expected_label"] not in ALLOWED_LABELS:
            raise ValueError(f"catalog case {case_id} has unsupported expected label")

        tags = item.get("selection_tags", [])
        if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
            raise ValueError(f"catalog case {case_id} has invalid selection_tags")

        cases.append(
            CatalogCase(
                case_id=case_id,
                case_version=case_version,
                source_fixture_id=item["source_fixture_id"].strip(),
                family=item["family"].strip(),
                variant=item["variant"].strip(),
                description=item["description"].strip(),
                expected_label=item["expected_label"].strip(),
                ground_truth_status=item["ground_truth_status"].strip(),
                expected_waf=item["expected_waf"].strip(),
                replay_policy=item["replay_policy"].strip(),
                selection_tags=tuple(tags),
            )
        )
    return catalog_version.strip(), cases


def _split_request(request: str) -> tuple[str, str, str, str]:
    newline = "\r\n" if "\r\n" in request else "\n"
    separator = newline + newline
    if separator in request:
        head, body = request.split(separator, 1)
        return head, separator, body, newline
    return request, "", "", newline


def _request_line_parts(request_line: str) -> tuple[str, str, str]:
    parts = request_line.split(" ", 2)
    if len(parts) != 3 or not all(parts):
        raise ValueError("fixture request has an invalid request line")
    return parts[0], parts[1], parts[2]


def _rebuild_request(
    head_lines: list[str],
    separator: str,
    body: str,
    *,
    newline: str,
) -> str:
    return newline.join(head_lines) + (separator + body if separator else "")


def _with_request_target(request: str, target: str) -> str:
    head, separator, body, newline = _split_request(request)
    lines = head.splitlines()
    method, _old_target, protocol = _request_line_parts(lines[0])
    lines[0] = f"{method} {target} {protocol}"
    return _rebuild_request(lines, separator, body, newline=newline)


def _append_query_parameter(request: str, value: str) -> str:
    head, separator, body, newline = _split_request(request)
    lines = head.splitlines()
    _method, target, _protocol = _request_line_parts(lines[0])
    joiner = "&" if "?" in target else "?"
    return _with_request_target(request, f"{target}{joiner}panel_case={value}")


def _lower_header_names(request: str) -> str:
    head, separator, body, newline = _split_request(request)
    lines = head.splitlines()
    for index in range(1, len(lines)):
        if ":" not in lines[index]:
            continue
        name, value = lines[index].split(":", 1)
        lines[index] = f"{name.lower()}:{value}"
    return _rebuild_request(lines, separator, body, newline=newline)


def _json_key_order(request: str) -> str:
    head, separator, body, newline = _split_request(request)
    if not separator or not body:
        raise ValueError("json_key_order requires a request body")
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ValueError("json_key_order requires a JSON request body") from exc
    if not isinstance(parsed, dict):
        raise ValueError("json_key_order requires a JSON object body")

    reordered = json.dumps(
        parsed, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    lines = head.splitlines()
    for index, line in enumerate(lines):
        if line.lower().startswith("content-length:"):
            lines[index] = f"Content-Length: {len(reordered.encode('utf-8'))}"
    return _rebuild_request(lines, separator, reordered, newline=newline)


def apply_variant(request: str, variant: str) -> str:
    """Apply one deterministic, semantics-limited catalogue transformation."""

    if variant == "identity":
        return request
    if variant == "append_benign_query":
        return _append_query_parameter(request, "catalog")
    if variant == "query_case":
        head, separator, body, newline = _split_request(request)
        lines = head.splitlines()
        method, target, protocol = _request_line_parts(lines[0])
        if "?" in target:
            path, query = target.split("?", 1)
            target = f"{path}?{query.swapcase()}"
        else:
            body = body.swapcase()
        lines[0] = f"{method} {target} {protocol}"
        return _rebuild_request(lines, separator, body, newline=newline)
    if variant == "encoded_spaces":
        return request.replace("%20", "+")
    if variant == "lower_header_names":
        return _lower_header_names(request)
    if variant == "json_key_order":
        return _json_key_order(request)
    if variant == "crlf":
        return request.replace("\r\n", "\n").replace("\n", "\r\n")
    raise ValueError(f"unsupported catalogue variant: {variant}")


def expand_catalog(
    *,
    catalog_path: Path = DEFAULT_CATALOG,
    fixtures_path: Path = DEFAULT_FIXTURES,
) -> list[dict[str, Any]]:
    catalog_version, cases = load_catalog(catalog_path)
    fixtures = load_fixture_requests(fixtures_path)
    expanded: list[dict[str, Any]] = []
    for case in cases:
        if case.source_fixture_id not in fixtures:
            raise ValueError(
                f"catalog case {case.case_id} references unknown fixture "
                f"{case.source_fixture_id!r}"
            )
        request = apply_variant(fixtures[case.source_fixture_id], case.variant)
        method = request.split(None, 1)[0].upper()
        if method not in ALLOWED_HTTP_METHODS:
            raise ValueError(
                f"catalog case {case.case_id} uses disallowed HTTP method: {method}"
            )
        expanded.append(
            {
                "catalog_version": catalog_version,
                "case_id": case.case_id,
                "case_version": case.case_version,
                "source_fixture_id": case.source_fixture_id,
                "family": case.family,
                "variant": case.variant,
                "description": case.description,
                "expected_label": case.expected_label,
                "ground_truth_status": case.ground_truth_status,
                "expected_waf": case.expected_waf,
                "replay_policy": case.replay_policy,
                "selection_tags": list(case.selection_tags),
                "input_sha256": hashlib.sha256(request.encode("utf-8")).hexdigest(),
                "http_request": request,
            }
        )
    return expanded


def render_markdown(catalog_path: Path = DEFAULT_CATALOG) -> str:
    catalog_version, cases = load_catalog(catalog_path)
    lines = [
        "# Panel Attack Catalogue",
        "",
        f"Catalogue version: `{catalog_version}`",
        "",
        "This is a deterministic, local-only catalogue for panel demonstrations.",
        (
            "The expected label is ground truth only where the case says "
            "`approved_fixture`;"
        ),
        "proposed variants require analyst review before acceptance.",
        "",
        "Confidence is measured from the unchanged model output. A case ID or tag does",
        "not force LOW, MEDIUM, HIGH, or CRITICAL confidence.",
        "",
        (
            "| Case | Family | Variant | Expected label | Ground truth | "
            "WAF expectation | Replay policy | Tags |"
        ),
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for case in cases:
        tags = ", ".join(case.selection_tags)
        lines.append(
            f"| `{case.case_id}` | {case.family} | `{case.variant}` | "
            f"{case.expected_label} | {case.ground_truth_status} | "
            f"{case.expected_waf} | {case.replay_policy} | {tags} |"
        )
    lines.extend(
        [
            "",
            "## Reproducible commands",
            "",
            "From the repository root:",
            "",
            "```powershell",
            ".venv\\Scripts\\python.exe -m scripts.panel_attack_catalog `",
            "  --output output\\attack-tests\\panel-cases.jsonl",
            "",
            ".venv\\Scripts\\python.exe -m scripts.attack_dataset_tester `",
            "  --dataset output\\attack-tests\\panel-cases.jsonl `",
            "  --include-normal `",
            "  --limit 0 `",
            "  --seed 20260902 `",
            "  --pause-ms 100 `",
            "  --output-csv output\\attack-tests\\panel-results.csv `",
            "  --output-jsonl output\\attack-tests\\panel-results.jsonl",
            "```",
            "",
            "The tester defaults to the internal local `/api/predict` route. Do not",
            "replace it with a public hostname or an unbounded loop.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_output(rows: list[dict[str, Any]], output: Path, output_format: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "markdown":
        output.write_text(render_markdown(), encoding="utf-8")
        return
    if output_format == "jsonl":
        with output.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        return
    if output_format == "csv":
        fieldnames = list(rows[0].keys())
        with output.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                csv_row = dict(row)
                csv_row["selection_tags"] = json.dumps(row["selection_tags"])
                writer.writerow(csv_row)
        return
    raise ValueError(f"unsupported output format: {output_format}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--format",
        choices=("jsonl", "csv", "markdown"),
        default="jsonl",
        help="Output format. Markdown uses the catalogue metadata only.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.format == "markdown":
            write_output([], args.output, args.format)
        else:
            write_output(
                expand_catalog(catalog_path=args.catalog, fixtures_path=args.fixtures),
                args.output,
                args.format,
            )
    except (OSError, ValueError) as exc:
        print(f"Failed to build panel catalogue: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
