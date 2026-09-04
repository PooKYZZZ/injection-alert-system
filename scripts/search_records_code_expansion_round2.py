"""Build and report the second Search Records code-injection expansion.

Round two starts from the 70 exact classifier-positive cases observed in the
first follow-up run: the 12 original positives and the 58 first-round
expansion positives.  It creates a deterministic, bounded set of 200
side-effect-free code-shaped query values.  The values are never evaluated;
they are sent only to the local demo portal's Search Records route.

The module deliberately keeps the seed snapshot, generated catalogue, and
observed result report separate.  A model prediction is recorded as observed
evidence, not as proof that arbitrary code executed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

from scripts.search_records_followup_catalog import (
    BASE_CATALOG,
    EXPECTED_LABELS,
    METHOD,
    QUERY_PARAMETER,
    ROUTE_PATH,
    _case,
    _catalog,
    _wire_query,
    validate_followup_catalog,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ROUND2_CATALOG_VERSION = "search-records-code-expansion-round2-v1"
ROUND2_SEED_FIXTURE_TYPE = "confirmed_code_injection_seeds_round2"
ROUND2_CASE_COUNT = 200
ROUND2_SEED_COUNT = 70
ROUND2_SEED_GROUPS = (
    "original_known_code_injection_cases",
    "expanded_known_code_injection_cases",
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


def _source_case_and_result(entry: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(entry, dict):
        raise ValueError("seed report group entry must be an object")
    case = entry.get("case")
    observed = entry.get("observed_result")
    if isinstance(case, dict) and isinstance(observed, dict):
        return case, observed
    if "case_id" in entry:
        return entry, entry
    raise ValueError("seed report group entry has no case/result data")


def _confirmed_seed_entries(report_path: Path) -> list[dict[str, Any]]:
    report = _read_object(report_path)
    groups = report.get("groups")
    if not isinstance(groups, dict):
        raise ValueError("round-one report is missing groups")

    entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for group_name in ROUND2_SEED_GROUPS:
        group = groups.get(group_name)
        if not isinstance(group, list):
            raise ValueError(f"round-one report is missing group {group_name}")
        for raw_entry in group:
            case, observed = _source_case_and_result(raw_entry)
            case_id = str(case.get("case_id") or observed.get("case_id") or "")
            if not case_id or case_id in seen_ids:
                raise ValueError(f"duplicate or missing round-two seed ID: {case_id}")
            if case.get("family") != "code_injection":
                raise ValueError(f"round-two seed is not code injection: {case_id}")
            if case.get("route_path") != ROUTE_PATH or case.get("method") != METHOD:
                raise ValueError(f"round-two seed is outside Search Records: {case_id}")
            if case.get("expected_label") != EXPECTED_LABELS["code_injection"]:
                raise ValueError(
                    f"round-two seed has the wrong expected label: {case_id}"
                )
            if observed.get("predicted_label") != EXPECTED_LABELS["code_injection"]:
                raise ValueError(
                    f"round-two seed is not a Code Injection prediction: {case_id}"
                )
            if observed.get("classification_correct") != "True":
                raise ValueError(f"round-two seed is not marked correct: {case_id}")
            payload = str(case.get("payload") or "")
            if not payload:
                raise ValueError(f"round-two seed has no payload: {case_id}")
            entries.append(
                {
                    "case": dict(case),
                    "observed_result": dict(observed),
                    "source_group": group_name,
                }
            )
            seen_ids.add(case_id)

    if len(entries) != ROUND2_SEED_COUNT:
        raise ValueError(
            f"round-one report must provide exactly {ROUND2_SEED_COUNT} "
            "confirmed seeds; "
            f"found {len(entries)}"
        )
    return entries


def build_seed_snapshot(report_path: Path) -> dict[str, Any]:
    """Preserve the exact 70 source rows before generating round two."""

    entries = _confirmed_seed_entries(report_path)
    return {
        "schema_version": 1,
        "fixture_type": ROUND2_SEED_FIXTURE_TYPE,
        "seed_count": len(entries),
        "route": _route(),
        "source_files": {
            "round_one_report": str(report_path),
            "round_one_report_sha256": _sha256_file(report_path),
        },
        "preservation_note": (
            "Immutable snapshot of the 70 exact Code Injection classifier-positive "
            "cases used as round-two seeds: 12 original positives and 58 first-round "
            "expansion positives. This is observed classification evidence, not proof "
            "that the query value was executed."
        ),
        "cases": entries,
    }


def _profile(payload: str) -> str:
    """Choose a syntax profile without treating the input as executable code."""

    lower = payload.lower()
    if "__import__" in lower or "eval(" in lower:
        return "python"
    if "ifs" in lower or "printf" in lower or "echo" in lower or "$((" in lower:
        return "shell"
    if "function" in lower or "return" in lower or "=>" in payload:
        return "javascript"
    if "{{" in payload or "#{" in payload or "${" in payload:
        return "template"
    if "`" in payload or "$ (" in lower or "$ (" in payload:
        return "shell"
    return "template"


def _number(serial: int) -> str:
    return str(2 + (serial % 7))


def _expression(profile: str, serial: int) -> str:
    number = _number(serial)
    if profile == "python":
        return f"({number}-1)"
    if profile == "javascript":
        return f"({number}+0)"
    if profile == "shell":
        return "printf '%s' CYBERTRACE_TEST"
    return f"{number}*1"


def _comment(profile: str, serial: int) -> str:
    marker = f"CYBERTRACE_R2_{serial:03d}"
    if profile in {"python", "shell"}:
        return f"# {marker}"
    if profile == "javascript":
        return f"// {marker}"
    return f"/*{marker}*/"


def _mutate_nested_expression(payload: str, profile: str, serial: int) -> str:
    expression = _expression(profile, serial)
    if profile == "python":
        return f"(({payload})); {expression}"
    if profile == "javascript":
        return f"(()=>{{return ({payload});}})(); {expression}"
    if profile == "shell":
        return f"( {payload}; {expression} )"
    return f"{{{{ ({payload}) + ({expression}) }}}}"


def _mutate_block_wrapper(payload: str, profile: str, serial: int) -> str:
    expression = _expression(profile, serial)
    if profile == "python":
        return f"(lambda: ({payload}))(); {expression}"
    if profile == "javascript":
        return f"function CYBERTRACE_R2_{serial:03d}(){{return ({payload});}}"
    if profile == "shell":
        return (
            f"function CYBERTRACE_R2_{serial:03d}(){{ printf '%s' "
            f"CYBERTRACE_TEST; }}; {payload}"
        )
    return f"{{% if true %}}({payload}){{% endif %}}"


def _mutate_separator_expression(payload: str, profile: str, serial: int) -> str:
    expression = _expression(profile, serial)
    if profile == "shell":
        return f"{payload}; {expression}"
    return f"{payload}; {expression}"


def _mutate_line_break(payload: str, profile: str, serial: int) -> str:
    expression = _expression(profile, serial)
    if profile == "javascript":
        return f"{{\n  {payload}\n}}\n{expression}"
    return f"{payload}\n{expression}"


def _mutate_quote_form(payload: str, profile: str, serial: int) -> str:
    if profile == "python":
        rewritten = payload.replace("'", '"')
        return f'({rewritten}); eval("{_number(serial)}-1")'
    if profile == "javascript":
        rewritten = payload.replace("'", '"')
        return f'({rewritten}); (()=>{{return "CYBERTRACE_TEST"}})()'
    if profile == "shell":
        return f'printf "%s" CYBERTRACE_TEST; {payload}'
    return f'{{{{ "CYBERTRACE_TEST" }}}}; {payload}'


def _mutate_encoded_delimiter(payload: str, profile: str, serial: int) -> str:
    encoded = (
        payload.replace(" ", "%20")
        .replace(";", "%3B")
        .replace("(", "%28")
        .replace(")", "%29")
    )
    if encoded == payload:
        encoded = f"{encoded}%0A{_number(serial)}%2B0"
    else:
        encoded = f"{encoded}%0A{_number(serial)}%2B0"
    return encoded


def _mutate_comment_boundary(payload: str, profile: str, serial: int) -> str:
    return f"{payload} {_comment(profile, serial)}\n{_expression(profile, serial)}"


def _mutate_argument_rewrite(payload: str, profile: str, serial: int) -> str:
    number = _number(serial)
    if profile == "python":
        return f'getattr(__import__("math"), "sqrt")({number}+{number}); {payload}'
    if profile == "javascript":
        return f"(()=>{{const value={number}+{number}; return value;}})(); {payload}"
    if profile == "shell":
        return f"$(printf '%s' CYBERTRACE_TEST); {payload}"
    return f"{{{{ ({number}+{number}) }}}}; {payload}"


def _mutate_computed_call(payload: str, profile: str, serial: int) -> str:
    if profile == "python":
        return f"getattr(__import__('math'), 'sqrt')({_number(serial)}); ({payload})"
    if profile == "javascript":
        return f"({{run:()=>({payload})}}).run();"
    if profile == "shell":
        return f"{{ printf '%s' CYBERTRACE_TEST; }}; {payload}"
    return f"{{{{({payload})}}}}"


def _mutate_alternate_delimiter(payload: str, profile: str, serial: int) -> str:
    if profile == "python":
        return f"[{payload}, {_number(serial)}-{_number(serial)}]"
    if profile == "javascript":
        return f"[{payload}, {_number(serial)}-{_number(serial)}].map(x=>x)"
    if profile == "shell":
        return f"[ {payload} ]; printf '%s' CYBERTRACE_TEST"
    return f"[{{{{ {payload} }}}}]"


def _mutate_case_marker(payload: str, profile: str, serial: int) -> str:
    marker = f"CyberTraceFlag{serial:03d}"
    if profile == "python":
        return f"{payload}; {marker.lower()} = {_number(serial)}"
    if profile == "javascript":
        return f"{payload}; const {marker} = {_number(serial)};"
    if profile == "shell":
        return f"{marker.upper()}={_number(serial)}; {payload}"
    return f"{{{{ {marker.swapcase()}|{payload} }}}}"


def _mutate_nested_block(payload: str, profile: str, serial: int) -> str:
    if profile == "python":
        return f"(\n  ({payload})\n)\n+ {_number(serial)}-0"
    if profile == "javascript":
        return f"(()=>{{return (()=>({payload}))()}})()"
    if profile == "shell":
        return f"{{ {{ {payload}; }}; }}"
    return f"{{{{ {{%raw%}} {payload} {{%endraw%}} }}}}"


def _mutate_operator_chain(payload: str, profile: str, serial: int) -> str:
    number = _number(serial)
    if profile == "shell":
        return (
            f"{payload} && printf '%s' CYBERTRACE_TEST || printf '%s' CYBERTRACE_TEST"
        )
    if profile == "python":
        return f"({payload}) or ({number} == {number})"
    if profile == "javascript":
        return f"({payload}) || ({number} === {number})"
    return f"{{{{ ({payload}) or ({number}=={number}) }}}}"


def _mutate_encoded_wrapper(payload: str, profile: str, serial: int) -> str:
    encoded_open = "%28"
    encoded_close = "%29"
    return f"{encoded_open}{payload}{encoded_close}%3B{_number(serial)}%2B0"


ROUND2_MUTATIONS: tuple[tuple[str, Callable[[str, str, int], str]], ...] = (
    ("nested_expression", _mutate_nested_expression),
    ("block_wrapper", _mutate_block_wrapper),
    ("separator_expression", _mutate_separator_expression),
    ("line_break_boundary", _mutate_line_break),
    ("quote_form_rewrite", _mutate_quote_form),
    ("encoded_delimiter_chain", _mutate_encoded_delimiter),
    ("comment_boundary", _mutate_comment_boundary),
    ("argument_rewrite", _mutate_argument_rewrite),
    ("computed_call_wrapper", _mutate_computed_call),
    ("alternate_delimiter", _mutate_alternate_delimiter),
    ("case_marker_context", _mutate_case_marker),
    ("nested_block_context", _mutate_nested_block),
    ("operator_chain", _mutate_operator_chain),
    ("encoded_wrapper_chain", _mutate_encoded_wrapper),
)


def _append_disambiguator(payload: str, serial: int) -> str:
    return f"{payload} /*CYBERTRACE_R2_UNIQUE_{serial:03d}*/"


def _seed_rows(seed_path: Path) -> list[dict[str, Any]]:
    payload = _read_object(seed_path)
    if payload.get("fixture_type") != ROUND2_SEED_FIXTURE_TYPE:
        raise ValueError("unexpected round-two seed fixture type")
    if payload.get("route") != _route():
        raise ValueError("round-two seed fixture is outside Search Records")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != ROUND2_SEED_COUNT:
        raise ValueError(
            f"round-two seed fixture must contain {ROUND2_SEED_COUNT} cases"
        )
    return cases


def build_round2_catalog(
    *, seed_path: Path, base_catalog_path: Path = BASE_CATALOG
) -> dict[str, Any]:
    seeds = _seed_rows(seed_path)
    base_catalog = _read_object(base_catalog_path)
    base_cases = base_catalog.get("cases")
    if not isinstance(base_cases, list):
        raise ValueError("base attack catalogue is missing cases")
    existing_payloads = {str(case.get("payload") or "") for case in base_cases}
    existing_wires = {str(case.get("wire_query") or "") for case in base_cases}
    seed_payloads: set[str] = set()
    cases: list[dict[str, Any]] = []

    for seed_index, seed_entry in enumerate(seeds):
        case = seed_entry.get("case")
        if not isinstance(case, dict):
            raise ValueError(f"round-two seed {seed_index + 1} has no case")
        seed_id = str(case.get("case_id") or "")
        source_payload = str(case.get("payload") or "")
        if not seed_id or not source_payload:
            raise ValueError(f"round-two seed {seed_index + 1} is incomplete")
        seed_payloads.add(source_payload)
        profile = _profile(source_payload)
        mutation_indexes = [
            (seed_index * 3) % len(ROUND2_MUTATIONS),
            (seed_index * 3 + 1) % len(ROUND2_MUTATIONS),
        ]
        if seed_index < 60:
            mutation_indexes.append((seed_index * 3 + 2) % len(ROUND2_MUTATIONS))

        for mutation_index in mutation_indexes:
            mutation_name, mutation = ROUND2_MUTATIONS[mutation_index]
            serial = len(cases) + 1
            candidate = mutation(source_payload, profile, serial)
            while (
                not candidate
                or candidate in existing_payloads
                or candidate in seed_payloads
                or _wire_query(candidate) in existing_wires
            ):
                candidate = _append_disambiguator(candidate, serial)
            existing_payloads.add(candidate)
            existing_wires.add(_wire_query(candidate))
            cases.append(
                _case(
                    case_id=f"SR-CODE-R2-{serial:03d}",
                    seed_id=seed_id,
                    source_seed_payload=source_payload,
                    family="code_injection",
                    expected_label=EXPECTED_LABELS["code_injection"],
                    variant="round2_expansion",
                    mutation=mutation_name,
                    payload=candidate,
                    description=(
                        f"Derived from confirmed classifier-positive seed {seed_id}; "
                        f"profile={profile}; applied {mutation_name.replace('_', ' ')}"
                    ),
                    status="proposed_code_expansion_round2",
                    tags=[
                        "search_records_only",
                        "local_demo_only",
                        "non_destructive",
                        "derived_from_70_confirmed_code_seeds",
                        "code_expansion_round2_candidate",
                        f"syntax_profile_{profile}",
                        f"mutation_{mutation_name}",
                    ],
                    expected_waf="RECORD_OR_BLOCK",
                    is_seed=False,
                )
            )

    if len(cases) != ROUND2_CASE_COUNT:
        raise AssertionError(
            f"expected {ROUND2_CASE_COUNT} round-two cases, generated {len(cases)}"
        )
    return _catalog(
        catalog_version=ROUND2_CATALOG_VERSION,
        cases=cases,
        maximum_cases=ROUND2_CASE_COUNT,
        description=(
            "local demo portal only; 200 inert code-injection variations derived "
            "from 70 confirmed Search Records classifier-positive seeds"
        ),
    )


def validate_round2_catalog(path: Path) -> dict[str, Any]:
    catalog = validate_followup_catalog(path)
    if catalog.get("catalog_version") != ROUND2_CATALOG_VERSION:
        raise ValueError("unexpected round-two catalogue version")
    if len(catalog["cases"]) != ROUND2_CASE_COUNT:
        raise ValueError(f"round-two catalogue must contain {ROUND2_CASE_COUNT} cases")
    if catalog.get("safety", {}).get("maximum_cases") != ROUND2_CASE_COUNT:
        raise ValueError("round-two catalogue has an unexpected case limit")
    if any(case.get("variant") != "round2_expansion" for case in catalog["cases"]):
        raise ValueError("round-two catalogue contains a non-round-two case")
    return catalog


def _read_result_report(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = _read_object(path)
    metadata = payload.get("metadata")
    rows = payload.get("rows")
    if not isinstance(metadata, dict) or not isinstance(rows, list):
        raise ValueError("round-two result report must contain metadata and rows")
    if metadata.get("catalog_version") != ROUND2_CATALOG_VERSION:
        raise ValueError("round-two result report has the wrong catalogue version")
    if metadata.get("route_path") != ROUTE_PATH or metadata.get("method") != METHOD:
        raise ValueError("round-two result report is outside Search Records")
    return metadata, rows


def _seed_snapshot_rows(seed_path: Path) -> list[dict[str, Any]]:
    entries = _seed_rows(seed_path)
    rows: list[dict[str, Any]] = []
    for entry in entries:
        observed = entry.get("observed_result")
        if not isinstance(observed, dict):
            raise ValueError("round-two seed snapshot has no observed result")
        rows.append(dict(observed))
    return rows


def _correct(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("classification_correct") == "True"]


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(
        sorted(Counter(str(row.get(key) or "<missing>") for row in rows).items())
    )


def _mutation_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("mutation") or "<missing>")].append(row)
    result: dict[str, dict[str, Any]] = {}
    for mutation, mutation_rows in sorted(grouped.items()):
        correct = len(_correct(mutation_rows))
        result[mutation] = {
            "tested": len(mutation_rows),
            "correct": correct,
            "accuracy_percent": round(100 * correct / len(mutation_rows), 2),
            "predicted_labels": _counts(mutation_rows, "predicted_label"),
        }
    return result


def _correlation(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "tested": len(rows),
        "requests_executed": sum(row.get("request_executed") == "True" for row in rows),
        "audit_correlated": sum(bool(row.get("transaction_id")) for row in rows),
        "bridge_correlated": sum(row.get("bridge_found") == "True" for row in rows),
        "terminal_predictions": sum(
            bool(row.get("predicted_label")) and bool(row.get("confidence"))
            for row in rows
        ),
    }


def build_report(
    *, seed_path: Path, catalog_path: Path, result_path: Path
) -> dict[str, Any]:
    seed_entries = _seed_rows(seed_path)
    catalog = validate_round2_catalog(catalog_path)
    metadata, rows = _read_result_report(result_path)
    if len(rows) != ROUND2_CASE_COUNT:
        raise ValueError(
            f"round-two result report must contain {ROUND2_CASE_COUNT} rows"
        )
    catalog_map = {case["case_id"]: case for case in catalog["cases"]}
    seen: set[str] = set()
    for row in rows:
        case_id = str(row.get("case_id") or "")
        if case_id in seen or case_id not in catalog_map:
            raise ValueError(
                f"round-two result has duplicate or unknown case: {case_id}"
            )
        definition = catalog_map[case_id]
        for key in (
            "payload",
            "wire_query",
            "seed_id",
            "source_seed_payload",
            "mutation",
            "expected_label",
            "route_path",
            "method",
        ):
            if str(row.get(key) or "") != str(definition.get(key) or ""):
                raise ValueError(
                    f"round-two result does not match catalogue {key}: {case_id}"
                )
        seen.add(case_id)

    correct = _correct(rows)
    incorrect = [row for row in rows if row.get("classification_correct") != "True"]
    seeds = _seed_snapshot_rows(seed_path)
    seed_ids = {str(row.get("case_id") or "") for row in seeds}
    round2_seed_ids = {str(case.get("seed_id") or "") for case in catalog["cases"]}
    if seed_ids != round2_seed_ids:
        raise ValueError(
            "round-two catalogue does not reference all 70 preserved seeds"
        )

    combined_count = len(seeds) + len(correct)
    return {
        "schema_version": 1,
        "report_type": "search_records_code_expansion_round2",
        "route": _route(),
        "preservation_note": (
            "The 70 confirmed seed rows are copied into a separate fixture and are "
            "not overwritten. Every one of the 200 new observed rows is retained, "
            "including misclassifications."
        ),
        "source_files": {
            "seed_snapshot": str(seed_path),
            "catalog": str(catalog_path),
            "result_report": str(result_path),
        },
        "metadata": metadata,
        "summary": {
            "preserved_confirmed_code_seeds": len(seeds),
            "new_variations_tested": len(rows),
            "new_correctly_classified_code_injection": len(correct),
            "new_misclassified": len(incorrect),
            "new_accuracy_percent": round(100 * len(correct) / len(rows), 2),
            "new_predicted_label_counts": _counts(rows, "predicted_label"),
            "new_misclassified_label_counts": _counts(incorrect, "predicted_label"),
            "confidence_level_counts": _counts(rows, "confidence_level"),
            "mutation_summary": _mutation_summary(rows),
            "correlation": _correlation(rows),
            "confirmed_seed_plus_new_correct": combined_count,
            "confirmed_seed_plus_new_total": len(seeds) + len(rows),
            "confirmed_seed_plus_new_accuracy_percent": round(
                100 * combined_count / (len(seeds) + len(rows)), 2
            ),
        },
        "groups": {
            "preserved_70_confirmed_code_seeds": seed_entries,
            "newly_confirmed_code_injection_cases": correct,
            "misclassified_round2_code_injection_cases": incorrect,
        },
    }


def _markdown_table(rows: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for row in rows:
        lines.append(
            f"| {row.get('case_id', '')} | {row.get('seed_id', '')} | "
            f"{row.get('mutation', '')} | {row.get('payload', '')} | "
            f"{row.get('predicted_label', '')} | {row.get('confidence', '')} | "
            f"{row.get('confidence_level', '')} |"
        )
    return lines


def to_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Search Records Code Injection Expansion Round 2",
        "",
        "Scope: local `GET /records/search?query=...` only; payloads were not "
        "executed.",
        "",
        "## Summary",
        "",
        f"- Preserved classifier-positive seeds: "
        f"{summary['preserved_confirmed_code_seeds']}.",
        f"- New variations tested: {summary['new_variations_tested']}.",
        f"- New Code Injection matches: "
        f"{summary['new_correctly_classified_code_injection']} "
        f"({summary['new_accuracy_percent']}%).",
        f"- New misclassifications: {summary['new_misclassified']}.",
        f"- Seed-plus-new confirmed total: "
        f"{summary['confirmed_seed_plus_new_correct']} "
        f"of {summary['confirmed_seed_plus_new_total']} "
        f"({summary['confirmed_seed_plus_new_accuracy_percent']}%).",
        f"- Correlation: {summary['correlation']['requests_executed']}/"
        f"{summary['correlation']['tested']} requests executed, "
        f"{summary['correlation']['audit_correlated']} audit-correlated, "
        f"{summary['correlation']['bridge_correlated']} bridge-correlated, "
        f"{summary['correlation']['terminal_predictions']} terminal predictions.",
        "",
        "## Predicted labels",
        "",
        "```json",
        json.dumps(summary["new_predicted_label_counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Confidence levels",
        "",
        "```json",
        json.dumps(summary["confidence_level_counts"], indent=2, sort_keys=True),
        "```",
        "",
        "## Mutation results",
        "",
        "| Mutation | Tested | Correct | Accuracy |",
        "| --- | ---: | ---: | ---: |",
    ]
    for mutation, values in summary["mutation_summary"].items():
        lines.append(
            f"| {mutation} | {values['tested']} | {values['correct']} | "
            f"{values['accuracy_percent']}% |"
        )
    lines.extend(
        [
            "",
            "## Misclassified round-two cases",
            "",
            "| Case | Seed | Mutation | Full payload | Predicted | Confidence | Tier |",
            "| --- | --- | --- | --- | --- | ---: | --- |",
        ]
    )
    lines.extend(
        _markdown_table(report["groups"]["misclassified_round2_code_injection_cases"])
    )
    lines.extend(
        [
            "",
            "## Retention",
            "",
            "The exact 70 seed cases are in the separate seed snapshot. The raw JSON "
            "result retains every full payload, source seed, mutation, prediction, "
            "confidence, WAF status, transaction, and bridge correlation.",
            "",
        ]
    )
    return "\n".join(lines)


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
        description="Preserve the 70 confirmed seeds or build/report round-two cases."
    )
    parser.add_argument(
        "--mode", choices=("snapshot", "catalog", "report"), required=True
    )
    parser.add_argument("--round-one-report", type=Path)
    parser.add_argument("--seed-snapshot", type=Path)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--base-catalog", type=Path, default=BASE_CATALOG)
    parser.add_argument("--result-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--output-markdown", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "snapshot":
        if args.round_one_report is None:
            raise SystemExit("snapshot mode requires --round-one-report")
        _write_object(args.output, build_seed_snapshot(args.round_one_report))
        print(f"seed_snapshot_cases={ROUND2_SEED_COUNT}")
        return 0
    if args.mode == "catalog":
        if args.seed_snapshot is None:
            raise SystemExit("catalog mode requires --seed-snapshot")
        catalog = build_round2_catalog(
            seed_path=args.seed_snapshot, base_catalog_path=args.base_catalog
        )
        _write_object(args.output, catalog)
        validate_round2_catalog(args.output)
        print(f"catalog_version={ROUND2_CATALOG_VERSION} cases={ROUND2_CASE_COUNT}")
        return 0
    if args.seed_snapshot is None or args.catalog is None or args.result_report is None:
        raise SystemExit(
            "report mode requires --seed-snapshot, --catalog, and --result-report"
        )
    report = build_report(
        seed_path=args.seed_snapshot,
        catalog_path=args.catalog,
        result_path=args.result_report,
    )
    markdown_path = args.output_markdown or args.output.with_suffix(".md")
    write_report(report, json_path=args.output, markdown_path=markdown_path)
    summary = report["summary"]
    print(
        f"new_code={summary['new_correctly_classified_code_injection']}/"
        f"{summary['new_variations_tested']} "
        f"misclassified={summary['new_misclassified']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
