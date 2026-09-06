"""Preserve the Search Records baseline and build follow-up catalogues.

The follow-up scope is deliberately limited to the local demo portal's
``GET /records/search?query=...`` route.  Code-injection variants remain
inert strings: they use side-effect-free expressions or output-only markers
and are never sent to an execution endpoint.  Benign queries are drawn from
the demo portal's record vocabulary and realistic search tasks.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote_plus

from scripts.search_records_attack_catalog import (
    EXPECTED_LABELS,
    METHOD,
    QUERY_PARAMETER,
    ROUTE_PATH,
    load_catalog,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_CATALOG = REPO_ROOT / "scripts" / "fixtures" / "search_records_attack_catalog.json"
KNOWN_CODE_SEEDS = (
    "SR-CODE-021",
    "SR-CODE-022",
    "SR-CODE-023",
    "SR-CODE-024",
    "SR-CODE-032",
    "SR-CODE-034",
    "SR-CODE-035",
    "SR-CODE-036",
    "SR-CODE-037",
    "SR-CODE-039",
    "SR-CODE-044",
    "SR-CODE-047",
)
CODE_CATALOG_VERSION = "search-records-code-expansion-v1"
NORMAL_CATALOG_VERSION = "search-records-normal-baseline-v1"
FOLLOWUP_FAMILIES = ("code_injection", "normal_traffic")
SAFE_NORMAL_QUERY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .-]*$")


@dataclass(frozen=True, slots=True)
class CodeSeed:
    case_id: str
    payload: str
    description: str


NORMAL_QUERIES = (
    ("LND-2026-0001", "Record number lookup for the first sample deed"),
    ("LND-2026-0002", "Record number lookup for the second sample deed"),
    ("LND-2026-0003", "Record number lookup for the third sample deed"),
    ("LND-2026-0004", "Record number lookup for the fourth sample deed"),
    ("LND-2026-0005", "Lookup for a later sample record number"),
    ("LND-2026-0006", "Lookup for another sample record number"),
    ("LND-2026-0007", "Lookup for an additional sample record number"),
    ("LND-2026-0008", "Lookup for an additional registry number"),
    ("LND-2026-0009", "Lookup for a sample cadastral number"),
    ("LND-2026-0010", "Lookup for a sample deed index number"),
    ("Maria Santos", "Search by the first sample owner name"),
    ("Daniel Reyes", "Search by the second sample owner name"),
    ("Elena Cruz", "Search by the third sample owner name"),
    ("Ramon Garcia", "Search by the fourth sample owner name"),
    ("Maria", "Search by an owner first name"),
    ("Daniel", "Search by another owner first name"),
    ("Elena", "Search by another owner first name"),
    ("Ramon", "Search by another owner first name"),
    ("North District", "Search the North District registry area"),
    ("North Branch", "Search the North Branch location"),
    ("Crest Branch", "Search the Crest Branch location"),
    ("South Branch", "Search the South Branch location"),
    ("Registry Sector", "Search by the registry sector phrase"),
    ("Malibu Point", "Search by the sample Malibu location"),
    ("Mountain Drive", "Search by the sample Mountain Drive location"),
    ("Residential", "Search for residential classifications"),
    ("Commercial", "Search for commercial classifications"),
    ("Agricultural", "Search for agricultural classifications"),
    ("Mixed Use", "Search for mixed use classifications"),
    ("Historical Preserve", "Search for historical preserve records"),
    ("Cultivation Yard", "Search by the sample property type"),
    ("Property Partitioning", "Search for a property partitioning service"),
    ("Title Deed Transfer", "Search for a title deed transfer service"),
    ("Active Registered", "Search for active registered status text"),
    ("Collateralized", "Search for collateralized record status"),
    ("Public land records", "A normal user search for public land records"),
    ("Search land records", "A normal user search task phrase"),
    ("Property title", "A normal title lookup phrase"),
    ("Record lookup", "A normal record lookup phrase"),
    ("Parcel boundary", "A normal parcel-boundary information phrase"),
    ("Survey date", "A normal survey-date search phrase"),
    ("Owner name", "A normal owner-name search phrase"),
    ("Record number", "A normal record-number search phrase"),
    ("North District registry", "A normal registry-area phrase"),
    ("Residential property", "A normal residential-property phrase"),
    ("Commercial property", "A normal commercial-property phrase"),
    ("Agricultural land", "A normal agricultural-land phrase"),
    ("Certified copy", "A normal certified-copy information phrase"),
    ("Deed transfer processing", "A normal deed-transfer service phrase"),
    ("Sample cadastral index", "A normal cadastral-index phrase"),
)


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read JSON file: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _write_object(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _route() -> dict[str, str]:
    return {"method": METHOD, "path": ROUTE_PATH, "query_parameter": QUERY_PARAMETER}


def _wire_query(payload: str) -> str:
    return quote_plus(payload, safe="")


def _profile(payload: str) -> str:
    if any(token in payload for token in ("echo", "printf", "$", "`")):
        return "shell"
    if any(token in payload for token in ("__import__", "eval(")):
        return "python"
    if any(token in payload for token in ("function", "return")):
        return "javascript"
    return "template"


def _toggle_first_word(payload: str, words: tuple[str, ...]) -> str:
    for word in words:
        match = re.search(re.escape(word), payload, flags=re.IGNORECASE)
        if match:
            current = match.group(0)
            return (
                payload[: match.start()]
                + current.swapcase()
                + payload[match.end() :]
            )
    return payload.swapcase()


def _mutate_whitespace(payload: str, profile: str) -> str:
    if profile == "shell":
        if " " in payload:
            return payload.replace(" ", "${IFS}", 1)
        return payload + "${IFS}"
    if profile == "python":
        if "(" in payload:
            return payload.replace("(", " (", 1)
        return payload + " "
    if profile == "javascript":
        return payload.replace("return", "return ", 1)
    return payload.replace("*", " * ", 1) if "*" in payload else payload + " "


def _mutate_case(payload: str, profile: str) -> str:
    if profile == "shell":
        return _toggle_first_word(payload, ("echo", "printf", "IFS"))
    if profile == "python":
        return _toggle_first_word(payload, ("__import__", "import", "eval", "sqrt"))
    if profile == "javascript":
        return _toggle_first_word(payload, ("function", "return"))
    return payload.swapcase()


def _mutate_wrapper(payload: str, profile: str) -> str:
    if profile == "shell":
        return f"( {payload} )"
    if profile == "javascript":
        return f"(({payload}))"
    return f"({payload})"


def _mutate_quoted_arguments(payload: str, profile: str) -> str:
    if profile == "shell":
        if "echo CYBERTRACE_TEST" in payload:
            return payload.replace("echo CYBERTRACE_TEST", "echo 'CYBERTRACE_TEST'", 1)
        if "printf CYBERTRACE_TEST" in payload:
            return payload.replace(
                "printf CYBERTRACE_TEST", "printf '%s' CYBERTRACE_TEST", 1
            )
        return f"{payload} 'CYBERTRACE_TEST'"
    if profile == "python" and "'" in payload:
        return payload.replace("'", '"')
    if profile == "javascript" and "return 1" in payload:
        return payload.replace("return 1", "return 'CYBERTRACE_TEST'", 1)
    return f"{payload} + 0"


def _mutate_separator(payload: str, profile: str) -> str:
    if profile == "shell":
        return f"{payload}; printf CYBERTRACE_TEST"
    if profile == "javascript":
        return f"{payload}; 2 + 2"
    return f"{payload}; 2+2"


def _mutate_alternate_delimiter(payload: str, profile: str) -> str:
    if profile == "shell":
        return f"{payload} && printf CYBERTRACE_TEST"
    if profile == "javascript":
        return f"[{payload}]"
    return f"[{payload}]"


def _mutate_comment(payload: str, profile: str, serial: int) -> str:
    if profile in {"shell", "python"}:
        return f"{payload} # CYBERTRACE_EXP_{serial:03d}"
    if profile == "javascript":
        return f"{payload} // CYBERTRACE_EXP_{serial:03d}"
    return f"{payload} /*CYBERTRACE_EXP_{serial:03d}*/"


def _mutate_encoded_spacing(payload: str, profile: str) -> str:
    if " " in payload:
        return payload.replace(" ", "%20", 1)
    return payload + ("%0a" if profile != "shell" else "%09")


def _mutate_argument_form(payload: str, profile: str) -> str:
    replacements = (
        ("sqrt(4)", "sqrt(2+2)"),
        ("eval('1+1')", 'eval("2-1")'),
        ("eval(\"1+1\")", "eval('2-1')"),
        ("return 1", "return (1)"),
        ("7*7", "7 * 7"),
        ("echo CYBERTRACE_TEST", "printf '%s' CYBERTRACE_TEST"),
        ("printf CYBERTRACE_TEST", "printf '%s' CYBERTRACE_TEST"),
    )
    for old, new in replacements:
        if old in payload:
            return payload.replace(old, new, 1)
    if profile == "shell":
        return f"{payload} CYBERTRACE_TEST"
    return f"{payload} + (0)"


def _mutate_call_wrapper(payload: str, profile: str, serial: int) -> str:
    if profile == "shell":
        return f"$(printf CYBERTRACE_EXP_{serial:03d})"
    if profile == "python":
        return "getattr(__import__('math'),'sqrt')(2+2)"
    if profile == "javascript":
        return "(()=>{return 1})()"
    return "{{7 * 7}}"


MUTATIONS: tuple[tuple[str, Callable[..., str]], ...] = (
    ("whitespace_expansion", _mutate_whitespace),
    ("case_variation", _mutate_case),
    ("wrapper_variation", _mutate_wrapper),
    ("quoted_argument_variation", _mutate_quoted_arguments),
    ("separator_variation", _mutate_separator),
    ("alternate_delimiter_variation", _mutate_alternate_delimiter),
    ("comment_variation", _mutate_comment),
    ("encoded_spacing_variation", _mutate_encoded_spacing),
    ("argument_form_variation", _mutate_argument_form),
)


def _append_disambiguator(payload: str, profile: str, serial: int) -> str:
    if profile in {"shell", "python"}:
        return f"{payload} # CYBERTRACE_EXP_{serial:03d}"
    return f"{payload} /*CYBERTRACE_EXP_{serial:03d}*/"


def _case(
    *,
    case_id: str,
    seed_id: str,
    source_seed_payload: str,
    family: str,
    expected_label: str,
    variant: str,
    mutation: str,
    payload: str,
    description: str,
    status: str,
    tags: list[str],
    expected_waf: str,
    is_seed: bool,
) -> dict[str, Any]:
    wire_query = _wire_query(payload)
    return {
        "case_id": case_id,
        "case_version": 1,
        "seed_id": seed_id,
        "source_seed_payload": source_seed_payload,
        "family": family,
        "method": METHOD,
        "route_path": ROUTE_PATH,
        "query_parameter": QUERY_PARAMETER,
        "expected_label": expected_label,
        "variant": variant,
        "mutation": mutation,
        "payload": payload,
        "wire_query": wire_query,
        "request_uri": f"{ROUTE_PATH}?{QUERY_PARAMETER}={wire_query}",
        "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "wire_sha256": hashlib.sha256(wire_query.encode("utf-8")).hexdigest(),
        "description": description,
        "ground_truth_status": status,
        "replay_policy": "local_search_records_only",
        "expected_waf": expected_waf,
        "selection_tags": tags,
        "is_seed": is_seed,
    }


def _catalog(
    *,
    catalog_version: str,
    cases: list[dict[str, Any]],
    maximum_cases: int,
    description: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "catalog_version": catalog_version,
        "scope": description,
        "route": _route(),
        "safety": {
            "non_destructive_inputs": True,
            "no_execution_endpoint": True,
            "no_public_hostnames": True,
            "maximum_cases": maximum_cases,
        },
        "confidence_note": (
            "Confidence is observed from the unchanged model. No threshold or "
            "action mapping is changed to produce a desired result."
        ),
        "expected_action_policy": (
            "Normal=ALLOWED; SQL Injection/Code Injection LOW=ALLOWED, "
            "MEDIUM=THROTTLED, HIGH/CRITICAL=BLOCKED; Other Attacks=None"
        ),
        "cases": cases,
    }


def _known_code_seed_rows(path: Path) -> tuple[CodeSeed, ...]:
    payload = _read_object(path)
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("known code seed fixture must contain a cases array")
    rows: list[CodeSeed] = []
    seen: set[str] = set()
    for row in raw_cases:
        if not isinstance(row, dict):
            raise ValueError("known code seed entry must be an object")
        case = row.get("case") if isinstance(row.get("case"), dict) else row
        result = row.get("observed_result", {})
        if not isinstance(case, dict) or not isinstance(result, dict):
            raise ValueError("known code seed entry has invalid case/result")
        case_id = str(case.get("case_id") or "")
        if case_id not in KNOWN_CODE_SEEDS or case_id in seen:
            raise ValueError(f"unexpected or duplicate known code seed: {case_id}")
        if case.get("expected_label") != "Code Injection":
            raise ValueError(f"known code seed has wrong expected label: {case_id}")
        if (
            result.get("predicted_label") != "Code Injection"
            or result.get("classification_correct") != "True"
        ):
            raise ValueError(f"known code seed is not a confirmed positive: {case_id}")
        payload_text = str(case.get("payload") or "")
        if not payload_text:
            raise ValueError(f"known code seed has no payload: {case_id}")
        rows.append(
            CodeSeed(
                case_id=case_id,
                payload=payload_text,
                description=str(case.get("description") or "Confirmed code seed"),
            )
        )
        seen.add(case_id)
    if tuple(row.case_id for row in rows) != KNOWN_CODE_SEEDS:
        raise ValueError(
            "known code seed fixture must preserve the canonical seed order"
        )
    return tuple(rows)


def build_code_expansion_catalog(
    *,
    known_code_path: Path,
    base_catalog_path: Path = BASE_CATALOG,
) -> dict[str, Any]:
    seeds = _known_code_seed_rows(known_code_path)
    base_catalog = load_catalog(base_catalog_path)
    existing_payloads = {str(case["payload"]) for case in base_catalog["cases"]}
    existing_wires = {str(case["wire_query"]) for case in base_catalog["cases"]}
    cases: list[dict[str, Any]] = []
    for seed_index, seed in enumerate(seeds):
        profile = _profile(seed.payload)
        mutation_rows = list(MUTATIONS[:8])
        if seed_index < 4:
            mutation_rows.append(MUTATIONS[8])
        for mutation_name, mutation in mutation_rows:
            serial = len(cases) + 1
            if mutation_name == "comment_variation":
                candidate = mutation(seed.payload, profile, serial)
            else:
                candidate = mutation(seed.payload, profile)
            while (
                candidate in existing_payloads
                or _wire_query(candidate) in existing_wires
            ):
                candidate = _append_disambiguator(candidate, profile, serial)
            existing_payloads.add(candidate)
            existing_wires.add(_wire_query(candidate))
            cases.append(
                _case(
                    case_id=f"SR-CODE-EXP-{serial:03d}",
                    seed_id=seed.case_id,
                    source_seed_payload=seed.payload,
                    family="code_injection",
                    expected_label=EXPECTED_LABELS["code_injection"],
                    variant="expansion",
                    mutation=mutation_name,
                    payload=candidate,
                    description=(
                        f"{seed.description}; derived from confirmed seed "
                        f"{seed.case_id}; applied {mutation_name.replace('_', ' ')}"
                    ),
                    status="proposed_code_expansion",
                    tags=[
                        "search_records_only",
                        "local_demo_only",
                        "non_destructive",
                        "derived_from_confirmed_code_seed",
                        "code_expansion_candidate",
                        f"mutation_{mutation_name}",
                    ],
                    expected_waf="RECORD_OR_BLOCK",
                    is_seed=False,
                )
            )
    if len(cases) != 100:
        raise AssertionError(
            f"expected 100 code expansion cases, generated {len(cases)}"
        )
    return _catalog(
        catalog_version=CODE_CATALOG_VERSION,
        cases=cases,
        maximum_cases=100,
        description=(
            "local demo portal only; 100 inert code-injection variations derived "
            "from 12 confirmed Search Records code seeds"
        ),
    )


def build_normal_catalog() -> dict[str, Any]:
    if len(NORMAL_QUERIES) != 50:
        raise AssertionError(f"expected 50 normal queries, found {len(NORMAL_QUERIES)}")
    cases: list[dict[str, Any]] = []
    for index, (payload, description) in enumerate(NORMAL_QUERIES, start=1):
        if not SAFE_NORMAL_QUERY.fullmatch(payload):
            raise ValueError(f"normal query contains non-benign punctuation: {payload}")
        cases.append(
            _case(
                case_id=f"SR-NORMAL-{index:03d}",
                seed_id=f"NORMAL-BASELINE-{index:03d}",
                source_seed_payload=payload,
                family="normal_traffic",
                expected_label="Normal",
                variant="benign",
                mutation="realistic_search_query",
                payload=payload,
                description=description,
                status="benign_reference",
                tags=[
                    "search_records_only",
                    "local_demo_only",
                    "non_attack_input",
                    "normal_traffic_reference",
                ],
                expected_waf="ALLOW_EXPECTED",
                is_seed=True,
            )
        )
    return _catalog(
        catalog_version=NORMAL_CATALOG_VERSION,
        cases=cases,
        maximum_cases=50,
        description=(
            "local demo portal only; 50 realistic benign Search Records queries"
        ),
    )


def _catalog_case_map(path: Path) -> dict[str, dict[str, Any]]:
    catalog = load_catalog(path)
    return {str(case["case_id"]): case for case in catalog["cases"]}


def _csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    except OSError as exc:
        raise ValueError(f"could not read CSV report: {path}") from exc


def _preserved_entry(
    row: dict[str, str], definition: dict[str, Any]
) -> dict[str, Any]:
    return {
        "case": definition,
        "observed_result": row,
    }


def build_baseline_snapshot(
    *,
    full_report_path: Path,
    seed_report_path: Path,
    base_catalog_path: Path = BASE_CATALOG,
    seed_catalog_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    full_rows = _csv_rows(full_report_path)
    seed_rows = _csv_rows(seed_report_path)
    if len(full_rows) != 150:
        raise ValueError(f"full report must contain 150 rows, found {len(full_rows)}")
    if len(seed_rows) != 30:
        raise ValueError(f"seed report must contain 30 rows, found {len(seed_rows)}")
    full_definitions = _catalog_case_map(base_catalog_path)
    seed_definitions = _catalog_case_map(seed_catalog_path)

    def entries(rows: list[dict[str, str]], definitions: dict[str, dict[str, Any]]):
        result: list[dict[str, Any]] = []
        for row in rows:
            case_id = str(row.get("case_id") or "")
            if case_id not in definitions:
                raise ValueError(f"report case is missing from its catalog: {case_id}")
            result.append(_preserved_entry(row, definitions[case_id]))
        return result

    all_full = entries(full_rows, full_definitions)
    all_seeds = entries(seed_rows, seed_definitions)
    sql = [entry for entry in all_full if entry["case"]["family"] == "sql_injection"]
    code = [
        entry for entry in all_full if entry["case"]["family"] == "code_injection"
    ]
    code_positive = [
        entry
        for entry in code
        if entry["observed_result"].get("classification_correct") == "True"
    ]
    if len(sql) != 50:
        raise ValueError(f"expected 50 SQL baseline rows, found {len(sql)}")
    if len(code) != 50:
        raise ValueError(f"expected 50 code baseline rows, found {len(code)}")
    if len(code_positive) != 12:
        raise ValueError(f"expected 12 confirmed code rows, found {len(code_positive)}")
    if [entry["case"]["case_id"] for entry in code_positive] != list(
        KNOWN_CODE_SEEDS
    ):
        raise ValueError("confirmed code rows do not match the preserved seed IDs")

    source_run_id = str(full_rows[0].get("run_id") or "")
    snapshot = {
        "schema_version": 1,
        "fixture_type": "search_records_followup_baseline",
        "source_run_id": source_run_id,
        "route": _route(),
        "source_files": {
            "full_report": str(full_report_path),
            "full_report_sha256": _sha256_file(full_report_path),
            "seed_report": str(seed_report_path),
            "seed_report_sha256": _sha256_file(seed_report_path),
            "full_catalog": str(base_catalog_path),
            "seed_catalog": str(seed_catalog_path),
        },
        "preservation_note": (
            "This snapshot preserves the original 50 SQL cases and results, "
            "the original 30 seed results, and the 12 exact code-positive cases "
            "before follow-up generation. Do not overwrite it during expansion."
        ),
        "original_sql_injection_cases": sql,
        "original_code_injection_cases": code,
        "original_code_injection_positive_cases": code_positive,
        "original_seed_cases": all_seeds,
    }
    known_code = {
        "schema_version": 1,
        "fixture_type": "confirmed_code_injection_seeds",
        "source_run_id": source_run_id,
        "route": _route(),
        "preservation_note": (
            "These 12 cases were exact Code Injection label matches in the "
            "preserved source run. They are immutable seed references for the "
            "100-case expansion catalog."
        ),
        "cases": code_positive,
    }
    return snapshot, known_code


def validate_followup_catalog(path: Path) -> dict[str, Any]:
    payload = _read_object(path)
    if payload.get("route") != _route():
        raise ValueError("follow-up catalog must target GET /records/search?query=...")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("follow-up catalog must contain a non-empty cases array")
    seen_ids: set[str] = set()
    seen_wires: set[str] = set()
    for index, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise ValueError(f"follow-up case {index} is not an object")
        for key in (
            "case_id",
            "family",
            "expected_label",
            "payload",
            "wire_query",
            "request_uri",
        ):
            if not isinstance(case.get(key), str) or not case[key]:
                raise ValueError(f"follow-up case {index} is missing {key}")
        case_id = case["case_id"]
        if case_id in seen_ids:
            raise ValueError(f"duplicate follow-up case ID: {case_id}")
        if case["family"] not in FOLLOWUP_FAMILIES:
            raise ValueError(f"unsupported follow-up family: {case['family']}")
        expected_label = (
            "Normal" if case["family"] == "normal_traffic" else "Code Injection"
        )
        if case["expected_label"] != expected_label:
            raise ValueError(f"expected label does not match family: {case_id}")
        if case.get("method") != METHOD or case.get("route_path") != ROUTE_PATH:
            raise ValueError(f"case is outside Search Records: {case_id}")
        expected_uri = f"{ROUTE_PATH}?{QUERY_PARAMETER}={case['wire_query']}"
        if case["request_uri"] != expected_uri:
            raise ValueError(f"request URI is not canonical: {case_id}")
        if case["wire_query"] != _wire_query(case["payload"]):
            raise ValueError(f"wire query does not match payload: {case_id}")
        payload_hash = hashlib.sha256(case["payload"].encode()).hexdigest()
        if case.get("payload_sha256") != payload_hash:
            raise ValueError(f"payload hash does not match payload: {case_id}")
        wire_hash = hashlib.sha256(case["wire_query"].encode()).hexdigest()
        if case.get("wire_sha256") != wire_hash:
            raise ValueError(f"wire hash does not match wire query: {case_id}")
        if case["wire_query"] in seen_wires:
            raise ValueError(f"duplicate follow-up wire query: {case_id}")
        seen_ids.add(case_id)
        seen_wires.add(case["wire_query"])
    maximum = int(payload.get("safety", {}).get("maximum_cases", 0))
    if len(cases) > maximum or maximum <= 0:
        raise ValueError("follow-up catalog exceeds its declared case limit")
    return payload


def write_catalog(path: Path, catalog: dict[str, Any]) -> None:
    _write_object(path, catalog)
    validate_followup_catalog(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Preserve or generate bounded Search Records follow-up catalogs."
    )
    parser.add_argument(
        "--mode", choices=("baseline", "code-expansion", "normal"), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--known-code-output", type=Path)
    parser.add_argument("--known-code-source", type=Path)
    parser.add_argument("--base-catalog", type=Path, default=BASE_CATALOG)
    parser.add_argument("--seed-catalog", type=Path)
    parser.add_argument("--full-report", type=Path)
    parser.add_argument("--seed-report", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "baseline":
        missing = [
            name
            for name, value in (
                ("--full-report", args.full_report),
                ("--seed-report", args.seed_report),
                ("--seed-catalog", args.seed_catalog),
                ("--known-code-output", args.known_code_output),
            )
            if value is None
        ]
        if missing:
            raise SystemExit("baseline mode requires " + ", ".join(missing))
        snapshot, known_code = build_baseline_snapshot(
            full_report_path=args.full_report,
            seed_report_path=args.seed_report,
            base_catalog_path=args.base_catalog,
            seed_catalog_path=args.seed_catalog,
        )
        _write_object(args.output, snapshot)
        _write_object(args.known_code_output, known_code)
        print("baseline_sql=50 baseline_seeds=30 confirmed_code=12")
        return 0

    if args.mode == "code-expansion":
        known_code_source = args.known_code_source or (
            REPO_ROOT / "scripts" / "fixtures" / "search_records_known_code_seeds.json"
        )
        catalog = build_code_expansion_catalog(
            known_code_path=known_code_source,
            base_catalog_path=args.base_catalog,
        )
    else:
        catalog = build_normal_catalog()
    write_catalog(args.output, catalog)
    print(
        f"catalog_version={catalog['catalog_version']} "
        f"cases={len(catalog['cases'])} "
        f"family={catalog['cases'][0]['family']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
