# CyberTrace

**Injection Alert System** — an academic capstone project for reviewing
suspicious web requests with machine-learning classification and web application
firewall evidence.

CyberTrace records request and detection context, classifies supported injection
patterns, and presents the resulting evidence for analyst review. It combines a
Next.js app with a public project site, an authenticated analyst dashboard and
backend-for-frontend (BFF), a FastAPI service, model inference, PostgreSQL-backed
application data, and an optional local ModSecurity/OWASP Core Rule Set (CRS)
integration.

> **Project scope:** CyberTrace is a research and demonstration system, not a
> production-ready WAF or a replacement for layered security controls. Use the
> attack-testing and enforcement paths only in systems you own or are authorized
> to test. A local proof or a healthy container does not establish hosted or
> production readiness.

## What it does

- Analyzes supported HTTP request records for SQL injection and code injection
  patterns.
- Stores detection context, including model output and available ModSecurity/CRS
  evidence.
- Provides public project information separately from the authenticated analyst
  dashboard.
- Provides an authenticated dashboard for reviewing traffic, alerts, and
  analyst triage.
- Includes controlled local Compose profiles for demonstrating ModSecurity/CRS
  audit-event ingestion.

The ML model score and confidence tier describe the model's output; they are not
attack severity and should not be presented as calibrated probabilities unless
calibration has been separately established. ModSecurity/CRS evidence is a
separate signal. A recorded action label or policy recommendation does not, by
itself, prove that a request was blocked or throttled by the network.

## How the main components connect

| Flow | Path |
|---|---|
| Public project site | Browser → host-gated Next.js public pages (`cybertracesystems.com`) |
| Dashboard and API | Browser → Next.js dashboard and BFF → FastAPI → model service and database |
| Accounts and sessions | Browser → Auth.js session in Next.js; server-side account records → Supabase PostgreSQL |
| Optional local WAF evidence | ModSecurity/OWASP CRS → audit log → bridge → FastAPI WAF-ingest endpoint |

The browser does not call FastAPI directly. The ModSecurity path is an optional,
controlled integration; it is not in front of every deployment or request.

## Status

CyberTrace is an active academic app-plus-BFF project with a controlled local
ModSecurity/OWASP CRS proof path. It is not a production-validated deployment.

Local WAF-ingest and controlled-enforcement results are dated evidence, not
proof of current public Cloudflare routing or hosted enforcement. See
[Project Ops Status](docs/project-ops/STATUS.md) for the latest operator check,
test results, and remaining verification gaps.

## Technology

| Area | Technologies |
|---|---|
| Dashboard | Next.js App Router, React, TypeScript, Auth.js, Zod |
| Backend | FastAPI, Python, Pydantic, asynchronous SQLAlchemy |
| Machine learning | PyTorch and Hugging Face Transformers |
| Data | PostgreSQL/Supabase for the hosted application path; local PostgreSQL and SQLite are used in development and tests |
| WAF demonstration | ModSecurity and OWASP CRS, with a Python audit-log bridge |
| Local orchestration | Docker Compose |

Use the versions pinned or constrained in the repository's runtime files and
package manifests rather than assuming that this table specifies exact patch
versions.

## Get started locally

The detailed guide covers environment files, direct development, the isolated
Docker stack, optional WAF profiles, and troubleshooting:
[Local setup](docs/SETUP.md).

Prerequisites are Git, Python 3.14 or newer, Node.js 24, npm, and Docker Desktop
for the Compose workflow. Prepare the local environment files exactly as
described in the setup guide before starting Compose. In particular, keep local
secrets in ignored environment files and do not point the ordinary local stack
at the hosted database.

After completing that preparation, start the isolated local application stack
from the repository root:

```powershell
docker compose --project-directory . --env-file .local/env/.env -f docker/compose/base.yml -f docker/compose/overlays/local.yml up --build -d
```

The Next.js app is served at [http://localhost:3000](http://localhost:3000).
For local sign-in, open [http://localhost:3000/login](http://localhost:3000/login);
the protected dashboard is under `/dashboard`. The public homepage is host-gated
to `cybertracesystems.com`, so `/` on ordinary `localhost` redirects to `/login`.
This describes the repository's routing code, not current DNS or Cloudflare
availability. Optional ModSecurity/CRS demonstration profiles are documented in
[Local setup](docs/SETUP.md); they are not enabled by this command.

## Run the main checks

Run the backend checks from the repository root:

```powershell
.venv/Scripts/python.exe -m pytest -q
```

Run the frontend checks from the repository root:

```powershell
Push-Location frontend
npm run lint
npm run typecheck
npx vitest run
Pop-Location
```

These are commands to run against the checkout; this README does not claim that
they have passed for every commit. See the contributor guide for additional
validation and focused test commands.

## Repository map

| Path | Purpose |
|---|---|
| `frontend/` | Next.js dashboard and BFF |
| `web_app/` | FastAPI backend and application layers |
| `ml_model/` | Model loading, training/evaluation code, and model artifacts |
| `config/` | Application and model configuration |
| `docker/` | Compose definitions and image build files |
| `migrations/` | Alembic database migrations |
| `tests/` | Backend and integration tests; frontend tests also live under `frontend/` |
| `docs/` | Setup, architecture, and project documentation |
| `reports/` | Dated proof and research artifacts |

## Project documentation

- [Documentation index](docs/README.md) — routes to the maintained guides and
  clearly dated status/evidence documents.
- [Local setup](docs/SETUP.md) — developer setup and local Compose workflows.
- [Architecture](docs/architecture.md) — application boundaries, data flow,
  security semantics, and implementation limitations.
- [Operator documentation map](docs/project-ops/README.md) — runbooks, status
  records, and WAF demonstration evidence.
- [Contributing](CONTRIBUTING.md) — workflow, guardrails, and validation.

## Maintainers and reuse

CyberTrace is maintained by its academic capstone team. This repository
does not currently include a `LICENSE` file; do not assume that code or
artifacts are licensed for reuse.
