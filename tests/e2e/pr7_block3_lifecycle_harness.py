from __future__ import annotations

import asyncio
import json
import secrets
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

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


def _wait_http(url: str, *, headers: dict[str, str] | None = None) -> None:
    deadline = time.monotonic() + 180
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            with httpx.Client(trust_env=False, follow_redirects=False) as client:
                response = client.get(url, headers=headers, timeout=5)
            if response.status_code < 500:
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


async def _read_state(database_url: str) -> dict[str, Any]:
    from web_app.infrastructure.database.database import (
        TrafficLog,
        WafEffectiveStateRow,
    )

    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
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
    await engine.dispose()
    return {"traffic": traffic, "state": state}


def _wait_attack_state(database_url: str) -> tuple[int, int]:
    deadline = time.monotonic() + 180
    last = "no completed verified CRITICAL state"
    while time.monotonic() < deadline:
        found = asyncio.run(_read_state(database_url))
        traffic = found["traffic"]
        state = found["state"]
        if traffic is not None and state is not None:
            if (
                traffic.prediction == "SQL Injection"
                and traffic.confidence_level == "CRITICAL"
                and traffic.source_verification_status == "VERIFIED"
                and traffic.source_provenance == "CLOUDFLARE_CONNECTING_IP"
            ):
                return int(state.recommendation_id), int(state.revision)
            last = (
                f"prediction={traffic.prediction!r} tier={traffic.confidence_level!r} "
                f"verification={traffic.source_verification_status!r} "
                f"provenance={traffic.source_provenance!r}"
            )
        time.sleep(1)
    raise AssertionError(f"attack state did not converge: {last}")


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


def _audit(project: str, override: Path) -> str:
    return _run(
        _compose(
            project,
            override,
            "exec",
            "-T",
            "pr7-block3-waf",
            "cat",
            "/var/log/modsecurity/modsec_audit.jsonl",
        )
    )


def _evidence_log(project: str, override: Path) -> list[dict[str, Any]]:
    text = _run(
        _compose(
            project,
            override,
            "exec",
            "-T",
            "pr7-block3-waf",
            "cat",
            "/var/log/modsecurity/pr7_evidence.jsonl",
        )
    )
    records = []
    for line in text.splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _revoke(database_url: str, recommendation_id: int) -> int:
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
        if result.category != "REVOKED":
            raise AssertionError(f"revoke failed: {result}")
        return result.revision

    return asyncio.run(_run_revoke())


def run_block3_lifecycle() -> None:
    project = f"pr7-block3-{secrets.token_hex(4)}"
    password = secrets.token_hex(24)
    sync_key = secrets.token_hex(32)
    ingest_key = secrets.token_hex(32)
    audit_key = secrets.token_hex(32)
    enforcement_key = secrets.token_hex(32)
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
                timeout=300,
            )
            backend_port = _port(project, override, "backend", 8000)
            backend_url = f"http://127.0.0.1:{backend_port}"
            _wait_http(f"{backend_url}/health")
            _wait_http(
                f"{backend_url}/api/internal/waf-enforcement/snapshot",
                headers={"Authorization": f"Bearer {sync_key}"},
            )

            db_port = _port(project, override, "postgres", 5432)
            database_url = (
                "postgresql+asyncpg://pr7_block3:"
                f"{password}@127.0.0.1:{db_port}/cybertrace_pr7_block3"
            )

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

            assert _client_request(
                project, override, "source-client-b", f"{PATH}?pr7_check={evidence_id}"
            ) != 403
            assert _client_request(
                project, override, "source-client-a", "/records/search/"
            ) != 403

            audit = _audit(project, override)
            assert evidence_id in audit
            assert '"pr7"' in audit
            assert f"revision-{revision}" in audit
            assert f"recommendation-{recommendation_id}" in audit

            evidence = [
                record for record in _evidence_log(project, override)
                if record.get("evidence_id") == evidence_id
            ]
            assert evidence
            matching = evidence[-1]
            assert matching["status"] == 403
            assert matching["upstream_addr"] in {"", "-"}
            assert matching["upstream_status"] in {"", "-"}
            assert matching["upstream_response_time"] in {"", "-"}

            revoked_revision = _revoke(database_url, recommendation_id)
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if _client_request(
                    project,
                    override,
                    "source-client-a",
                    f"{PATH}?after_revoke={evidence_id}",
                ) != 403:
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
        except Exception as exc:
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
            raise RuntimeError(f"PR7 Block 3 lifecycle failed\n{logs}") from exc
        finally:
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
            except Exception:
                pass
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
            except Exception:
                pass
