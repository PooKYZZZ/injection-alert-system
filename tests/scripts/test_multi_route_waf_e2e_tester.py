from __future__ import annotations

from pathlib import Path

from scripts.multi_route_waf_e2e_tester import (
    ROUTES,
    REPORT_FIELDS,
    _observed_http_effect,
    build_scenarios,
    validate_origin,
)
from scripts.search_records_attack_catalog import load_catalog


ROOT = Path(__file__).resolve().parents[2]
CATALOG = load_catalog(ROOT / "scripts/fixtures/search_records_attack_catalog.json")


def test_route_matrix_covers_the_expected_get_and_post_surfaces() -> None:
    assert sum(route.method == "GET" for route in ROUTES) == 8
    assert sum(route.method == "POST" for route in ROUTES) == 5
    assert {route.route for route in ROUTES if route.attack_enabled} == {
        "search_records",
        "track_status",
        "record_detail",
        "request_copy_page",
        "book_appointment",
        "support_desk",
        "demo_login_submit",
        "request_copy_submit",
        "comments_submit",
    }


def test_route_matrix_builds_distinct_normal_sqli_and_code_scenarios() -> None:
    scenarios = build_scenarios(CATALOG, run_id="test-run-id")
    assert len(scenarios) == 31
    assert len({scenario.test_id for scenario in scenarios}) == len(scenarios)
    assert sum(scenario.scenario == "normal" for scenario in scenarios) == 13
    assert sum(scenario.scenario == "sql_injection" for scenario in scenarios) == 9
    assert sum(scenario.scenario == "code_injection" for scenario in scenarios) == 9
    assert all(scenario.expected_prediction for scenario in scenarios)


def test_report_schema_does_not_include_submitted_values() -> None:
    assert "payload" not in REPORT_FIELDS
    assert "query" not in REPORT_FIELDS
    assert "form" not in REPORT_FIELDS
    assert "password" not in REPORT_FIELDS
    assert "ml_action_recommendation" in REPORT_FIELDS
    assert "observed_http_effect" in REPORT_FIELDS
    login_attack = next(
        scenario
        for scenario in build_scenarios(CATALOG, run_id="privacy-run")
        if scenario.route.route == "demo_login_submit"
        and scenario.scenario == "sql_injection"
    )
    assert login_attack.form is not None
    assert "password" in login_attack.form


def test_report_separates_observed_http_effect_from_policy_recommendation() -> None:
    assert _observed_http_effect(403, ["942100", "949110"]) == "MODSECURITY_BLOCKED"
    assert _observed_http_effect(403, []) == "HTTP_FORBIDDEN_WITHOUT_CRS_EVIDENCE"
    assert _observed_http_effect(429, []) == "HTTP_THROTTLED"
    assert _observed_http_effect(303, []) == "APPLICATION_REDIRECT"
    assert _observed_http_effect(200, []) == "NO_HTTP_BLOCK_OR_THROTTLE_OBSERVED"


def test_runner_accepts_only_explicit_local_http_origins() -> None:
    assert validate_origin(
        "http://demo-target-modsecurity:8080",
        allowed_hosts={"demo-target-modsecurity"},
        label="origin",
    ) == "http://demo-target-modsecurity:8080"
    for value in (
        "https://demo-target-modsecurity:8080",
        "http://example.com:8080",
        "http://demo-target-modsecurity",
        "http://user@demo-target-modsecurity:8080",
    ):
        try:
            validate_origin(
                value,
                allowed_hosts={"demo-target-modsecurity"},
                label="origin",
            )
        except ValueError:
            continue
        raise AssertionError(f"unexpectedly accepted non-local endpoint: {value}")
