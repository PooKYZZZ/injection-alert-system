from __future__ import annotations

import asyncio
import json
import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.e2e.pr7_block3_artifacts import (
    require_pinned_compose_images,
    require_portal_commit,
    verify_model_lock,
)

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_FILES = (
    ROOT / "docker-compose.yml",
    ROOT / "docker-compose.test.yml",
    ROOT / "docker-compose.pr7-block3.yml",
)
SOURCE_A = "172.31.7.10"
SOURCE_B = "172.31.7.11"
PATH = "/records/search"
ATTACK_PATH = "/records/search?id=1%20OR%201=1--"
MODEL_RUN_DIR = ROOT / (
    "ml_model/model_registry/staging/"
    "distilbert_v3_907k_cleaned_20260312_133755"
)
PORTAL_PATH = Path(
    os.environ.get(
        "DEMO_PORTAL_CONTEXT",
        str(ROOT.parent.parent / "land-records-portal"),
    )
).resolve()


def _run(command: list[str], *, timeout: float = 180) -> str:
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout[-5000:]}\n"
            f"stderr:\n{result.stderr[-5000:]}"
        )
    return result.stdout.strip()


def _compose(project: str, override: Path, *args: str) -> list[str]:
    command = ["docker", "compose", "--project-name", project]
    for compose_file in COMPOSE_FILES:
        command.extend(["-f", str(compose_file)])
    command.extend(["-f", str(override), "--profile", "pr7-block3"])
    command.extend(args)
    return command


