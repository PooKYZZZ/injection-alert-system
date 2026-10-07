# CyberTrace

**Injection Alert System** is an academic capstone exploring how to reduce
analyst fatigue and improve the workflow for reviewing suspicious web traffic.
CyberTrace brings machine-learning detections and available ModSecurity/OWASP
CRS evidence into one analyst workflow, helping analysts prioritize alerts,
inspect why requests were flagged, and make informed, consistent triage and
response decisions.

The system uses a Next.js dashboard and backend-for-frontend (BFF), a FastAPI
backend, transformer-based model artifacts, Supabase-backed application data,
and optional local WAF integration.

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

CyberTrace is an academic Next.js/FastAPI system with ML-based detection,
analyst review, Supabase-backed data, and optional local WAF integration. It is
not production-validated.

- **Local proof:** ModSecurity/OWASP CRS ingest runs through `localhost:8088`
  and the demo target through `localhost:8089`. Controlled enforcement evidence
  covers LOW/MEDIUM (PR5), HIGH (PR6), and CRITICAL (PR7); this does not prove
  hosted or Cloudflare enforcement.
- **Remaining gaps:** Cloudflare/origin trust verification and hosted
  enforcement are unverified. Alert SSE is single-process without durable
  replay or multi-worker fan-out; notification-worker operational validation
  remains incomplete.
- **Interpretation:** Confidence describes model certainty, not attack
  severity. `Normal` remains `ALLOWED`.

See [Project Ops Status](docs/project-ops/STATUS.md) for dated tests and proof,
and [Architecture](docs/architecture.md) for implementation details and gaps.

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

The [local setup guide](docs/SETUP.md) covers environment files and direct
development. Use the [Docker Compose guide](docker/compose/README.md) for the
isolated stack commands and the [smoke-test runbook](docs/project-ops/SMOKE_TEST_RUNBOOK.md)
for optional WAF profiles and verification.

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
the [smoke-test runbook](docs/project-ops/SMOKE_TEST_RUNBOOK.md); they are not
enabled by this command.

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
- [Local setup](docs/SETUP.md) — direct development setup and local environment
  boundaries.
- [Docker Compose guide](docker/compose/README.md) — ordinary local stack
  commands.
- [Smoke-test runbook](docs/project-ops/SMOKE_TEST_RUNBOOK.md) — WAF/demo smoke
  procedures and evidence boundaries.
- [Architecture](docs/architecture.md) — application boundaries, data flow,
  security semantics, and implementation limitations.
- [Operator documentation map](docs/project-ops/README.md) — runbooks, status
  records, and WAF demonstration evidence.
- [Contributing](CONTRIBUTING.md) — workflow, guardrails, and validation.

## Maintainers and reuse

CyberTrace is maintained by its academic capstone team. This repository
does not currently include a `LICENSE` file; do not assume that code or
artifacts are licensed for reuse.
