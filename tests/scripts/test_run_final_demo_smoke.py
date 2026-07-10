import json
from datetime import datetime, timedelta, timezone

import scripts.run_final_demo_smoke as smoke


def test_successful_backend_checks_emit_pass(monkeypatch, capsys):
    monkeypatch.setattr(smoke, "_request_status", lambda url, timeout: 200)

    exit_code = smoke.main(
        ["--mode", "backend", "--base-url", "http://backend.test"]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "backend_health: PASS" in output
    assert "backend_api_health: PASS" in output


def test_failed_check_emits_fail_and_nonzero_exit(monkeypatch, capsys):
    monkeypatch.setattr(smoke, "_request_status", lambda url, timeout: 503)

    exit_code = smoke.main(
        ["--mode", "backend", "--base-url", "http://backend.test"]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL" in output


def test_json_output_is_parseable(monkeypatch, capsys):
    monkeypatch.setattr(smoke, "_request_status", lambda url, timeout: 200)

    exit_code = smoke.main(["--mode", "backend", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["mode"] == "backend"
    assert payload["passed"] is True
    assert all(check["status"] == "PASS" for check in payload["checks"])


def test_timeout_returns_controlled_failure_without_traceback(monkeypatch, capsys):
    def _timeout(url, timeout):
        raise TimeoutError("timed out while connecting")

    monkeypatch.setattr(smoke, "_request_status", _timeout)

    exit_code = smoke.main(["--mode", "backend"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "FAIL" in captured.out
    assert "service unavailable or timed out" in captured.out
    assert "Traceback" not in captured.out
    assert captured.err == ""


def test_secret_like_exception_values_and_header_names_are_not_emitted(
    monkeypatch, capsys
):
    def _secret_failure(url, timeout):
        raise RuntimeError(
            "Authorization: Bearer bearer-secret "
            "API_SECRET_KEY=api-secret "
            "DATABASE_URL=postgresql://user:db-secret@example.test/app"
        )

    monkeypatch.setattr(smoke, "_request_status", _secret_failure)

    exit_code = smoke.main(["--mode", "backend", "--json"])

    output = capsys.readouterr().out
    assert exit_code == 1
    for forbidden in (
        "Authorization",
        "bearer-secret",
        "API_SECRET_KEY",
        "api-secret",
        "DATABASE_URL",
        "db-secret",
    ):
        assert forbidden not in output


def test_backend_mode_does_not_run_demo_target_checks(monkeypatch):
    requested_urls = []

    def _capture_request(url, timeout):
        requested_urls.append(url)
        return 200

    monkeypatch.setattr(smoke, "_request_status", _capture_request)

    exit_code = smoke.main(["--mode", "backend"])

    assert exit_code == 0
    assert requested_urls
    assert all("8089" not in url for url in requested_urls)
    assert all("/records/search" not in url for url in requested_urls)


def test_missing_audit_jsonl_is_skipped_gracefully(tmp_path):
    result = smoke._check_audit_log(
        tmp_path / "missing.jsonl", "CYBERTRACE_SMOKE_missing"
    )

    assert result.status == "SKIP"
    assert result.required is False


def test_audit_jsonl_finds_marker_correlated_transaction_id(tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        '{"transaction":{"unique_id":"tx-current","request":'
        '{"uri":"/search?q=CYBERTRACE_SMOKE_current"}}}\n'
        '{"transaction":{"unique_id":"tx-unrelated"}}\n',
        encoding="utf-8",
    )

    result = smoke._check_audit_log(audit_log, "CYBERTRACE_SMOKE_current")

    assert result.status == "PASS"
    assert result.transaction_id == "tx-current"
    assert result.correlated is True


def test_stale_latest_audit_line_without_current_marker_fails(tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        '{"transaction":{"unique_id":"tx-old","request":'
        '{"uri":"/search?q=CYBERTRACE_SMOKE_old"}}}\n',
        encoding="utf-8",
    )

    result = smoke._check_audit_log(audit_log, "CYBERTRACE_SMOKE_current")

    assert result.status == "FAIL"
    assert result.correlated is False
    assert result.transaction_id is None


def test_audit_jsonl_non_object_entry_returns_controlled_failure(tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text('["untrusted", "entry"]\n', encoding="utf-8")

    result = smoke._check_audit_log(
        audit_log, "CYBERTRACE_SMOKE_current"
    )

    assert result.status == "FAIL"
    assert result.correlated is False


def test_audit_lookup_waits_for_current_modsecurity_record(
    monkeypatch, tmp_path
):
    responses = [
        smoke.CheckResult(
            name="audit_transaction",
            status="FAIL",
            details="current smoke marker was not found in the audit JSONL",
            correlated=False,
        ),
        smoke.CheckResult(
            name="audit_transaction",
            status="PASS",
            details="current marker and transaction_id are correlated",
            correlated=True,
            transaction_id="tx-current",
        ),
    ]
    sleeps: list[float] = []
    monkeypatch.setattr(
        smoke,
        "_check_audit_log",
        lambda path, marker: responses.pop(0),
    )
    monkeypatch.setattr(smoke.time, "sleep", sleeps.append)

    result = smoke._wait_for_audit_log(
        tmp_path / "modsec_audit.jsonl",
        "CYBERTRACE_SMOKE_current",
    )

    assert result.status == "PASS"
    assert result.transaction_id == "tx-current"
    assert sleeps == [smoke.AUDIT_LOOKUP_RETRY_INTERVAL_SECONDS]


def test_backend_lookup_rejects_stale_or_mismatched_records():
    started_at = datetime.now(timezone.utc)
    stale = {
        "found": True,
        "transaction_id": "tx-current",
        "timestamp": (started_at - timedelta(seconds=1)).isoformat(),
        "query_string": "q=CYBERTRACE_SMOKE_current",
    }
    mismatched = {
        "found": True,
        "transaction_id": "tx-current",
        "timestamp": (started_at + timedelta(seconds=1)).isoformat(),
        "query_string": "q=CYBERTRACE_SMOKE_other",
    }

    stale_result = smoke._validate_backend_lookup(
        stale,
        transaction_id="tx-current",
        marker="CYBERTRACE_SMOKE_current",
        started_at=started_at,
    )
    mismatch_result = smoke._validate_backend_lookup(
        mismatched,
        transaction_id="tx-current",
        marker="CYBERTRACE_SMOKE_current",
        started_at=started_at,
    )

    assert stale_result.status == "FAIL"
    assert mismatch_result.status == "FAIL"


def test_backend_lookup_accepts_current_marker_with_second_precision_timestamp():
    started_at = datetime(2026, 7, 4, 21, 8, 54, 849572, tzinfo=timezone.utc)
    payload = {
        "found": True,
        "transaction_id": "tx-current",
        "timestamp": "2026-07-04T21:08:54Z",
        "query_string": "q=CYBERTRACE_SMOKE_current",
    }

    result = smoke._validate_backend_lookup(
        payload,
        transaction_id="tx-current",
        marker="CYBERTRACE_SMOKE_current",
        started_at=started_at,
    )

    assert result.status == "PASS"
    assert result.correlated is True


def test_backend_lookup_waits_for_bridge_ingest(monkeypatch):
    marker = "CYBERTRACE_SMOKE_current"
    started_at = datetime.now(timezone.utc)
    responses = [
        {"found": False, "transaction_id": "tx-current"},
        {
            "found": True,
            "transaction_id": "tx-current",
            "timestamp": started_at.isoformat(),
            "query_string": f"q={marker}",
        },
    ]
    sleeps: list[float] = []
    monkeypatch.setattr(
        smoke,
        "_run_backend_lookup",
        lambda transaction_id: responses.pop(0),
    )
    monkeypatch.setattr(smoke.time, "sleep", sleeps.append)

    result = smoke._backend_lookup_check(
        transaction_id="tx-current",
        marker=marker,
        started_at=started_at,
        required=True,
    )

    assert result.status == "PASS"
    assert result.correlated is True
    assert sleeps == [smoke.BACKEND_LOOKUP_RETRY_INTERVAL_SECONDS]


def test_require_backend_lookup_fails_when_lookup_is_unavailable(
    monkeypatch, tmp_path, capsys
):
    marker = "CYBERTRACE_SMOKE_required"
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        json.dumps(
            {
                "transaction": {
                    "unique_id": "tx-required",
                    "request": {"uri": f"/search?q={marker}"},
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(smoke, "_new_marker", lambda: marker)
    monkeypatch.setattr(
        smoke,
        "_request_status",
        lambda url, timeout: 403 if marker in url else 200,
    )
    monkeypatch.setattr(
        smoke,
        "_run_backend_lookup",
        lambda transaction_id: (_ for _ in ()).throw(
            RuntimeError("API_SECRET_KEY=must-not-leak")
        ),
    )

    exit_code = smoke.main(
        [
            "--mode",
            "waf-8088",
            "--audit-log",
            str(audit_log),
            "--require-backend-lookup",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert payload["status"] == "FAIL"
    assert payload["marker"] == marker
    assert payload["audit_correlated"] is True
    assert payload["backend_correlated"] is False
    assert payload["failures"]
    assert "must-not-leak" not in json.dumps(payload)


def test_optional_backend_lookup_is_warn_not_full_proof(
    monkeypatch, tmp_path, capsys
):
    marker = "CYBERTRACE_SMOKE_optional"
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        json.dumps(
            {
                "transaction": {
                    "unique_id": "tx-optional",
                    "request": {"uri": f"/search?q={marker}"},
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(smoke, "_new_marker", lambda: marker)
    monkeypatch.setattr(
        smoke,
        "_request_status",
        lambda url, timeout: 403 if marker in url else 200,
    )

    exit_code = smoke.main(
        [
            "--mode",
            "waf-8088",
            "--audit-log",
            str(audit_log),
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["status"] == "WARN"
    assert payload["audit_correlated"] is True
    assert payload["backend_correlated"] is False
    assert payload["warnings"]
