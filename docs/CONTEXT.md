# CyberTrace Project Context

**Last reviewed:** 2026-10-08

**Academic context:** capstone project for LARES (Land Registration Systems, Inc.); defense: May 2026.

## Purpose

CyberTrace is an academic security-monitoring and analyst-triage project. It aims to reduce analyst fatigue and improve review workflow by bringing suspicious web-request records, machine-learning predictions, available Web Application Firewall (WAF) evidence, and analyst triage into one place. Analysts can prioritize what needs attention, inspect the context behind a detection, and record a review or response decision without treating a model score as the whole story.

The project is intended to support human review and explainability. It does not claim that machine learning alone proves an attack, that a recorded action label proves a request was blocked, or that CyberTrace has measured a reduction in analyst fatigue.

## People and system boundary

| Participant or system | Relationship to CyberTrace |
|---|---|
| Analyst | Reviews suspicious traffic, examines available evidence, and records triage decisions. |
| Administrator | Manages accounts and access according to the implemented role permissions. |
| Public-site visitor | Reads public project information; this is separate from the authenticated analyst dashboard. |
| Next.js application | Serves the public pages and dashboard. Its server-side route handlers form the browser-facing backend-for-frontend (BFF). |
| FastAPI backend | Applies backend use cases, accesses the model service, and reads/writes application data. |
| ML model | Produces a supported prediction and confidence score for the request data it receives. |
| PostgreSQL / Supabase | Provides the application-data boundary for the hosted path; local development and tests may use isolated databases. |
| ModSecurity / OWASP CRS | Optional WAF evidence source used in controlled local and demonstration paths; it is not necessarily in front of every CyberTrace deployment or request. |

```text
Analyst or visitor browser
  +-- public-site request --------> Next.js public pages
  +-- dashboard/API request -----> Next.js BFF --> FastAPI --> ML model
                                                   |
                                                   +--------> Application database

Optional controlled WAF evidence path:
ModSecurity / OWASP CRS -> audit log -> bridge -> FastAPI
```

The browser talks to Next.js, not directly to FastAPI. The optional WAF path supplies evidence to CyberTrace; it should not be described as a universal production traffic gateway. See [Architecture](architecture.md) for the current implementation topology and interfaces.

## How to interpret detections and actions

- A **prediction** is the model's classification of the supplied request data. It may be wrong and should be considered with the rest of the evidence.
- A **confidence score/tier** describes how strongly the model supports its prediction. Project tiers such as LOW, MEDIUM, HIGH, and CRITICAL are confidence categories, not attack-severity ratings or calibrated probabilities.
- **WAF/CRS evidence** is a separate signal produced by the WAF path. It may be absent, incomplete, or impossible to correlate to another record; do not infer a relationship from similar IP addresses, routes, payloads, or timestamps alone.
- An **analyst triage label** records a human review decision. A **policy recommendation** describes what a policy would choose. Neither alone proves what happened at the network or application boundary.
- Treat a **recorded action label** as stored alert metadata unless there is independent evidence of the observed HTTP response or enforcement source. Keep the prediction, confidence, WAF evidence, policy decision, analyst decision, and observed outcome distinct.

These distinctions are part of the product's explainability and safety boundary. For exact current field names, endpoint behavior, and enforcement limitations, use [Architecture](architecture.md) and the applicable dated evidence in [Project Ops Status](project-ops/STATUS.md).

## Repository orientation

| Location | What belongs there |
|---|---|
| `frontend/` | Next.js public pages, authenticated dashboard, and BFF route handlers. |
| `web_app/` | FastAPI backend, application/domain layers, persistence adapters, and model-service boundary. |
| `ml_model/` | Model code, preprocessing/training/evaluation workflows, and model artifacts. |
| `migrations/` | Database schema and function migrations. |
| `docker/` | Compose definitions and local integration profiles. |
| `tests/` | Backend, frontend, integration, and operational-boundary tests. |
| `docs/` and `reports/` | Setup, architecture, requirements, runbooks, dated verification, and academic evidence. |

## Where to go next

| Question | Start here |
|---|---|
| What is the project for? | [Repository overview](../README.md) and this context guide. |
| How is the current code structured and what does it actually implement? | [Architecture](architecture.md). |
| How do I configure and run a local checkout? | [Local setup](SETUP.md) and the [Docker Compose guide](../docker/compose/README.md). |
| What did a specific operator or test session verify? | [Project Ops Status](project-ops/STATUS.md); check each record's date and scope. |
| How do I perform a controlled local smoke test? | [Smoke-test runbook](project-ops/SMOKE_TEST_RUNBOOK.md). |
| What did the client ask for? | [Client requirements](client-requirements.md). Requirements are not proof of implementation. |
| What unresolved work has been recorded? | [Implementation gap register](project-ops/IMPLEMENTATION_GAP_REGISTER.md). It was last reviewed on 2026-07-30, so reconcile it with current code before using it as a backlog. |

## Evidence and maintenance rules

This page is stable orientation, not a live status report or implementation inventory. A date on this page indicates when its framing was reviewed; it does not certify the current deployment, tests, database, or enforcement settings.

- Describe intended product purpose and system boundaries here; keep file-by-file details and exact runtime behavior in `architecture.md`.
- Keep commands and task procedures in setup guides and runbooks.
- Keep test results, migrations observed, hosted checks, and other time-sensitive evidence in `project-ops/STATUS.md`, with dates and explicit scope.
- Keep requirements distinct from implementation and verification.
- When evidence is incomplete, label it unknown or partial rather than filling gaps with assumptions.