def _capture_timing_artifact(project: str, override: Path) -> None:
    """Persist bounded WAF timing fields before disposable cleanup removes logs."""
    destination = os.environ.get("PR7_BLOCK3_ARTIFACT_DIR", "").strip()
    if not destination:
        return
    try:
        raw = _run(
            _compose(
                project,
                override,
                "logs",
                "--no-color",
                "--tail",
                "500",
                "pr7-block3-waf",
            ),
            timeout=60,
        )
        allowed = {
            "event",
            "timestamp",
            "mode",
            "selected_kind",
            "reason",
            "total_ms",
            "duration_ms",
        }
        events: list[dict[str, Any]] = []
        for line in raw.splitlines():
            payload = line.strip()
            if "{" in payload:
                payload = payload[payload.find("{") :]
            try:
                item = json.loads(payload)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("event"):
                events.append({key: item[key] for key in allowed if key in item})
        output = Path(destination).resolve()
        allowed_root = (ROOT / "artifacts").resolve()
        try:
            output.relative_to(allowed_root)
        except ValueError as exc:
            raise ValueError(
                "PR7_BLOCK3_ARTIFACT_DIR must be under repository artifacts"
            ) from exc
        output.mkdir(parents=True, exist_ok=True)
        (output / f"waf-timings-{project}.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "measurement": "pr7_waf_runtime_timing_events",
                    "scope": "local_disposable_e2e",
                    "events": events[-500:],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        # Evidence capture must never change enforcement or mask the test result.
        print(f"PR7 timing artifact capture skipped: {exc}")


def require_block3bc_artifacts() -> dict[str, Any]:
    lock_path = ROOT / "docs/project-ops/pr7-block3bc-artifact-lock.json"
    lock = verify_model_lock(MODEL_RUN_DIR, lock_path)
    require_portal_commit(PORTAL_PATH, lock["portal"]["commit"])
    require_pinned_compose_images(
        (
            ROOT / "docker-compose.yml",
            ROOT / "docker-compose.demo-target.yml",
            ROOT / "docker-compose.target-cloudflare.yml",
            ROOT / "docker-compose.pr7-block3b.yml",
        ),
        lock_path,
    )
    return lock


def _port(project: str, override: Path, service: str, container_port: int) -> int:
    value = _run(_compose(project, override, "port", service, str(container_port)))
    return int(value.rsplit(":", 1)[1])


def _override(
    *,
    postgres_password: str,
    sync_key: str,
    ingest_key: str,
    audit_key: str,
    enforcement_key: str,
) -> str:
    model_path = (
        "/app/ml_model/model_registry/staging/"
        "distilbert_v3_907k_cleaned_20260312_133755"
    )
    ttl_seconds = os.environ.get("PR7_BLOCK3_RECOMMENDATION_TTL_SECONDS", "900")
    if not ttl_seconds.isdigit() or not 30 <= int(ttl_seconds) <= 3600:
        raise ValueError(
            "PR7_BLOCK3_RECOMMENDATION_TTL_SECONDS must be an integer from 30 to 3600"
        )
    challenge_ttl = max(1, min(int(ttl_seconds) - 1, 300))
    return f"""services:
  postgres:
    environment:
      POSTGRES_PASSWORD: {postgres_password}

  backend:
    environment:
      APP_ENV: testing
      DATABASE_URL: postgresql+asyncpg://pr7_block3:{postgres_password}@postgres:5432/cybertrace_pr7_block3
      MODEL_PATH: {model_path}
      MODEL_REGISTRY_PATH: {model_path}
      API_SECRET_KEY: {secrets.token_hex(32)}
      WAF_INGEST_API_KEY: {ingest_key}
      WAF_AUDIT_EVIDENCE_KEY: {audit_key}
      WAF_STATE_SYNC_ENABLED: "true"
      WAF_STATE_SYNC_API_KEY: {sync_key}
      PR7_CRITICAL_WAF_MUTATION_ENABLED: "true"
      PR7_WAF_CAPACITY: "64"
      WAF_SOURCE_VERIFICATION_MODE: cloudflare_tunnel
      CLOUDFLARE_TARGET_ISOLATION_ENABLED: "true"
      CLOUDFLARE_TARGET_VERIFIED_PROOF: "true"
      ENFORCEMENT_MODE: enforce
      ENFORCEMENT_CHECK_API_KEY: {enforcement_key}
      ENFORCEMENT_RECOMMENDATION_TTL_SECONDS: "{ttl_seconds}"
      ENFORCEMENT_CHALLENGE_GRANT_TTL_SECONDS: "{challenge_ttl}"
      ENFORCEMENT_TURNSTILE_SECRET_KEY: 1x0000000000000000000000000000000AA
      ENFORCEMENT_TURNSTILE_EXPECTED_HOSTNAME: localhost
      ENFORCEMENT_TURNSTILE_TEST_MODE: "true"
      NOTIFICATION_WORKER_ENABLED: "false"
      NOTIFICATION_WORKER_REQUIRED: "false"

  pr7-block3-waf:
    environment:
      WAF_STATE_SYNC_API_KEY: {sync_key}

  pr7-block3-bridge:
    environment:
      WAF_INGEST_API_KEY: {ingest_key}
      WAF_AUDIT_EVIDENCE_KEY: {audit_key}
"""


def _wait_http(
    url: str,
    *,
    expected_status: int = 200,
    headers: dict[str, str] | None = None,
) -> None:
    timeout_raw = os.environ.get("PR7_BLOCK3_STARTUP_TIMEOUT_SECONDS", "180")
    if not timeout_raw.isdigit() or not 60 <= int(timeout_raw) <= 900:
        raise ValueError(
            "PR7_BLOCK3_STARTUP_TIMEOUT_SECONDS must be an integer from 60 to 900"
        )
    deadline = time.monotonic() + int(timeout_raw)
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            with httpx.Client(trust_env=False, follow_redirects=False) as client:
                response = client.get(url, headers=headers, timeout=5)
            if response.status_code == expected_status:
                return
            last_error = f"HTTP {response.status_code}: {response.text[:200]}"
        except httpx.HTTPError as exc:
            last_error = str(exc)
        time.sleep(1)
    raise AssertionError(f"timed out waiting for {url}: {last_error}")


def _snapshot(backend_url: str, sync_key: str) -> dict[str, Any]:
    with httpx.Client(trust_env=False, follow_redirects=False) as client:
        response = client.get(
            f"{backend_url}/api/internal/waf-enforcement/snapshot",
            headers={"Authorization": f"Bearer {sync_key}"},
            timeout=5,
        )
    response.raise_for_status()
    return response.json()


def _wait_waf_ready(project: str, override: Path) -> None:
    timeout_raw = os.environ.get("PR7_BLOCK3_STARTUP_TIMEOUT_SECONDS", "180")
    if not timeout_raw.isdigit() or not 60 <= int(timeout_raw) <= 900:
        raise ValueError(
            "PR7_BLOCK3_STARTUP_TIMEOUT_SECONDS must be an integer from 60 to 900"
        )
    deadline = time.monotonic() + int(timeout_raw)
    last_error = "not attempted"
    script = (
        "import urllib.request; "
        "response=urllib.request.urlopen("
        "'http://127.0.0.1:8081/__pr7/ready', timeout=5); "
        "print(response.status)"
    )
    while time.monotonic() < deadline:
        try:
            status = _run(
                _compose(
                    project,
                    override,
                    "exec",
                    "-T",
                    "pr7-block3-waf",
                    "python3",
                    "-c",
                    script,
                ),
                timeout=10,
            ).strip()
            if status == "204":
                return
            last_error = f"unexpected status output: {status!r}"
        except (RuntimeError, subprocess.SubprocessError) as exc:
            last_error = str(exc)
        time.sleep(1)
    raise AssertionError(f"timed out waiting for WAF readiness: {last_error}")


def _client_request(
    project: str,
    override: Path,
    service: str,
    path: str,
    *,
    evidence_id: str | None = None,
) -> int:
    script = (
        "import sys,urllib.error,urllib.request; "
        "path=sys.argv[1]; evidence=sys.argv[2]; "
        "headers={'Accept-Encoding':'identity'}; "
        "headers.update({'X-PR7-Evidence-ID':evidence} if evidence else {}); "
        "request=urllib.request.Request("
        "'http://pr7-block3-waf:8080'+path, headers=headers); "
        "processor=type('NoRaise',(urllib.request.HTTPErrorProcessor,),{"
        "'http_response':lambda self,request,response: response,"
        "'https_response':lambda self,request,response: response}); "
        "response=urllib.request.build_opener(processor()).open(request, timeout=10); "
        "print(response.status)"
    )
    return int(
        _run(
            _compose(
                project,
                override,
                "exec",
                "-T",
                service,
                "python",
                "-c",
                script,
                path,
                evidence_id or "",
            )
        ).splitlines()[-1]
    )


async def _read_state(factory) -> dict[str, Any]:
    from web_app.infrastructure.database.database import (
        TrafficLog,
        WafEffectiveStateRow,
    )

    async with factory() as session:
        traffic = (
            await session.execute(
                select(TrafficLog)
                .where(
                    TrafficLog.source_ip == SOURCE_A,
                    TrafficLog.request_path == PATH,
                    TrafficLog.status == "COMPLETED",
                )
                .order_by(TrafficLog.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        state = (
            await session.execute(
                select(WafEffectiveStateRow)
                .where(
                    WafEffectiveStateRow.source_ip == SOURCE_A,
                    WafEffectiveStateRow.protected_path == PATH,
                    WafEffectiveStateRow.status == "ACTIVE",
                )
                .order_by(WafEffectiveStateRow.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
    return {"traffic": traffic, "state": state}


async def _wait_attack_state_async(factory) -> tuple[int, int]:
    deadline = time.monotonic() + 180
    last = "no completed verified CRITICAL state"
    while time.monotonic() < deadline:
        found = await _read_state(factory)
        traffic = found["traffic"]
        state = found["state"]
        if traffic is not None and state is not None:
            if (
                traffic.prediction == "SQL Injection"
                and traffic.confidence_level == "CRITICAL"
                and traffic.source_verification_status == "VERIFIED"
                and traffic.source_provenance == "CLOUDFLARE_CONNECTING_IP"
                and traffic.model_version
                == "distilbert_v3_907k_cleaned_20260312_133755"
            ):
                return int(state.recommendation_id), int(state.revision)
            last = (
                f"prediction={traffic.prediction!r} tier={traffic.confidence_level!r} "
                f"verification={traffic.source_verification_status!r} "
                f"provenance={traffic.source_provenance!r}"
            )
        await asyncio.sleep(1)
    raise AssertionError(f"attack state did not converge: {last}")


async def _wait_attack_state_with_engine(database_url: str) -> tuple[int, int]:
    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        return await _wait_attack_state_async(factory)
    finally:
        await engine.dispose()


def _wait_attack_state(database_url: str) -> tuple[int, int]:
    return asyncio.run(_wait_attack_state_with_engine(database_url))


def _wait_snapshot(
    backend_url: str,
    sync_key: str,
    *,
    revision: int,
    recommendation_id: int | None,
    expected_count: int,
) -> None:
    deadline = time.monotonic() + 120
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = _snapshot(backend_url, sync_key)
        items = last.get("items", [])
        recommendation_matches = recommendation_id is None or any(
            item.get("recommendation_id") == recommendation_id for item in items
        )
        if (
            last.get("revision") == revision
            and len(items) == expected_count
            and recommendation_matches
        ):
            return
        time.sleep(1)
    raise AssertionError(f"snapshot did not converge: {json.dumps(last)}")


def _audit_tail(project: str, override: Path) -> list[str]:
    text = _run(
        _compose(
            project,
            override,
            "exec",
            "-T",
            "pr7-block3-waf",
            "sh",
            "-c",
            "tail -c 524288 /var/log/modsecurity/modsec_audit.jsonl "
            "2>/dev/null || true",
        )
    )
    return text.splitlines()


def _require_correlated_pr7_audit(
    project: str,
    override: Path,
    *,
    evidence_id: str,
    revision: int,
    recommendation_id: int,
    timeout_seconds: float = 30,
) -> str:
    required = (
        evidence_id,
        '"pr7"',
        f"revision-{revision}",
        f"recommendation-{recommendation_id}",
    )
    deadline = time.monotonic() + timeout_seconds
    while True:
        for line in reversed(_audit_tail(project, override)):
            if all(token in line for token in required):
                return line
        if time.monotonic() >= deadline:
            break
        time.sleep(0.25)
    raise AssertionError(
        "no single ModSecurity transaction contained the evidence marker, "
        f"PR7 tag, revision {revision}, and recommendation {recommendation_id}"
    )


def _evidence_log(project: str, override: Path) -> list[dict[str, Any]]:
    text = _run(
        _compose(
            project,
            override,
            "exec",
            "-T",
            "pr7-block3-waf",
            "sh",
            "-c",
            "tail -c 262144 /var/log/modsecurity/pr7_evidence.jsonl "
            "2>/dev/null || true",
        )
    )
    records = []
    for line in text.splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _wait_evidence_record(
    project: str,
    override: Path,
    evidence_id: str,
    *,
    timeout_seconds: float = 20,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while True:
        matches = [
            record
            for record in _evidence_log(project, override)
            if record.get("evidence_id") == evidence_id
        ]
        if matches:
            return matches[-1]
        if time.monotonic() >= deadline:
            break
        time.sleep(0.25)
    raise AssertionError(f"missing WAF evidence record {evidence_id}")


def _request_with_evidence(
    project: str,
    override: Path,
    service: str,
    path: str,
) -> tuple[int, str]:
    evidence_id = secrets.token_hex(12)
    status = _client_request(
        project,
        override,
        service,
        path,
        evidence_id=evidence_id,
    )
    return status, evidence_id


def _backend_network(project: str) -> str:
    return f"{project}_pr7-block3"


def _backend_container(project: str, override: Path) -> str:
    return _run(_compose(project, override, "ps", "-q", "backend")).splitlines()[-1]


def _disconnect_backend(project: str, override: Path) -> None:
    _run(
        [
            "docker",
            "network",
            "disconnect",
            _backend_network(project),
            _backend_container(project, override),
        ],
        timeout=30,
    )


def _reconnect_backend(project: str, override: Path) -> None:
    _run(
        [
            "docker",
            "network",
            "connect",
            _backend_network(project),
            _backend_container(project, override),
        ],
        timeout=30,
    )


def _waf_status(project: str, override: Path) -> dict[str, Any]:
    return json.loads(
        _run(
            _compose(
                project,
                override,
                "exec",
                "-T",
                "pr7-block3-waf",
                "pr7-waf-control",
                "status",
            ),
            timeout=30,
        )
    )


def _selected_expiry_epoch(project: str, override: Path) -> int:
    """Read the bounded absolute expiry embedded in the selected rule file."""
    script = (
        "import re; "
        "text=open('/pr7-state/selected.conf', encoding='ascii').read(); "
        "match=re.search(r'SecRule TIME_EPOCH \\\"@lt ([0-9]+)\\\"', text); "
        "print(match.group(1) if match else '0')"
    )
    value = _run(
        _compose(
            project,
            override,
            "exec",
            "-T",
            "pr7-block3-waf",
            "python3",
            "-c",
            script,
        ),
        timeout=30,
    ).splitlines()[-1]
    if not value.isdigit() or int(value) <= 0:
        raise AssertionError("selected PR7 rule did not contain an absolute expiry")
    return int(value)


def _revoke(
    database_url: str,
    recommendation_id: int,
    *,
    allow_terminal_noop: bool = False,
) -> int:
    from web_app.infrastructure.repositories.waf_state_repository import (
        WafStateRepository,
    )

    async def _run_revoke() -> int:
        engine = create_async_engine(database_url)
        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )
        async with factory() as session:
            result = await WafStateRepository(session).revoke(
                recommendation_id=recommendation_id
            )
        await engine.dispose()
        allowed_categories = {"REVOKED"}
        if allow_terminal_noop:
            allowed_categories.add("TERMINAL_NOOP")
        if result.category not in allowed_categories:
            raise AssertionError(f"revoke failed: {result}")
        return result.revision

    return asyncio.run(_run_revoke())


def _cleanup(project: str, override: Path) -> list[str]:
    errors: list[str] = []

    try:
        _run(
            _compose(
                project,
                override,
                "exec",
                "-T",
                "pr7-block3-waf",
                "pr7-waf-control",
                "disable",
            ),
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"disable failed: {type(exc).__name__}: {exc}")

    try:
        status = json.loads(
            _run(
                _compose(
                    project,
                    override,
                    "exec",
                    "-T",
                    "pr7-block3-waf",
                    "pr7-waf-control",
                    "status",
                ),
                timeout=30,
            )
        )
        metadata = status.get("metadata", {})
        if (
            status.get("disabled") is not True
            or metadata.get("selected_kind") != "disabled_empty"
            or metadata.get("selected_source_revision") is not None
        ):
            errors.append(f"unsafe final WAF state: {status!r}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"final-state check failed: {type(exc).__name__}: {exc}")

    try:
        _run(
            _compose(
                project,
                override,
                "down",
                "--volumes",
                "--remove-orphans",
            ),
            timeout=120,
        )
    except Exception as exc:  # noqa: BLE001
        errors.append(f"compose down failed: {type(exc).__name__}: {exc}")

    for kind, command in (
        (
            "containers",
            [
                "docker",
                "ps",
                "-aq",
                "--filter",
                f"label=com.docker.compose.project={project}",
            ],
        ),
        (
            "volumes",
            [
                "docker",
                "volume",
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={project}",
            ],
        ),
        (
            "networks",
            [
                "docker",
                "network",
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={project}",
            ],
        ),
    ):
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
            leftovers = result.stdout.split()
            if leftovers:
                errors.append(f"leftover {kind}: {leftovers}")
            if result.returncode != 0:
                errors.append(f"leftover check failed for {kind}: {result.returncode}")
        except Exception as exc:  # noqa: BLE001
            errors.append(
                f"leftover check failed for {kind}: "
                f"{type(exc).__name__}: {exc}"
            )

    return errors


def run_block3_lifecycle() -> None:
    project = f"pr7-block3-{secrets.token_hex(4)}"
    password = secrets.token_hex(24)
    sync_key = secrets.token_hex(32)
    ingest_key = secrets.token_hex(32)
    audit_key = secrets.token_hex(32)
    enforcement_key = secrets.token_hex(32)
    # The lifecycle uses the PR7 3B/3C artifact set.  Keep this separate from
    # the historical Block 3 lock so the disposable run validates the portal
    # sentinel revision that is actually mounted by the current stack.
    require_block3bc_artifacts()
    with tempfile.TemporaryDirectory(prefix="pr7-block3-") as temporary:
        override = Path(temporary) / "compose.override.yml"
        override.write_text(
            _override(
                postgres_password=password,
                sync_key=sync_key,
                ingest_key=ingest_key,
                audit_key=audit_key,
                enforcement_key=enforcement_key,
            ),
            encoding="utf-8",
        )
        primary_error: BaseException | None = None
        try:
            _run(
                _compose(
                    project,
                    override,
                    "up",
                    "--detach",
                    "--build",
                    "postgres",
                    "backend",
                    "demo-portal",
                    "pr7-block3-waf",
                    "pr7-block3-bridge",
                    "source-client-a",
                    "source-client-b",
                ),
                timeout=420,
            )
            backend_port = _port(project, override, "backend", 8000)
            backend_url = f"http://127.0.0.1:{backend_port}"
            _wait_http(f"{backend_url}/health", expected_status=200)
            _wait_http(
                f"{backend_url}/api/internal/waf-enforcement/snapshot",
                expected_status=200,
                headers={"Authorization": f"Bearer {sync_key}"},
            )
            _wait_waf_ready(project, override)

            db_port = _port(project, override, "postgres", 5432)
            database_url = (
                "postgresql+asyncpg://pr7_block3:"
                f"{password}@127.0.0.1:{db_port}/cybertrace_pr7_block3"
            )

            baseline_status, baseline_id = _request_with_evidence(
                project, override, "source-client-a", f"{PATH}?baseline=1"
            )
            assert baseline_status < 500
            assert baseline_status != 403
            baseline_record = _wait_evidence_record(
                project, override, baseline_id
            )
            assert baseline_record["upstream_addr"] not in {"", "-"}
            assert baseline_record["upstream_status"] not in {"", "-"}

            wrong_path_baseline_status, wrong_path_baseline_id = (
                _request_with_evidence(
                    project, override, "source-client-a", f"{PATH}/?baseline=1"
                )
            )
            assert wrong_path_baseline_status < 500
            wrong_path_baseline_record = _wait_evidence_record(
                project, override, wrong_path_baseline_id
            )
            assert wrong_path_baseline_record["upstream_addr"] not in {"", "-"}

            assert (
                _client_request(project, override, "source-client-a", ATTACK_PATH)
                == 403
            )
            recommendation_id, revision = _wait_attack_state(database_url)
            _wait_snapshot(
                backend_url,
                sync_key,
                revision=revision,
                recommendation_id=recommendation_id,
                expected_count=1,
            )

            evidence_id = secrets.token_hex(12)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if (
                    _client_request(
                        project,
                        override,
                        "source-client-a",
                        f"{PATH}?pr7_check={evidence_id}",
                        evidence_id=evidence_id,
                    )
                    == 403
                ):
                    break
                time.sleep(1)
            else:
                raise AssertionError("harmless matching request was not PR7-blocked")

            _require_correlated_pr7_audit(
                project,
                override,
                evidence_id=evidence_id,
                revision=revision,
                recommendation_id=recommendation_id,
            )

            matching = _wait_evidence_record(project, override, evidence_id)
            assert matching["status"] == 403
            assert matching["remote_addr"] == SOURCE_A
            assert matching["uri"] == PATH
            assert matching["upstream_addr"] in {"", "-"}
            assert matching["upstream_status"] in {"", "-"}
            assert matching["upstream_response_time"] in {"", "-"}

            # A selected non-empty state is data-plane safe even when the
            # control-plane backend is unavailable.  The WAF must retain the
            # last verified snapshot rather than replacing it with empty
            # state after a failed poll.
            _disconnect_backend(project, override)
            try:
                outage_status, outage_id = _request_with_evidence(
                    project,
                    override,
                    "source-client-a",
                    f"{PATH}?backend_outage={evidence_id}",
                )
                assert outage_status == 403
                outage_record = _wait_evidence_record(project, override, outage_id)
                assert outage_record["remote_addr"] == SOURCE_A
                assert outage_record["upstream_addr"] in {"", "-"}
                outage_state = _waf_status(project, override)
                outage_metadata = outage_state.get("metadata", {})
                assert outage_state.get("disabled") is False
                assert outage_metadata.get("selected_kind") == "authoritative"
                assert outage_metadata.get("selected_source_revision") == revision

                if os.environ.get("PR7_RUN_BLOCK3_EXPIRY_OUTAGE") == "1":
                    expiry_epoch = _selected_expiry_epoch(project, override)
                    expiry_deadline = expiry_epoch + 2
                    while time.time() <= expiry_deadline:
                        time.sleep(1)
                    expired_status, expired_id = _request_with_evidence(
                        project,
                        override,
                        "source-client-a",
                        f"{PATH}?after_expiry={evidence_id}",
                    )
                    assert expired_status != 403
                    expired_record = _wait_evidence_record(
                        project, override, expired_id
                    )
                    assert expired_record["upstream_addr"] not in {"", "-"}
                    assert (
                        _client_request(
                            project,
                            override,
                            "source-client-a",
                            ATTACK_PATH,
                        )
                        == 403
                    ), "static CRS did not remain active after PR7 expiry"
            finally:
                _reconnect_backend(project, override)
            _wait_http(f"{backend_url}/health", expected_status=200)

            wrong_source_status, wrong_source_id = _request_with_evidence(
                project, override, "source-client-b", f"{PATH}?wrong_source=1"
            )
            assert wrong_source_status == baseline_status
            wrong_source_record = _wait_evidence_record(
                project, override, wrong_source_id
            )
            assert wrong_source_record["remote_addr"] == SOURCE_B
            assert wrong_source_record["upstream_addr"] not in {"", "-"}
            assert wrong_source_record["upstream_status"] not in {"", "-"}

            wrong_path_status, wrong_path_id = _request_with_evidence(
                project, override, "source-client-a", f"{PATH}/?wrong_path=1"
            )
            assert wrong_path_status == wrong_path_baseline_status
            wrong_path_record = _wait_evidence_record(
                project, override, wrong_path_id
            )
            assert wrong_path_record["remote_addr"] == SOURCE_A
            assert wrong_path_record["uri"] == f"{PATH}/"
            assert wrong_path_record["upstream_addr"] not in {"", "-"}

            revoked_revision = _revoke(
                database_url,
                recommendation_id,
                allow_terminal_noop=(
                    os.environ.get("PR7_RUN_BLOCK3_EXPIRY_OUTAGE") == "1"
                ),
            )
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                after_revoke_status, after_revoke_id = _request_with_evidence(
                    project,
                    override,
                    "source-client-a",
                    f"{PATH}?after_revoke={evidence_id}",
                )
                if after_revoke_status == baseline_status:
                    after_revoke_record = _wait_evidence_record(
                        project, override, after_revoke_id
                    )
                    if after_revoke_record["upstream_addr"] not in {"", "-"}:
                        break
                time.sleep(1)
            else:
                raise AssertionError("revoked PR7 state continued to block")
            _wait_snapshot(
                backend_url,
                sync_key,
                revision=revoked_revision,
                recommendation_id=None,
                expected_count=0,
            )
        except BaseException as exc:
            try:
                logs = _run(
                    _compose(
                        project,
                        override,
                        "logs",
                        "--no-color",
                        "--tail",
                        "200",
                        "postgres",
                        "backend",
                        "demo-portal",
                        "pr7-block3-waf",
                        "pr7-block3-bridge",
                    ),
                    timeout=60,
                )
            except Exception as log_error:
                logs = f"unable to collect disposable logs: {log_error}"
            primary_error = RuntimeError(f"PR7 Block 3 lifecycle failed\n{logs}")
            raise primary_error from exc
        finally:
            _capture_timing_artifact(project, override)
            cleanup_errors = _cleanup(project, override)
            if cleanup_errors:
                if primary_error is None:
                    raise RuntimeError(
                        "Block 3 assertions passed but cleanup failed:\n"
                        + "\n".join(cleanup_errors)
                    )
                primary_error.add_note(
                    "Block 3 cleanup errors:\n" + "\n".join(cleanup_errors)
                )
