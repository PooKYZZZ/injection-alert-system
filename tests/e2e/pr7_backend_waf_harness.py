from __future__ import annotations

import asyncio
import json
import os
import secrets
import subprocess
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
POSTGRES_PASSWORD = "pr7-local-password"
POSTGRES_HOST_URL = (
    "postgresql+asyncpg://pr7:pr7-local-password@127.0.0.1:{port}/cybertrace_pr7"
)
POSTGRES_CONTAINER_URL = (
    "postgresql+asyncpg://pr7:pr7-local-password@postgres:5432/cybertrace_pr7"
)
SOURCE_IP = "203.0.113.7"
PATH = "/records/search"


def _run(command: list[str], *, cwd: Path = ROOT) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result.stdout.strip()


def _compose(project: str, override: Path, *args: str) -> list[str]:
    return [
        "docker",
        "compose",
        "--project-name",
        project,
        "-f",
        "docker-compose.yml",
        "-f",
        "docker-compose.test.yml",
        "-f",
        str(override),
        *args,
    ]


def _port(project: str, override: Path, service: str, container_port: int) -> int:
    value = _run(
        _compose(project, override, "port", service, str(container_port))
    )
    return int(value.rsplit(":", 1)[1])


def _override(database_url: str, sync_key: str) -> str:
    return f"""services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: cybertrace_pr7
      POSTGRES_USER: pr7
      POSTGRES_PASSWORD: {POSTGRES_PASSWORD}
    ports:
      - "127.0.0.1::5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U pr7 -d cybertrace_pr7"]
      interval: 2s
      timeout: 3s
      retries: 30
    volumes:
      - pr7-postgres:/var/lib/postgresql/data

  backend:
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "127.0.0.1::8000"
    environment:
      APP_ENV: testing
      DATABASE_URL: {database_url}
      MODEL_PATH: /app/ml_model/model_registry
      MODEL_REGISTRY_PATH: /app/ml_model/model_registry
      API_SECRET_KEY: {"a" * 32}
      WAF_INGEST_API_KEY: {"b" * 32}
      WAF_AUDIT_EVIDENCE_KEY: {"c" * 32}
      WAF_STATE_SYNC_ENABLED: "true"
      WAF_STATE_SYNC_API_KEY: {sync_key}
      WAF_SOURCE_VERIFICATION_MODE: unverified
      ENFORCEMENT_MODE: off
      NOTIFICATION_WORKER_ENABLED: "false"
      NOTIFICATION_WORKER_REQUIRED: "false"

  pr7-waf:
    depends_on:
      backend:
        condition: service_healthy
    ports:
      - "127.0.0.1::8080"
      - "127.0.0.1::8081"
    environment:
      PR7_WAF_MODE: enforce
      PR7_POLL_INTERVAL: "1"
      WAF_STATE_SYNC_API_KEY: {sync_key}

volumes:
  pr7-postgres:
"""


def _wait_http(url: str, *, headers: dict[str, str] | None = None) -> None:
    deadline = time.monotonic() + 90
    last_error = "not attempted"
    while time.monotonic() < deadline:
        try:
            with httpx.Client(trust_env=False, follow_redirects=False) as client:
                response = client.get(url, headers=headers, timeout=3)
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


def _poll_snapshot(
    backend_url: str,
    sync_key: str,
    *,
    expected_count: int,
    expected_revision: int | None = None,
) -> dict[str, Any]:
    deadline = time.monotonic() + 45
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = _snapshot(backend_url, sync_key)
        if len(last.get("items", [])) == expected_count and (
            expected_revision is None or last.get("revision") == expected_revision
        ):
            return last
        time.sleep(1)
    raise AssertionError(f"snapshot did not converge: {json.dumps(last)}")


def _probe(
    project: str,
    override: Path,
    *,
    source_ip: str | None = SOURCE_IP,
    path: str = PATH,
) -> int:
    script = (
        "import httpx,sys; "
        "headers={'Accept-Encoding':'identity'}; "
        "source=sys.argv[1]; path=sys.argv[2]; "
        "headers.update({'X-PR7-Probe-Source':source} if source else {}); "
        "print(httpx.get('http://127.0.0.1:8081'+path, headers=headers, "
        "trust_env=False, follow_redirects=False, timeout=5).status_code)"
    )
    source = source_ip or ""
    try:
        output = _run(
            _compose(
                project,
                override,
                "exec",
                "-T",
                "pr7-waf",
                "python3",
                "-c",
                script,
                source,
                path,
            )
        )
    except RuntimeError:
        return 599
    return int(output.splitlines()[-1])


