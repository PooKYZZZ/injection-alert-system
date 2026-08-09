"""Generate deterministic, route-aware fixture batches for the 20-day study."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import quote

from ml_model.preprocessing.model_input import prepare_legacy_model_input
from ml_model.retraining.experiment_contract import canonical_json_sha256, sha256_file

EXPERIMENT_VERSION = "retraining-20-day-v2"
GENERATOR_VERSION = "records-search-generator.v2"
SUPPORTED_SEED = 2026
TOTAL_DAYS = 20
DAILY_SAMPLE_COUNT = 30
NORMAL_COUNT = 20
HARD_NORMAL_COUNT = 8
ATTACK_COUNT = 10
TARGET_METHOD = "GET"
TARGET_ROUTE = "/records/search"
PREPROCESSING_VERSION = "http-preprocessor-v1"
SOURCE_TYPE = "curated_simulation_fixture"
REVIEW_STATUS = "curated_simulation_fixture"

DAY_PROFILES = (
    "Oak Valley agricultural cooperative permit registry",
    "Riverbend municipal assessment ledger",
    "Pinecrest agricultural parcel archive",
    "North Harbor cadastral review docket",
    "Lakeside conservation easement index",
    "Cedar Ridge transfer certificate archive",
    "Westfield residential zoning register",
    "Silver Creek boundary survey ledger",
    "Maple Junction historical parcel record",
    "East Meadow ownership verification file",
    "Brookstone rural assessment schedule",
    "Sunrise district transfer history index",
    "Highland watershed land-use register",
    "Greenfield registry maintenance docket",
    "Redwood township parcel classification log",
    "Clearwater agricultural permit archive",
    "Hillcrest municipal boundary record",
    "Fairview development review ledger",
    "Golden Plains title reference index",
    "Stonebridge public easement register",
)

ORDINARY_NORMAL_TEMPLATES = (
    "parcel register {profile} {marker} reference 2026",
    "owner lookup {profile} {marker} district file",
    "permit archive {profile} {marker} reference",
    "assessment ledger {profile} {marker} revision",
    "easement record {profile} {marker} page summary",
    "classification {profile} {marker} residential parcel",
    "registry office {profile} {marker} index",
    "transfer docket {profile} {marker} number",
    "survey record {profile} {marker} boundary",
    "recording date {profile} {marker} March notice",
    "public notice {profile} {marker} parcel",
    "search keyword {profile} {marker} record",
)

HARD_NORMAL_TEMPLATES = (
    "Union Square {marker} records for {profile}",
    "Script documentation {marker} title {profile}",
    "Command center {marker} permit {profile}",
    "Select committee {marker} registry {profile}",
    "OR history {marker} note {profile}",
    "AND gate {marker} map {profile}",
    "Template guide {marker} parcel {profile}",
    "Shell command {marker} reference {profile}",
)

SQL_TEMPLATES = (
    "{profile}' OR '7'='7' -- docket-{day} {marker}",
    (
        "{profile}' UNION SELECT parcel_no,owner_name FROM land_index "
        "-- ref-{day} {marker}"
    ),
    "{profile}'; WAITFOR DELAY '0:0:1' -- registry-{day} {marker}",
    "{profile}' AND EXISTS (SELECT * FROM records) -- page-{day} {marker}",
)

CODE_TEMPLATES = (
    "{profile} {{{{ {number}*{number} }}}} {marker}",
    "{profile} ${{runtime.evaluate('parcel-{day}')}} {marker}",
    "{profile} <%= {day}*{day} %> {marker}",
    "{profile} eval('lookup-{day}') {marker}",
)

OTHER_TEMPLATES = (
    "<script>confirm('ref-{day}')</script> {profile} {marker}",
    "<img src=x onerror=alert({day})> {profile} {marker}",
    "{profile}/../../etc/passwd?ref={day} {marker}",
    "{profile}; whoami && cat /etc/hosts {marker}",
)

ROW_MARKERS = (
    "alpha meadow", "bravo harbor", "cobalt parcel", "delta archive",
    "ember district", "frost ledger", "granite index", "hazel docket",
    "indigo survey", "juniper permit", "kestrel boundary", "lilac registry",
    "marble transfer", "nectar notice", "ochre easement", "pebble record",
    "quartz ownership", "raven classification", "saffron title", "topaz zoning",
    "umber acreage", "violet filing", "willow cadastral", "xenon archive",
    "yarrow parcel", "zephyr registry", "amber review", "birch reference",
    "copper mapping", "driftwood assessment",
)

DAY_MARKERS = (
    "alpine kiln mosaic", "birch lantern meadow", "cinder atlas quay",
    "delta copper orchard", "ember harbor slate", "fallow ivory bridge",
    "granite juniper field", "hazel cobalt terrace", "indigo maple vault",
    "juniper quartz avenue", "kestrel amber basin", "lilac bronze crossing",
    "marble cedar gallery", "nectar driftwood square", "ochre elm passage",
    "pebble frost meadow", "quartz greenway marker", "raven heather quay",
    "saffron iron terrace", "topaz willow crossing",
)

ATTACK_ROTATION = (
    {"SQL Injection": 4, "Code Injection": 3, "Other Attacks": 3},
    {"SQL Injection": 3, "Code Injection": 4, "Other Attacks": 3},
    {"SQL Injection": 3, "Code Injection": 3, "Other Attacks": 4},
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _encoded_request(value: str) -> str:
    encoded = quote(value, safe="-._~")
    raw_request = f"GET {TARGET_ROUTE}?query={encoded} HTTP/1.1\r\n\r\n"
    model_input_text, _, preprocessing_version = prepare_legacy_model_input(
        raw_request
    )
    if preprocessing_version != PREPROCESSING_VERSION:
        raise RuntimeError(
            "fixture generation produced an unexpected preprocessing version: "
            f"{preprocessing_version}"
        )
    return model_input_text


def _sample(
    *,
    day: int,
    ordinal: int,
    label: str,
    scenario_type: str,
    value: str,
) -> dict[str, Any]:
    model_input_text = _encoded_request(value)
    sample_id = (
        f"records-search-v2-day-{day:02d}-{scenario_type}-{ordinal:02d}"
    )
    return {
        "batch_day": day,
        "ground_truth_label": label,
        "is_synthetic": True,
        "model_input_hash": _sha256_text(model_input_text),
        "model_input_text": model_input_text,
        "preprocessing_version": PREPROCESSING_VERSION,
        "provenance_id": f"fixture:records-search-v2:{sample_id}",
        "request_method": TARGET_METHOD,
        "request_path": TARGET_ROUTE,
        "review_status": REVIEW_STATUS,
        "route_scope": "target_route",
        "sample_id": sample_id,
        "scenario_type": scenario_type,
        "source_type": SOURCE_TYPE,
    }


def _attack_counts(day: int) -> dict[str, int]:
    return dict(ATTACK_ROTATION[(day - 1) % len(ATTACK_ROTATION)])


def _build_day(day: int, *, seed: int) -> list[dict[str, Any]]:
    profile = DAY_PROFILES[(day - 1 + seed - SUPPORTED_SEED) % len(DAY_PROFILES)]
    rows: list[dict[str, Any]] = []
    ordinal = 1
    for template in ORDINARY_NORMAL_TEMPLATES:
        rows.append(
            _sample(
                day=day,
                ordinal=ordinal,
                label="Normal",
                scenario_type="ordinary_normal",
                value=template.format(
                    profile=profile,
                    marker=f"{ROW_MARKERS[ordinal - 1]} {DAY_MARKERS[day - 1]}",
                ),
            )
        )
        ordinal += 1
    for template in HARD_NORMAL_TEMPLATES:
        rows.append(
            _sample(
                day=day,
                ordinal=ordinal,
                label="Normal",
                scenario_type="hard_normal",
                value=template.format(
                    profile=profile,
                    marker=f"{ROW_MARKERS[ordinal - 1]} {DAY_MARKERS[day - 1]}",
                ),
            )
        )
        ordinal += 1

    attack_templates = {
        "SQL Injection": ("sql_injection", SQL_TEMPLATES),
        "Code Injection": ("code_injection", CODE_TEMPLATES),
        "Other Attacks": ("other_attack", OTHER_TEMPLATES),
    }
    for label, count in _attack_counts(day).items():
        scenario_type, templates = attack_templates[label]
        for index in range(count):
            value = templates[index].format(
                profile=profile,
                day=day,
                number=day + index + 7,
                marker=f"{ROW_MARKERS[ordinal - 1]} {DAY_MARKERS[day - 1]}",
            )
            rows.append(
                _sample(
                    day=day,
                    ordinal=ordinal,
                    label=label,
                    scenario_type=scenario_type,
                    value=value,
                )
            )
            ordinal += 1

    if len(rows) != DAILY_SAMPLE_COUNT:
        raise AssertionError(f"day {day} generated {len(rows)} rows")
    texts = [str(row["model_input_text"]) for row in rows]
    if len(texts) != len(set(texts)):
        raise ValueError(f"day {day} generated duplicate model inputs")
    return rows


def _validate_days(days: Iterable[int]) -> tuple[int, ...]:
    selected = tuple(sorted({int(day) for day in days}))
    if not selected or any(day < 1 or day > TOTAL_DAYS for day in selected):
        raise ValueError("days must contain values from 1 through 20")
    return selected


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> str:
    content = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for row in rows
    )
    path.write_text(content, encoding="utf-8", newline="\n")
    return sha256_file(path)


def generate_experiment_batches(
    experiment_root: Path | str,
    *,
    seed: int = SUPPORTED_SEED,
    days: Iterable[int] | None = None,
) -> dict[str, Any]:
    """Write reproducible route-specific fixture batches and their manifest."""

    if int(seed) != SUPPORTED_SEED:
        raise ValueError(f"seed must be the locked value {SUPPORTED_SEED}")
    selected_days = _validate_days(days or range(1, TOTAL_DAYS + 1))
    root = Path(experiment_root).expanduser().resolve()
    batch_root = root / "daily_batches" / "records_search_v2"
    batch_root.mkdir(parents=True, exist_ok=True)

    batch_hashes: dict[str, str] = {}
    batch_counts: dict[str, int] = {}
    label_counts: Counter[str] = Counter()
    scenario_counts: Counter[str] = Counter()
    for day in selected_days:
        rows = _build_day(day, seed=int(seed))
        relative_name = f"day_{day:02d}.jsonl"
        batch_hashes[relative_name] = _write_jsonl(
            batch_root / relative_name, rows
        )
        batch_counts[relative_name] = len(rows)
        label_counts.update(str(row["ground_truth_label"]) for row in rows)
        scenario_counts.update(str(row["scenario_type"]) for row in rows)

    unsigned_manifest: dict[str, Any] = {
        "manifest_version": "retraining-fixture-manifest.v2",
        "experiment_version": EXPERIMENT_VERSION,
        "generator_version": GENERATOR_VERSION,
        "seed": int(seed),
        "day_count": len(selected_days),
        "days": list(selected_days),
        "daily_sample_count": DAILY_SAMPLE_COUNT,
        "normal_samples_per_day": NORMAL_COUNT,
        "hard_normal_samples_per_day": HARD_NORMAL_COUNT,
        "attack_samples_per_day": ATTACK_COUNT,
        "target_method": TARGET_METHOD,
        "target_route": TARGET_ROUTE,
        "preprocessing_version": PREPROCESSING_VERSION,
        "historical_dataset_version": "v3_907k_cleaned",
        "golden_version": "golden-v2",
        "synthetic_fixture_only": True,
        "production_data": False,
        "label_distribution": dict(sorted(label_counts.items())),
        "scenario_distribution": dict(sorted(scenario_counts.items())),
        "batch_hashes": batch_hashes,
        "batch_counts": batch_counts,
    }
    manifest = {
        **unsigned_manifest,
        "total_sample_count": sum(batch_counts.values()),
        "manifest_sha256": canonical_json_sha256(
            {**unsigned_manifest, "total_sample_count": sum(batch_counts.values())}
        ),
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def validate_fixture_manifest(
    experiment_root: Path | str,
    *,
    expected_days: Iterable[int] | None = None,
    require_complete: bool = False,
) -> dict[str, Any]:
    """Verify the manifest and every generated batch before preflight use."""

    root = Path(experiment_root).expanduser().resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"fixture manifest does not exist: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("fixture manifest must be a JSON object")
    stored_hash = manifest.get("manifest_sha256")
    unsigned = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    if stored_hash != canonical_json_sha256(unsigned):
        raise ValueError("fixture manifest hash mismatch")
    required_contract = {
        "manifest_version": "retraining-fixture-manifest.v2",
        "experiment_version": EXPERIMENT_VERSION,
        "generator_version": GENERATOR_VERSION,
        "seed": SUPPORTED_SEED,
        "daily_sample_count": DAILY_SAMPLE_COUNT,
        "normal_samples_per_day": NORMAL_COUNT,
        "hard_normal_samples_per_day": HARD_NORMAL_COUNT,
        "attack_samples_per_day": ATTACK_COUNT,
        "target_method": TARGET_METHOD,
        "target_route": TARGET_ROUTE,
        "preprocessing_version": PREPROCESSING_VERSION,
        "historical_dataset_version": "v3_907k_cleaned",
        "golden_version": "golden-v2",
        "synthetic_fixture_only": True,
        "production_data": False,
    }
    mismatches = [
        key
        for key, expected in required_contract.items()
        if manifest.get(key) != expected
    ]
    if mismatches:
        raise ValueError(
            "fixture manifest contract mismatch: " + ", ".join(mismatches)
        )
    manifest_days = manifest.get("days")
    if not isinstance(manifest_days, list) or any(
        not isinstance(day, int) for day in manifest_days
    ):
        raise ValueError("fixture manifest days must be a list of integers")
    normalized_manifest_days = tuple(sorted(set(manifest_days)))
    if normalized_manifest_days != tuple(manifest_days):
        raise ValueError("fixture manifest days must be sorted and unique")
    if manifest.get("day_count") != len(manifest_days):
        raise ValueError("fixture manifest day_count does not match days")
    if require_complete and normalized_manifest_days != tuple(
        range(1, TOTAL_DAYS + 1)
    ):
        raise ValueError("fixture manifest must cover all 20 simulation days")
    requested_days = tuple(
        sorted({int(day) for day in expected_days})
    ) if expected_days is not None else normalized_manifest_days
    if not set(requested_days).issubset(set(normalized_manifest_days)):
        raise ValueError(
            "fixture manifest does not cover the requested simulation days"
        )
    batch_root = root / "daily_batches" / "records_search_v2"
    batch_hashes = manifest.get("batch_hashes")
    batch_counts = manifest.get("batch_counts")
    if not isinstance(batch_hashes, dict) or not isinstance(batch_counts, dict):
        raise ValueError("fixture manifest batch hashes/counts are missing")
    expected_names = {
        f"day_{day:02d}.jsonl" for day in normalized_manifest_days
    }
    if set(batch_hashes) != expected_names or set(batch_counts) != expected_names:
        raise ValueError("fixture manifest batch days do not match the contract")
    actual_names = {path.name for path in batch_root.glob("day_*.jsonl")}
    if actual_names != expected_names:
        raise ValueError("fixture directory contains unlisted or stale day files")
    label_distribution: Counter[str] = Counter()
    scenario_distribution: Counter[str] = Counter()
    total_sample_count = 0
    allowed_labels = {
        "Code Injection",
        "Normal",
        "Other Attacks",
        "SQL Injection",
    }
    allowed_scenarios = {
        "code_injection",
        "hard_normal",
        "ordinary_normal",
        "other_attack",
        "sql_injection",
    }
    for name, expected_hash in batch_hashes.items():
        path = batch_root / str(name)
        if not path.is_file():
            raise FileNotFoundError(f"fixture batch does not exist: {path}")
        actual_hash = sha256_file(path)
        if actual_hash != expected_hash:
            raise ValueError(f"fixture batch hash mismatch: {name}")
        rows = []
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"fixture batch {name} has invalid JSON at line {line_number}"
                ) from exc
            if not isinstance(row, dict):
                raise ValueError(f"fixture batch {name} rows must be objects")
            rows.append(row)
        line_count = len(rows)
        if line_count != int(batch_counts.get(name, -1)):
            raise ValueError(f"fixture batch count mismatch: {name}")
        day_number = int(Path(name).stem.split("_")[-1])
        for row in rows:
            required_row_values = {
                "batch_day": day_number,
                "is_synthetic": True,
                "preprocessing_version": PREPROCESSING_VERSION,
                "request_method": TARGET_METHOD,
                "request_path": TARGET_ROUTE,
                "review_status": REVIEW_STATUS,
                "route_scope": "target_route",
                "source_type": SOURCE_TYPE,
            }
            if row.get("batch_day") != required_row_values["batch_day"]:
                raise ValueError(f"fixture batch day mismatch: {name}")
            for key, expected in required_row_values.items():
                if key != "batch_day" and row.get(key) != expected:
                    raise ValueError(f"fixture row contract mismatch: {name}:{key}")
            if row.get("ground_truth_label") not in allowed_labels:
                raise ValueError(f"fixture row label is unsupported: {name}")
            if row.get("scenario_type") not in allowed_scenarios:
                raise ValueError(f"fixture row scenario is unsupported: {name}")
            model_input_text = row.get("model_input_text")
            if not isinstance(model_input_text, str) or not model_input_text:
                raise ValueError(f"fixture row model input is missing: {name}")
            if row.get("model_input_hash") != _sha256_text(model_input_text):
                raise ValueError(f"fixture row model input hash mismatch: {name}")
            label_distribution[str(row["ground_truth_label"])] += 1
            scenario_distribution[str(row.get("scenario_type"))] += 1
        total_sample_count += line_count
    if manifest.get("total_sample_count") != total_sample_count:
        raise ValueError("fixture manifest total_sample_count does not match batches")
    if manifest.get("label_distribution") != dict(sorted(label_distribution.items())):
        raise ValueError("fixture manifest label distribution does not match batches")
    if manifest.get("scenario_distribution") != dict(
        sorted(scenario_distribution.items())
    ):
        raise ValueError(
            "fixture manifest scenario distribution does not match batches"
        )
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=SUPPORTED_SEED)
    parser.add_argument("--days", nargs="+", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    manifest = generate_experiment_batches(
        args.output_dir,
        seed=args.seed,
        days=args.days,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
