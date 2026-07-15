import json
from pathlib import Path

from scripts.modsecurity_replay_harness import (
    DEFAULT_HELDOUT_JSON,
    DEFAULT_QUARANTINE_JSON,
    _lookup_downstream,
    _post_ingest_event,
    build_report_rows,
    build_waf_ingest_payload,
    detect_modsecurity_events,
    load_default_samples,
    normalize_sample_row,
    write_reports,
)


class _Response:
    status = 200

    def __init__(self, body: bytes = b'{"found":true}') -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self) -> bytes:
        return self._body


def test_replay_submission_uses_dedicated_waf_key(monkeypatch) -> None:
    captured = {}

    def _urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", _urlopen)

    status = _post_ingest_event(
        {"transaction_id": "tx-1"},
        endpoint="http://backend/api/internal/waf-events",
        waf_ingest_api_key="dedicated-waf-key",
        timeout=7,
    )

    assert status == 200
    assert captured == {
        "authorization": "Bearer dedicated-waf-key",
        "timeout": 7,
    }


def test_replay_lookup_keeps_general_internal_key(monkeypatch) -> None:
    captured = {}

    def _urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", _urlopen)

    found, _body = _lookup_downstream(
        "tx-1",
        endpoint="http://backend/api/internal/waf-events",
        internal_api_key="general-internal-key",
        timeout=9,
    )

    assert found is True
    assert captured == {
        "authorization": "Bearer general-internal-key",
        "timeout": 9,
    }


def test_default_sample_paths_resolve_under_repo_data_directory():
    expected_root = Path(__file__).resolve().parents[2] / "data" / "processed" / "v3_907k_cleaned" / "sample_exports"

    assert DEFAULT_HELDOUT_JSON == expected_root / "heldout_test_15.json"
    assert DEFAULT_QUARANTINE_JSON == expected_root / "quarantine_15.json"


def test_load_default_samples_combines_two_exports(tmp_path: Path):
    heldout = tmp_path / "heldout_test_15.json"
    quarantine = tmp_path / "quarantine_15.json"

    heldout.write_text(
        json.dumps(
            [
                {
                    "request_http_method": "GET",
                    "request_http_request": "/a",
                    "request_body": "",
                    "payload_hash": "h1",
                }
            ]
        ),
        encoding="utf-8",
    )
    quarantine.write_text(
        json.dumps(
            [
                {
                    "request_http_method": "POST",
                    "request_http_request": "/b",
                    "request_body": "x=1",
                    "payload_hash": "h2",
                }
            ]
        ),
        encoding="utf-8",
    )

    rows = load_default_samples(heldout, quarantine)

    assert len(rows) == 2
    assert rows[0]["request_http_request"] == "/a"
    assert rows[1]["request_http_request"] == "/b"


def test_normalize_sample_row_returns_skip_reason_for_missing_path():
    replay = normalize_sample_row(
        {
            "request_http_method": "GET",
            "request_http_request": "",
            "request_body": "",
        },
        replay_tx="tx-001",
    )

    assert replay.skip_reason is not None
    assert "path" in replay.skip_reason.lower()


def test_normalize_sample_row_parses_path_query_and_body():
    replay = normalize_sample_row(
        {
            "request_http_method": "POST",
            "request_http_request": "/api/login?x=1",
            "request_body": "user=admin",
        },
        replay_tx="tx-002",
    )

    assert replay.skip_reason is None
    assert replay.method == "POST"
    assert replay.path == "/api/login"
    assert replay.query_string == "x=1"
    assert replay.body == "user=admin"


def test_normalize_sample_row_skips_templated_path_controls():
    replay = normalize_sample_row(
        {
            "request_http_method": "GET",
            "request_http_request": "/api/search/{{ data.url }}",
            "request_body": "",
        },
        replay_tx="tx-ctl",
    )

    assert replay.skip_reason is not None
    assert "unreplayable" in replay.skip_reason


def test_detect_modsecurity_events_matches_replay_header():
    logs = "\n".join(
        [
            "modsecurity-1  | {\"transaction\":{\"request\":{\"headers\":{\"X-Replay-Tx\":\"tx-keep\"}},\"messages\":[{\"details\":{\"ruleId\":\"942100\"},\"message\":\"SQL Injection\"}]}}",
            "modsecurity-1  | {\"transaction\":{\"request\":{\"headers\":{\"X-Replay-Tx\":\"tx-drop\"}},\"messages\":[]}}",
        ]
    )

    detected = detect_modsecurity_events(logs, replay_tx="tx-keep")

    assert detected.detected is True
    assert detected.transaction_id is not None
    assert "942100" in detected.rule_ids


def test_build_waf_ingest_payload_uses_detection_evidence_fields():
    replay = normalize_sample_row(
        {
            "request_http_method": "GET",
            "request_http_request": "/api/health?x=1",
            "request_body": "",
        },
        replay_tx="tx-003",
    )

    logs = "modsecurity-1  | {\"transaction\":{\"client_ip\":\"203.0.113.10\",\"time_stamp\":\"Tue Mar 24 07:54:07 2026\",\"unique_id\":\"u-1\",\"request\":{\"headers\":{\"X-Replay-Tx\":\"tx-003\",\"User-Agent\":\"ua\"}},\"messages\":[{\"details\":{\"ruleId\":\"942100\",\"tags\":[\"attack-sqli\"]},\"message\":\"SQL Injection Attack\"}]}}}"
    detection = detect_modsecurity_events(logs, replay_tx="tx-003")

    payload = build_waf_ingest_payload(replay, detection)

    assert payload["transaction_id"] == "u-1"
    assert payload["request_path"] == "/api/health"
    assert payload["query_string"] == "x=1"
    assert payload["crs_rule_ids"] == ["942100"]


def test_build_report_rows_counts_detection_only_with_response_and_evidence():
    rows = build_report_rows(
        [
            {
                "row_index": 1,
                "replay_tx": "tx-1",
                "response_status": 403,
                "response_ok": True,
                "modsec_detected": True,
                "downstream_stored": True,
                "skip_reason": None,
                "failure": None,
            },
            {
                "row_index": 2,
                "replay_tx": "tx-2",
                "response_status": None,
                "response_ok": False,
                "modsec_detected": True,
                "downstream_stored": False,
                "skip_reason": None,
                "failure": "timeout",
            },
        ]
    )

    assert rows.summary["total"] == 2
    assert rows.summary["replayed"] == 2
    assert rows.summary["detected_by_modsec"] == 1
    assert rows.summary["downstream_stored"] == 1
    assert rows.summary["failures"] == 1


def test_write_reports_creates_summary_json_csv_and_raw_artifacts(tmp_path: Path):
    output_dir = tmp_path / "reports"
    response_artifacts = {
        "tx-1": "HTTP 403\\nblocked",
    }
    modsec_artifacts = {
        "tx-1": '{"transaction":{"messages":[{"message":"SQL Injection"}]}}',
    }

    report = build_report_rows(
        [
            {
                "row_index": 1,
                "replay_tx": "tx-1",
                "response_status": 403,
                "response_ok": True,
                "modsec_detected": True,
                "downstream_stored": True,
                "skip_reason": None,
                "failure": None,
            }
        ]
    )

    write_reports(
        output_dir=output_dir,
        report=report,
        response_artifacts=response_artifacts,
        modsec_artifacts=modsec_artifacts,
    )

    assert (output_dir / "summary.txt").exists()
    assert (output_dir / "report.json").exists()
    assert (output_dir / "report.csv").exists()
    assert (output_dir / "responses" / "tx-1.txt").exists()
    assert (output_dir / "modsecurity" / "tx-1.log").exists()