async def _seed(database_url: str, sync_key: str) -> tuple[int, int]:
    os.environ["APP_ENV"] = "testing"
    os.environ["DATABASE_URL"] = database_url
    os.environ["WAF_STATE_SYNC_ENABLED"] = "true"
    os.environ["WAF_STATE_SYNC_API_KEY"] = sync_key
    from sqlalchemy import insert
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    from web_app.infrastructure.database.database import TrafficLog
    from web_app.infrastructure.repositories.waf_state_repository import (
        WafStateRepository,
    )

    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    async with factory() as session:
        await session.execute(
            insert(TrafficLog).values(
                id=1,
                source_ip=SOURCE_IP,
                source_provenance="CLOUDFLARE_CONNECTING_IP",
                source_verification_status="VERIFIED",
                request_path=PATH,
                request_method="GET",
                http_request="GET /records/search HTTP/1.1",
                created_at=datetime.now(timezone.utc),
                timestamp=datetime.now(timezone.utc),
                status="COMPLETED",
                processing_attempt=0,
                prediction="SQL Injection",
                confidence_level="CRITICAL",
            )
        )
        await session.commit()
        result = await WafStateRepository(session).record_critical_waf_recommendation(
            trigger_traffic_log_id=1,
            recommendation_expires_at=expires,
            effective_expires_at=expires,
        )
    await engine.dispose()
    if result.category != "ACTIVATED":
        raise AssertionError(f"CRITICAL recommendation was not activated: {result}")
    return result.recommendation_id, result.revision


async def _revoke(database_url: str, recommendation_id: int) -> int:
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    from web_app.infrastructure.repositories.waf_state_repository import (
        WafStateRepository,
    )

    engine = create_async_engine(database_url)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        result = await WafStateRepository(session).revoke(
            recommendation_id=recommendation_id
        )
    await engine.dispose()
    if result.category != "REVOKED":
        raise AssertionError(f"recommendation was not revoked: {result}")
    return result.revision


def run_backend_to_waf_test() -> None:
    project = f"pr7-e2e-{secrets.token_hex(4)}"
    sync_key = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory(prefix="pr7-e2e-") as temporary:
        override = Path(temporary) / "compose.override.yml"
        override.write_text(
            _override(POSTGRES_CONTAINER_URL, sync_key), encoding="utf-8"
        )
        try:
            _run(
                _compose(
                    project,
                    override,
                    "--profile",
                    "pr7-local-waf",
                    "up",
                    "--detach",
                    "--build",
                    "postgres",
                    "backend",
                    "pr7-waf",
                )
            )
            backend_port = _port(project, override, "backend", 8000)
            backend_url = f"http://127.0.0.1:{backend_port}"
            _wait_http(f"{backend_url}/health")
            _wait_http(
                f"{backend_url}/api/internal/waf-enforcement/snapshot",
                headers={"Authorization": f"Bearer {sync_key}"},
            )

            db_port = _port(project, override, "postgres", 5432)
            database_url = POSTGRES_HOST_URL.format(port=db_port)
            recommendation_id, revision = asyncio.run(_seed(database_url, sync_key))
            _poll_snapshot(
                backend_url,
                sync_key,
                expected_count=1,
                expected_revision=revision,
            )

            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if _probe(project, override) == 403:
                    break
                time.sleep(1)
            else:
                raise AssertionError("real CRITICAL snapshot did not produce 403")
            assert _probe(project, override, source_ip="203.0.113.8") == 204
            assert _probe(project, override, path="/records/search/other") == 204

            audit = _run(
                _compose(
                    project,
                    override,
                    "exec",
                    "-T",
                    "pr7-waf",
                    "cat",
                    "/var/log/modsecurity/modsec_audit.jsonl",
                )
            )
            assert "PR7" in audit
            assert f"revision-{revision}" in audit
            assert f"recommendation-{recommendation_id}" in audit

            revoked_revision = asyncio.run(_revoke(database_url, recommendation_id))
            _poll_snapshot(
                backend_url,
                sync_key,
                expected_count=0,
                expected_revision=revoked_revision,
            )
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and _probe(project, override) != 204:
                time.sleep(1)
            assert _probe(project, override) == 204

            _run(_compose(project, override, "restart", "pr7-waf"))
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                if _probe(project, override) == 204:
                    break
                time.sleep(1)
            assert _probe(project, override) == 204
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
                        "pr7-waf",
                    )
                )
            except Exception as log_error:
                logs = f"unable to collect disposable logs: {log_error}"
            raise RuntimeError(f"PR7 backend-to-WAF E2E failed\n{logs}") from exc
        finally:
            _run(
                _compose(
                    project,
                    override,
                    "--profile",
                    "pr7-local-waf",
                    "down",
                    "--volumes",
                    "--remove-orphans",
                )
            )
