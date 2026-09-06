"""Build a deterministic, Search Records-only attack test catalogue.

This module keeps the test inputs local to the demo portal's
/records/search query parameter. The generated cases are deliberately
non-destructive: command-style examples use inert output/arithmetic
expressions and are never sent to an execution endpoint.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote, quote_plus

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    REPO_ROOT / "scripts" / "fixtures" / "search_records_attack_catalog.json"
)

ROUTE_PATH = "/records/search"
METHOD = "GET"
QUERY_PARAMETER = "query"
CATALOG_VERSION = "search-records-panel-v2"
SEED_CATALOG_VERSION = f"{CATALOG_VERSION}-seeds"
FAMILIES = ("sql_injection", "code_injection", "general_attack")
EXPECTED_LABELS = {
    "sql_injection": "SQL Injection",
    "code_injection": "Code Injection",
    "general_attack": "Other Attacks",
}
FAMILY_PREFIXES = {
    "sql_injection": "SQL",
    "code_injection": "CODE",
    "general_attack": "GEN",
}
VARIANTS = ("seed", "spacing", "case", "delimiter", "obfuscation")


@dataclass(frozen=True, slots=True)
class Seed:
    seed_id: str
    family: str
    payload: str
    description: str


@dataclass(frozen=True, slots=True)
class CatalogCase:
    case_id: str
    seed_id: str
    family: str
    expected_label: str
    variant: str
    mutation: str
    payload: str
    wire_query: str
    request_uri: str
    payload_sha256: str
    wire_sha256: str
    description: str
    ground_truth_status: str
    replay_policy: str
    expected_waf: str
    selection_tags: tuple[str, ...]
    is_seed: bool


def _seed_rows() -> tuple[Seed, ...]:
    """Return the reviewed, inert seed vocabulary.

    No seed causes command execution, file access, network access, database
    mutation, or template rendering. The strings are only query values on
    the demo portal route.
    """

    sql = (
        ("SQL-SEED-001", "' OR '1'='1", "Boolean tautology with quoted strings"),
        ("SQL-SEED-002", "' OR 1=1 --", "Boolean tautology with line comment"),
        ("SQL-SEED-003", "admin'--", "Authentication-style comment termination"),
        ("SQL-SEED-004", "1' AND '1'='1", "Quoted boolean conjunction"),
        ("SQL-SEED-005", "1') OR ('1'='1", "Nested delimiter tautology"),
        ("SQL-SEED-006", "' UNION SELECT NULL--", "Non-destructive UNION shape"),
        ("SQL-SEED-007", "1 UNION SELECT NULL,NULL--", "Numeric UNION shape"),
        ("SQL-SEED-008", "1' ORDER BY 1--", "ORDER BY probing shape"),
        ("SQL-SEED-009", "1' AND 1=2--", "False boolean comparison"),
        ("SQL-SEED-010", "x' XOR 'x'='x", "Alternate boolean operator"),
    )
    code = (
        (
            "CODE-SEED-001",
            "report.pdf; echo CYBERTRACE_TEST",
            "Inert shell command separator using echo",
        ),
        (
            "CODE-SEED-002",
            "$" + "(printf CYBERTRACE_TEST)",
            "Inert shell command substitution using printf",
        ),
        (
            "CODE-SEED-003",
            chr(96) + "printf CYBERTRACE_TEST" + chr(96),
            "Inert backtick command substitution using printf",
        ),
        (
            "CODE-SEED-004",
            "$" + "{IFS}echo$" + "{IFS}CYBERTRACE_TEST",
            "Shell IFS separator with inert echo",
        ),
        (
            "CODE-SEED-005",
            "__import__('math').sqrt(4)",
            "Side-effect-free Python expression",
        ),
        ("CODE-SEED-006", "eval('1+1')", "Side-effect-free arithmetic evaluation"),
        (
            "CODE-SEED-007",
            "function(){return 1}",
            "Side-effect-free JavaScript function expression",
        ),
        ("CODE-SEED-008", "$" + "{7*7}", "Expression-wrapper syntax"),
        ("CODE-SEED-009", "#{7*7}", "Template expression syntax"),
        ("CODE-SEED-010", "{{7*7}}", "Template arithmetic expression"),
    )
    general = (
        (
            "GEN-SEED-001",
            "<script>console.log('CYBERTRACE_TEST')</script>",
            "Script-tag XSS shape with a local console marker",
        ),
        (
            "GEN-SEED-002",
            "<img src=x onerror=alert(1)>",
            "Event-handler XSS shape",
        ),
        ("GEN-SEED-003", "<svg onload=alert(1)>", "SVG event-handler XSS shape"),
        (
            "GEN-SEED-004",
            "../../../../etc/passwd",
            "Unix path-traversal string used only as a query value",
        ),
        (
            "GEN-SEED-005",
            "..%2f..%2fetc%2fpasswd",
            "Percent-encoded traversal string",
        ),
        (
            "GEN-SEED-006",
            r"..\..\windows\system32\drivers\etc\hosts",
            "Windows path-traversal string",
        ),
        (
            "GEN-SEED-007",
            "..%5c..%5cwindows%5csystem32%5cdrivers%5cetc%5chosts",
            "Percent-encoded Windows traversal string",
        ),
        ("GEN-SEED-008", "{{config}}", "Template-object disclosure shape"),
        (
            "GEN-SEED-009",
            "<iframe src=javascript:alert(1)>",
            "Inline-script iframe shape",
        ),
        (
            "GEN-SEED-010",
            "&#x3c;script&#x3e;alert(1)&#x3c;/script&#x3e;",
            "HTML-entity encoded script shape",
        ),
    )

    rows: list[Seed] = []
    for family, values in (
        ("sql_injection", sql),
        ("code_injection", code),
        ("general_attack", general),
    ):
        rows.extend(
            Seed(
                seed_id=seed_id, family=family, payload=payload, description=description
            )
            for seed_id, payload, description in values
        )
    return tuple(rows)


def seeds() -> tuple[Seed, ...]:
    return _seed_rows()


def _sql_case(payload: str) -> str:
    replacements = (
        ("UNION", "UnIoN"),
        ("SELECT", "SeLeCt"),
        ("ORDER", "OrDeR"),
        ("AND", "aNd"),
        ("OR", "oR"),
        ("XOR", "xOr"),
    )
    result = payload
    for word, replacement in replacements:
        result = re.sub(word, replacement, result, flags=re.IGNORECASE)
    if result == payload:
        return payload.swapcase()
    return result


def _spacing_variant(seed: Seed) -> str:
    if " " in seed.payload:
        replacement = {
            "sql_injection": "/**/",
            "code_injection": "$" + "{IFS}",
            "general_attack": "\t",
        }[seed.family]
        return seed.payload.replace(" ", replacement)
    suffix = {
        "sql_injection": "/**/",
        "code_injection": ";echo",
        "general_attack": "%00",
    }[seed.family]
    return seed.payload + suffix


def _case_variant(seed: Seed) -> str:
    if seed.family == "sql_injection":
        return _sql_case(seed.payload)
    result = seed.payload.swapcase()
    if result == seed.payload:
        return f"{seed.payload} + 0"
    return result


def _delimiter_variant(seed: Seed) -> str:
    if seed.family == "general_attack":
        return f'<div data-panel="{seed.payload}">'
    return f"({seed.payload})"


def _obfuscation_variant(seed: Seed) -> str:
    if seed.family == "sql_injection":
        result = seed.payload
        for word in ("UNION", "SELECT", "ORDER", "AND", "OR", "XOR"):
            result = re.sub(
                word,
                lambda match: f"{match.group(0)[:1]}/**/{match.group(0)[1:]}",
                result,
                flags=re.IGNORECASE,
            )
        if result == seed.payload:
            result += "/**/panel"
        return result

    if seed.family == "code_injection":
        result = seed.payload.replace("printf", "pri" + "$" + "{IFS}" + "ntf")
        result = result.replace("echo", "e" + "$" + "{IFS}" + "cho")
        result = result.replace("return", "ret" + "$" + "{IFS}" + "urn")
        if result == seed.payload:
            result = f"({seed.payload})+0"
        return result

    result = (
        seed.payload.replace("<", "&#60;").replace(">", "&#62;").replace("/", "%2f")
    )
    if result == seed.payload:
        result += "%0a"
    return result


def _mutate(seed: Seed, variant: str) -> str:
    if variant == "seed":
        return seed.payload
    if variant == "spacing":
        return _spacing_variant(seed)
    if variant == "case":
        return _case_variant(seed)
    if variant == "delimiter":
        return _delimiter_variant(seed)
    if variant == "obfuscation":
        return _obfuscation_variant(seed)
    raise ValueError(f"unsupported variant: {variant}")


def _wire_query(payload: str, variant: str, seed_number: int) -> str:
    if variant in {"seed", "case", "obfuscation"}:
        encoded = quote_plus(payload, safe="")
    else:
        encoded = quote(payload, safe="")
    if variant == "obfuscation" and seed_number % 2 == 0:
        encoded = re.sub(
            r"%[0-9A-Fa-f]{2}",
            lambda match: match.group(0).lower(),
            encoded,
        )
    return encoded


def _expected_waf(family: str) -> str:
    if family == "sql_injection":
        return "BLOCK_IF_CRS_MATCHES"
    return "RECORD_OR_BLOCK"


def _build_case(
    seed: Seed,
    *,
    seed_number: int,
    variant_number: int,
    variant: str,
    family_number: int,
) -> CatalogCase:
    payload = _mutate(seed, variant)
    wire_query = _wire_query(payload, variant, seed_number)
    prefix = FAMILY_PREFIXES[seed.family]
    case_number = (seed_number - 1) * len(VARIANTS) + variant_number
    case_id = f"SR-{prefix}-{case_number:03d}"
    mutation = "seed_identity" if variant == "seed" else f"{variant}_mutation"
    description = (
        seed.description
        if variant == "seed"
        else f"{seed.description}; applied {mutation.replace('_', ' ')}"
    )
    tags = [
        "search_records_only",
        "local_demo_only",
        "non_destructive",
        "panel_reference_candidate",
    ]
    if variant == "seed":
        tags.append("baseline_seed")
    else:
        tags.extend(["mutation_candidate", f"mutation_{variant}"])
    if family_number == 1 and variant == "seed":
        tags.append("first_baseline_batch")

    return CatalogCase(
        case_id=case_id,
        seed_id=seed.seed_id,
        family=seed.family,
        expected_label=EXPECTED_LABELS[seed.family],
        variant=variant,
        mutation=mutation,
        payload=payload,
        wire_query=wire_query,
        request_uri=f"{ROUTE_PATH}?{QUERY_PARAMETER}={wire_query}",
        payload_sha256=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        wire_sha256=hashlib.sha256(wire_query.encode("utf-8")).hexdigest(),
        description=description,
        ground_truth_status=(
            "baseline_candidate" if variant == "seed" else "proposed_variant"
        ),
        replay_policy="local_search_records_only",
        expected_waf=_expected_waf(seed.family),
        selection_tags=tuple(tags),
        is_seed=variant == "seed",
    )


def _case_to_dict(case: CatalogCase) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "case_version": 1,
        "seed_id": case.seed_id,
        "family": case.family,
        "method": METHOD,
        "route_path": ROUTE_PATH,
        "query_parameter": QUERY_PARAMETER,
        "expected_label": case.expected_label,
        "variant": case.variant,
        "mutation": case.mutation,
        "payload": case.payload,
        "wire_query": case.wire_query,
        "request_uri": case.request_uri,
        "payload_sha256": case.payload_sha256,
        "wire_sha256": case.wire_sha256,
        "description": case.description,
        "ground_truth_status": case.ground_truth_status,
        "replay_policy": case.replay_policy,
        "expected_waf": case.expected_waf,
        "selection_tags": list(case.selection_tags),
        "is_seed": case.is_seed,
    }


def build_cases(phase: str = "full") -> list[CatalogCase]:
    if phase not in {"seeds", "full"}:
        raise ValueError("phase must be 'seeds' or 'full'")

    result: list[CatalogCase] = []
    seen_payloads: dict[str, set[tuple[str, str]]] = {
        family: set() for family in FAMILIES
    }
    family_counts = {family: 0 for family in FAMILIES}
    for seed in seeds():
        family_counts[seed.family] += 1
        family_number = family_counts[seed.family]
        variants: Iterable[str] = ("seed",) if phase == "seeds" else VARIANTS
        for variant_number, variant in enumerate(variants, start=1):
            case = _build_case(
                seed,
                seed_number=family_number,
                variant_number=variant_number,
                variant=variant,
                family_number=family_number,
            )
            key = (case.payload, case.wire_query)
            if key in seen_payloads[seed.family]:
                raise ValueError(
                    f"duplicate generated case in {seed.family}: {case.case_id}"
                )
            seen_payloads[seed.family].add(key)
            result.append(case)

    expected_count = 30 if phase == "seeds" else 150
    if len(result) != expected_count:
        raise AssertionError(
            f"expected {expected_count} cases, generated {len(result)}"
        )
    return result


def build_catalog(phase: str = "full") -> dict[str, Any]:
    cases = build_cases(phase)
    catalog_version = SEED_CATALOG_VERSION if phase == "seeds" else CATALOG_VERSION
    return {
        "schema_version": 1,
        "catalog_version": catalog_version,
        "scope": "local demo portal only; Search Records route only",
        "route": {
            "method": METHOD,
            "path": ROUTE_PATH,
            "query_parameter": QUERY_PARAMETER,
        },
        "safety": {
            "non_destructive_inputs": True,
            "no_execution_endpoint": True,
            "no_public_hostnames": True,
            "maximum_cases": 150,
        },
        "confidence_note": (
            "Confidence is observed from the unchanged model. Cases are not "
            "altered to force a LOW, MEDIUM, HIGH, or CRITICAL result."
        ),
        "expected_action_policy": (
            "Normal=ALLOWED; SQL Injection/Code Injection LOW=ALLOWED, "
            "MEDIUM=THROTTLED, HIGH/CRITICAL=BLOCKED; Other Attacks=None"
        ),
        "cases": [_case_to_dict(case) for case in cases],
    }


def load_catalog(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read catalogue: {path}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError("catalogue must be an object with a cases array")
    route = payload.get("route")
    if route != {
        "method": METHOD,
        "path": ROUTE_PATH,
        "query_parameter": QUERY_PARAMETER,
    }:
        raise ValueError("catalogue route must be GET /records/search?query=...")

    seen_ids: set[str] = set()
    seen_wire: set[str] = set()
    for index, case in enumerate(payload["cases"], start=1):
        if not isinstance(case, dict):
            raise ValueError(f"catalogue case {index} is not an object")
        for key in (
            "case_id",
            "family",
            "expected_label",
            "payload",
            "wire_query",
            "request_uri",
        ):
            if not isinstance(case.get(key), str) or not case[key]:
                raise ValueError(f"catalogue case {index} is missing {key}")
        if case["case_id"] in seen_ids:
            raise ValueError(f"duplicate case id: {case['case_id']}")
        if case["wire_query"] in seen_wire:
            raise ValueError(f"duplicate wire query: {case['case_id']}")
        if case["family"] not in FAMILIES:
            raise ValueError(f"unsupported family: {case['family']}")
        if case["expected_label"] != EXPECTED_LABELS[case["family"]]:
            raise ValueError(f"expected label does not match family: {case['case_id']}")
        if case["method"] != METHOD or case["route_path"] != ROUTE_PATH:
            raise ValueError(f"case is outside Search Records route: {case['case_id']}")
        if (
            case["request_uri"]
            != f"{ROUTE_PATH}?{QUERY_PARAMETER}={case['wire_query']}"
        ):
            raise ValueError(f"request URI is not canonical: {case['case_id']}")
        seen_ids.add(case["case_id"])
        seen_wire.add(case["wire_query"])
    return payload


def _markdown(catalog: dict[str, Any]) -> str:
    cases = catalog["cases"]
    counts = {
        family: sum(case["family"] == family for case in cases) for family in FAMILIES
    }
    lines = [
        "# Search Records attack catalogue",
        "",
        f"Catalogue version: {catalog['catalog_version']}",
        "",
        "This catalogue is restricted to the local demo portal GET "
        "/records/search?query=... route. Exact query values and wire encodings "
        "are stored in the JSON catalogue; this summary intentionally omits them "
        "from the table.",
        "",
        f"Counts: SQL injection={counts['sql_injection']}, "
        f"code injection={counts['code_injection']}, "
        f"general attack={counts['general_attack']}.",
        "",
        "| Case | Family | Variant | Expected label | Ground-truth status |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in cases:
        lines.append(
            f"| {case['case_id']} | {case['family']} | {case['variant']} | "
            f"{case['expected_label']} | {case['ground_truth_status']} |"
        )
    return "\n".join(lines) + "\n"


def write_catalog(path: Path, *, phase: str, output_format: str) -> dict[str, Any]:
    catalog = build_catalog(phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "json":
        path.write_text(
            json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    elif output_format == "jsonl":
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for case in catalog["cases"]:
                handle.write(json.dumps(case, ensure_ascii=False) + "\n")
    elif output_format == "markdown":
        path.write_text(_markdown(catalog), encoding="utf-8")
    else:
        raise ValueError(f"unsupported format: {output_format}")
    return catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic Search Records-only attack catalogue."
    )
    parser.add_argument("--phase", choices=("seeds", "full"), default="full")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--format", choices=("json", "jsonl", "markdown"), default="json"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    catalog = write_catalog(args.output, phase=args.phase, output_format=args.format)
    counts = {
        family: sum(case["family"] == family for case in catalog["cases"])
        for family in FAMILIES
    }
    print(
        f"catalog_version={catalog['catalog_version']} cases={len(catalog['cases'])} "
        f"sql={counts['sql_injection']} code={counts['code_injection']} "
        f"general={counts['general_attack']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
