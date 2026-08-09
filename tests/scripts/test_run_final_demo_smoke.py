import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

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

    exit_code = smoke.main(["--mode", "backend", "--base-url", "http://backend.test"])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "FAIL" in output


def test_json_output_is_parseable(monkeypatch, capsys):
    monkeypatch.setattr(smoke, "_request_status", lambda url, timeout: 200)

    exit_code = smoke.main(
        ["--mode", "backend", "--base-url", "http://backend.test", "--json"]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["mode"] == "backend"
    assert payload["passed"] is True
    assert all(check["status"] == "PASS" for check in payload["checks"])


def test_timeout_returns_controlled_failure_without_traceback(monkeypatch, capsys):
    def _timeout(url, timeout):
        raise TimeoutError("timed out while connecting")

    monkeypatch.setattr(smoke, "_request_status", _timeout)

    exit_code = smoke.main(["--mode", "backend", "--base-url", "http://backend.test"])

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

    exit_code = smoke.main(
        ["--mode", "backend", "--base-url", "http://backend.test", "--json"]
    )

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

    exit_code = smoke.main(["--mode", "backend", "--base-url", "http://backend.test"])

    assert exit_code == 0
    assert requested_urls
    assert all("8089" not in url for url in requested_urls)
    assert all("/records/search" not in url for url in requested_urls)


def test_missing_audit_jsonl_fails_waf_chain_proof(tmp_path):
    result = smoke._check_audit_log(
        tmp_path / "missing.jsonl",
        start_offset=0,
        expected_path="/records/search",
        expected_status=200,
    )

    assert result.status == "FAIL"
    assert result.required is True


def test_audit_cursor_ignores_invalid_historical_bytes(tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    historical = b"\x80\x81historical-invalid\n"
    audit_log.write_bytes(historical)
    start_offset = audit_log.stat().st_size
    current = {
        "transaction": {
            "unique_id": "tx-current-offset",
            "request": {"uri": "/records/search?query=Maple"},
            "response": {"http_code": 200},
        }
    }
    with audit_log.open("ab") as handle:
        handle.write(json.dumps(current).encode("utf-8") + b"\n")

    result = smoke._check_audit_log(
        audit_log,
        start_offset=start_offset,
        expected_path="/records/search",
        expected_status=200,
    )

    assert result.status == "PASS"
    assert result.transaction_id == "tx-current-offset"


def test_audit_cursor_rejects_invalid_new_event(tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text("{\"historical\": true}\n", encoding="utf-8")
    start_offset = audit_log.stat().st_size
    audit_log.write_bytes(audit_log.read_bytes() + b"\x80\x81{not-json}\n")

    result = smoke._check_audit_log(
        audit_log,
        start_offset=start_offset,
        expected_path="/records/search",
        expected_status=200,
    )

    assert result.status == "FAIL"
    assert "new audit" in result.details.lower()


def test_demo_target_smoke_does_not_put_run_id_in_requests(monkeypatch):
    requested_urls = []

    def _request(url, timeout):
        requested_urls.append(url)
        return 403 if "UNION" in url else 200

    monkeypatch.setattr(smoke, "_request_status", _request)
    monkeypatch.setattr(smoke, "_audit_log_offset", lambda path: 0)
    monkeypatch.setattr(
        smoke,
        "_wait_for_audit_log",
        lambda **kwargs: smoke.CheckResult(
            name=kwargs["check_name"],
            status="PASS",
            details="correlated",
            correlated=True,
            transaction_id=(
                "tx-normal"
                if kwargs["expected_status"] == 200
                else "tx-attack"
            ),
        ),
    )
    monkeypatch.setattr(
        smoke,
        "_backend_lookup_check",
        lambda **kwargs: smoke.CheckResult(
            name=kwargs["check_name"],
            status="PASS",
            details="correlated",
            correlated=True,
            transaction_id=kwargs["transaction_id"],
        ),
    )

    checks = smoke.run_checks(
        "demo-target-8089",
        base_url="http://localhost:8089",
        timeout=5,
        audit_log=None,
        marker="CYBERTRACE_SMOKE_not-in-request",
        started_at=datetime.now(timezone.utc),
        require_backend_lookup=True,
        audit_start_offset=0,
    )

    assert all("CYBERTRACE_SMOKE_not-in-request" not in url for url in requested_urls)
    assert {check.name for check in checks} >= {
        "demo_target_normal",
        "demo_target_attack",
        "audit_transaction_normal",
        "audit_transaction_attack",
        "backend_transaction_lookup_normal",
        "backend_transaction_lookup_attack",
    }


def test_json_summary_aggregates_named_demo_chain_correlations(monkeypatch, capsys):
    monkeypatch.setattr(
        smoke,
        "run_checks",
        lambda *args, **kwargs: [
            smoke.CheckResult(
                name="demo_target_home",
                status="PASS",
                details="HTTP 200",
            ),
            smoke.CheckResult(
                name="audit_transaction_normal",
                status="PASS",
                details="correlated",
                correlated=True,
                transaction_id="tx-normal",
            ),
            smoke.CheckResult(
                name="audit_transaction_attack",
                status="PASS",
                details="correlated",
                correlated=True,
                transaction_id="tx-attack",
            ),
            smoke.CheckResult(
                name="backend_transaction_lookup_normal",
                status="PASS",
                details="correlated",
                correlated=True,
                transaction_id="tx-normal",
            ),
            smoke.CheckResult(
                name="backend_transaction_lookup_attack",
                status="PASS",
                details="correlated",
                correlated=True,
                transaction_id="tx-attack",
            ),
        ],
    )

    exit_code = smoke.main(["--mode", "demo-target-8089", "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["audit_correlated"] is True
    assert payload["backend_correlated"] is True


def test_backend_default_health_check_uses_container_network(monkeypatch):
    calls = []

    def _run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(stdout='{"health":200,"api_health":200}\n')

    monkeypatch.setattr(smoke.subprocess, "run", _run)

    checks = smoke._backend_internal_health_checks(timeout=5)

    assert all(check.status == "PASS" for check in checks)
    assert calls
    assert calls[0][0:4] == ["docker", "compose", "exec", "-T"]
    assert "backend" in calls[0]


def test_backend_health_command_is_anchored_to_repository_root(monkeypatch):
    calls = []

    def _run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout='{"health":200,"api_health":200}\n')

    monkeypatch.setattr(smoke.subprocess, "run", _run)

    smoke._run_backend_internal_health(timeout=5)

    assert calls[0][1]["cwd"] == smoke.REPO_ROOT


def test_backend_internal_health_uses_requested_timeout(monkeypatch):
    calls = []

    def _run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout='{"health":200,"api_health":200}\n')

    monkeypatch.setattr(smoke.subprocess, "run", _run)

    smoke._run_backend_internal_health(timeout=2.5)

    command = calls[0][0][-1]
    assert "timeout=2.5" in command
    assert calls[0][1]["timeout"] == 6.0


def test_backend_lookup_command_is_anchored_to_repository_root(monkeypatch):
    calls = []

    def _run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout='{"found":false}\n')

    monkeypatch.setattr(smoke.subprocess, "run", _run)

    smoke._run_backend_lookup("tx-current")

    assert calls[0][1]["cwd"] == smoke.REPO_ROOT


def test_audit_jsonl_finds_new_route_status_transaction_id(tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        '{"transaction":{"unique_id":"tx-current","request":'
        '{"uri":"/records/search?query=Maple"},"response":{"http_code":200}}}\n'
        '{"transaction":{"unique_id":"tx-unrelated"}}\n',
        encoding="utf-8",
    )

    result = smoke._check_audit_log(
        audit_log,
        start_offset=0,
        expected_path="/records/search",
        expected_status=200,
    )

    assert result.status == "PASS"
    assert result.transaction_id == "tx-current"
    assert result.correlated is True


def test_audit_jsonl_requires_probe_query_for_correlation(tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        '{"transaction":{"unique_id":"tx-unrelated","request":'
        '{"uri":"/records/search?query=Other"},"response":{"http_code":200}}}\n',
        encoding="utf-8",
    )

    result = smoke._check_audit_log(
        audit_log,
        start_offset=0,
        expected_path="/records/search",
        expected_query="query=Maple",
        expected_status=200,
    )

    assert result.status == "FAIL"
    assert result.correlated is False


def test_historical_audit_line_before_cursor_is_not_reused(tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        '{"transaction":{"unique_id":"tx-old","request":'
        '{"uri":"/records/search?query=Maple"},"response":{"http_code":200}}}\n',
        encoding="utf-8",
    )

    result = smoke._check_audit_log(
        audit_log,
        start_offset=audit_log.stat().st_size,
        expected_path="/records/search",
        expected_status=200,
    )

    assert result.status == "FAIL"
    assert result.correlated is False
    assert result.transaction_id is None


def test_audit_jsonl_non_object_entry_returns_controlled_failure(tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text('["untrusted", "entry"]\n', encoding="utf-8")

    result = smoke._check_audit_log(
        audit_log,
        start_offset=0,
        expected_path="/records/search",
        expected_status=200,
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
            details="new audit event was not found",
            correlated=False,
        ),
        smoke.CheckResult(
            name="audit_transaction",
            status="PASS",
            details="new audit event correlated",
            correlated=True,
            transaction_id="tx-current",
        ),
    ]
    sleeps: list[float] = []
    monkeypatch.setattr(
        smoke,
        "_check_audit_log",
        lambda **kwargs: responses.pop(0),
    )
    monkeypatch.setattr(smoke.time, "sleep", sleeps.append)

    result = smoke._wait_for_audit_log(
        tmp_path / "modsec_audit.jsonl",
        start_offset=0,
        expected_path="/records/search",
        expected_status=200,
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
        "request_path": "/records/search",
    }
    mismatched = {
        "found": True,
        "transaction_id": "tx-current",
        "timestamp": (started_at + timedelta(seconds=1)).isoformat(),
        "request_path": "/transactions/status",
    }

    stale_result = smoke._validate_backend_lookup(
        stale,
        transaction_id="tx-current",
        started_at=started_at,
        expected_path="/records/search",
    )
    mismatch_result = smoke._validate_backend_lookup(
        mismatched,
        transaction_id="tx-current",
        started_at=started_at,
        expected_path="/records/search",
    )

    assert stale_result.status == "FAIL"
    assert mismatch_result.status == "FAIL"


def test_backend_lookup_failure_reports_safe_policy_mismatch():
    started_at = datetime.now(timezone.utc)
    result = smoke._validate_backend_lookup(
        {
            "found": True,
            "transaction_id": "tx-current",
            "timestamp": started_at.isoformat(),
            "request_path": "/records/search",
            "prediction": "Other Attacks",
            "action_taken": "THROTTLED",
        },
        transaction_id="tx-current",
        started_at=started_at,
        expected_path="/records/search",
        expected_prediction="Normal",
        expected_action="ALLOWED",
    )

    assert result.status == "FAIL"
    assert "prediction=Other Attacks" in result.details
    assert "action=THROTTLED" in result.details


def test_backend_lookup_accepts_current_timestamp_with_second_precision():
    started_at = datetime(2026, 7, 4, 21, 8, 54, 849572, tzinfo=timezone.utc)
    payload = {
        "found": True,
        "transaction_id": "tx-current",
        "timestamp": "2026-07-04T21:08:54Z",
        "request_path": "/records/search",
    }

    result = smoke._validate_backend_lookup(
        payload,
        transaction_id="tx-current",
        started_at=started_at,
        expected_path="/records/search",
    )

    assert result.status == "PASS"
    assert result.correlated is True


def test_backend_lookup_waits_for_bridge_ingest(monkeypatch):
    started_at = datetime.now(timezone.utc)
    responses = [
        {"found": False, "transaction_id": "tx-current"},
        {
            "found": True,
            "transaction_id": "tx-current",
            "timestamp": started_at.isoformat(),
            "request_path": "/records/search",
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
        started_at=started_at,
        required=True,
        expected_path="/records/search",
    )

    assert result.status == "PASS"
    assert result.correlated is True
    assert sleeps == [smoke.BACKEND_LOOKUP_RETRY_INTERVAL_SECONDS]


def test_require_backend_lookup_fails_when_lookup_is_unavailable(
    monkeypatch, tmp_path, capsys
):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        json.dumps(
            {
                "transaction": {
                    "unique_id": "tx-required",
                    "request": {"uri": "/api/health?id=17%27%20OR%2017%3D17--"},
                    "response": {"http_code": 403},
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(smoke, "_audit_log_offset", lambda path: 0)
    monkeypatch.setattr(
        smoke,
        "_request_status",
        lambda url, timeout: 403 if "/api/health?id=" in url else 200,
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
    assert payload["audit_correlated"] is True
    assert payload["backend_correlated"] is False
    assert payload["failures"]
    assert "must-not-leak" not in json.dumps(payload)


def test_optional_backend_lookup_is_warn_not_full_proof(
    monkeypatch, tmp_path, capsys
):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        json.dumps(
            {
                "transaction": {
                    "unique_id": "tx-optional",
                    "request": {"uri": "/api/health?id=17%27%20OR%2017%3D17--"},
                    "response": {"http_code": 403},
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(smoke, "_audit_log_offset", lambda path: 0)
    monkeypatch.setattr(
        smoke,
        "_request_status",
        lambda url, timeout: 403 if "/api/health?id=" in url else 200,
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
