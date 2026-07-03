import json

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
    result = smoke._check_audit_log(tmp_path / "missing.jsonl")

    assert result.status == "SKIP"
    assert result.required is False


def test_audit_jsonl_finds_latest_transaction_id(tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text(
        '{"transaction":{"unique_id":"tx-old"}}\n'
        '{"transaction":{"unique_id":"tx-latest"}}\n',
        encoding="utf-8",
    )

    result = smoke._check_audit_log(audit_log)

    assert result.status == "PASS"
    assert result.details == "transaction_id present"


def test_audit_jsonl_non_object_entry_returns_controlled_failure(tmp_path):
    audit_log = tmp_path / "modsec_audit.jsonl"
    audit_log.write_text('["untrusted", "entry"]\n', encoding="utf-8")

    result = smoke._check_audit_log(audit_log)

    assert result.status == "FAIL"
    assert result.details == "latest audit JSONL entry is unavailable or invalid"
