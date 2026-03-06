# Structural Audit Report — Injection Alert System

**Date:** 2026-02-26  
**Scope:** Full structural audit across 8 evaluation dimensions  
**Auditor Perspective:** Enterprise Security Systems Architect / DevSecOps Reviewer

---

## 1. Overall Structural Grade: **D+**

The project has a valid foundation — a working FastAPI scaffold with Pydantic schemas, SQLAlchemy ORM, a mock inference stub, organized tests, and a CI pipeline. However, **the vast majority of the documented architecture does not exist in code**. The gap between what the documentation describes (hybrid CRS + ML enforcement, Ansible automation, retraining pipeline, dashboard frontend, LLM explanations) and what actually exists (a single-service REST API with a regex-based mock classifier) is severe.

---

## 2. Strengths in Project Structure

| # | Strength | Evidence |
|---|----------|----------|
| 1 | **Clean backend scaffold** | [app.py](file:///G:/Documents/PDDDD/injection-alert-system/web_app/app.py) uses FastAPI lifespan, modular router inclusion, proper CORS middleware |
| 2 | **Proper configuration management** | [config.py](file:///G:/Documents/PDDDD/injection-alert-system/web_app/config.py) uses `pydantic-settings` with `.env` isolation and environment-aware properties |
| 3 | **Schema-first API design** | [schemas.py](file:///G:/Documents/PDDDD/injection-alert-system/web_app/schemas.py) defines typed request/response models with field validation and examples |
| 4 | **Confidence-gated action logic** | [routes.py](file:///G:/Documents/PDDDD/injection-alert-system/web_app/api/routes.py) implements BLOCKED/THROTTLED/ALLOWED decisions based on confidence level — the core triage concept works |
| 5 | **Mock model with clean interface** | [mock_model.py](file:///G:/Documents/PDDDD/injection-alert-system/ml_model/models/mock_model.py) is designed for easy swapping to a real model (documented in docstring) |
| 6 | **Reasonable test coverage** | 6 test files covering API routes, config, database, mock model, and schemas with session-scoped fixtures |
| 7 | **Data directory convention** | `data/{raw,interim,processed,external}` follows the cookiecutter data-science standard |
| 8 | **CI pipeline exists** | [ci.yml](file:///G:/Documents/PDDDD/injection-alert-system/.github/workflows/ci.yml) runs pytest on push/PR against master |
| 9 | **Well-organized .gitignore** | Properly excludes `.env`, `__pycache__`, ML artifacts (`*.pt`, `*.h5`, `*.onnx`), data dirs, logs, and IDE files |
| 10 | **Rich documentation ecosystem** | `plans/` (9 checklists + README), [CONTEXT.md](file:///G:/Documents/PDDDD/CONTEXT.md), [feasibility_report.md](file:///G:/Documents/PDDDD/feasibility_report.md), and 10 files in `plans/` cover academic and technical dimensions |

---

## 3. Missing Structural Components

> [!CAUTION]
> These are files, directories, or modules that should exist based on the documented architecture but are **completely absent** from the repository.

### 3.1 — ML / Inference Layer

| Missing Component | Expected Path | Impact |
|---|---|---|
| Real model training script | `ml_model/training/train.py` | No training code exists anywhere |
| Training configuration | `ml_model/training/config.yaml` | No hyperparameters, epochs, LR schedules |
| Data preprocessing pipeline | `ml_model/preprocessing/` | No tokenization, label encoding, or data loading |
| Model evaluation scripts | `ml_model/evaluation/` | No metrics computation, confusion matrix, or reporting |
| ONNX export script | `ml_model/export/export_onnx.py` | [requirements.txt](file:///G:/Documents/PDDDD/injection-alert-system/requirements.txt) lists `onnx`/`onnxruntime`/`optimum` but no export code |
| Real inference service | `ml_model/inference/predictor.py` | Only [mock_model.py](file:///G:/Documents/PDDDD/injection-alert-system/tests/test_mock_model.py) exists; no transformer-based inference |
| Model registry / versioning | `ml_model/registry/` or `model_registry/` | No model version tracking, no `model_version` population in DB |
| Tokenizer artifacts location | `ml_model/tokenizers/` | No tokenizer config or cached tokenizer |

### 3.2 — ModSecurity / CRS Integration

| Missing Component | Expected Path | Impact |
|---|---|---|
| ModSecurity configuration | `config/modsecurity/` | No CRS rules, no modsecurity.conf |
| Log bridge / parser | `services/log_bridge/` or `web_app/log_parser.py` | No ModSecurity audit log ingestion |
| CRS rule management | `config/crs/` | Documented as CRS-first enforcement, but no CRS artifacts |

### 3.3 — Automation / Ansible

| Missing Component | Expected Path | Impact |
|---|---|---|
| Ansible playbooks | `ansible/playbooks/` | `ansible/` contains only [.gitkeep](file:///G:/Documents/PDDDD/injection-alert-system/data/.gitkeep) |
| Ansible roles | `ansible/roles/` | No role-based structure |
| Inventory files | `ansible/inventory/{dev,staging,prod}` | No environment separation |
| Mitigation orchestrator playbooks | `ansible/playbooks/mitigate.yml` | Documented automated response has no implementation |
| Rollback playbooks | `ansible/playbooks/rollback.yml` | No rollback strategy |

### 3.4 — Frontend / Dashboard

| Missing Component | Expected Path | Impact |
|---|---|---|
| Dashboard application | `frontend/` or `dashboard/` | Entire frontend is absent |
| Alert visualization | — | No UI for viewing alerts, confidence distributions, or audit trails |

### 3.5 — Deployment / Infrastructure

| Missing Component | Expected Path | Impact |
|---|---|---|
| Dockerfile(s) | `Dockerfile`, `docker-compose.yml` | No containerization |
| systemd service files | `deploy/systemd/` | No production process management |
| Nginx configuration | `deploy/nginx/` | Documented Nginx reverse proxy has no config |
| SSL certificate management | `deploy/ssl/` or `deploy/nginx/ssl/` | No SSL setup |
| Production vs dev config split | `config/environments/` | Single [.env.example](file:///G:/Documents/PDDDD/injection-alert-system/.env.example) for all environments |
| Database migrations | `migrations/` or `alembic/` | Uses `create_all()` — no schema migration tooling |

### 3.6 — Retraining Pipeline

| Missing Component | Expected Path | Impact |
|---|---|---|
| Scheduled retraining job | `ml_model/retraining/` | Documented 20-day pipeline has no code |
| Data staging for retraining | `data/staging/` | No mechanism to collect feedback data for retraining |
| Validation gating | `ml_model/retraining/validate.py` | No champion/challenger model comparison |
| Retraining artifacts store | `artifacts/retraining/` | No versioned outputs from retraining runs |

### 3.7 — Observability

| Missing Component | Expected Path | Impact |
|---|---|---|
| Structured logging config | `web_app/logging_config.py` | No structured logging; uses default Python logging |
| Metrics endpoint / exporter | `web_app/metrics.py` | No Prometheus/StatsD metrics |
| Action audit log | `logs/audit/` structure | `action_taken` in DB but no dedicated audit trail |
| Alerting configuration | `config/alerting/` | No PagerDuty/Slack/email alert integration |

### 3.8 — Security Hardening

| Missing Component | Expected Path | Impact |
|---|---|---|
| API authentication middleware | `web_app/middleware/auth.py` | `API_SECRET_KEY` exists in config but is **never used** in routes |
| Rate limiting | `web_app/middleware/rate_limit.py` | No rate limiting on `/api/predict` |
| Input sanitization layer | — | Raw `http_request` string passed directly to model |
| Secrets management | `deploy/vault/` or `deploy/secrets/` | Secrets in `.env` with no vault integration plan |

---

## 4. Structural Risks & Architectural Smells

> [!WARNING]
> These are issues in the existing code that would cause problems in production even without adding new components.

### 🔴 Critical

| # | Risk | Location | Detail |
|---|------|----------|--------|
| 1 | **[test.db](file:///G:/Documents/PDDDD/injection-alert-system/test.db) committed to repo** | [test.db](file:///G:/Documents/PDDDD/injection-alert-system/test.db) (20KB) | SQLite test database is tracked in Git despite `*.db` in [.gitignore](file:///G:/Documents/PDDDD/injection-alert-system/.gitignore). Must be removed via `git rm --cached`. |
| 2 | **CORS allows all origins** | [app.py:41](file:///G:/Documents/PDDDD/injection-alert-system/web_app/app.py#L41) | `allow_origins=["*"]` with `allow_credentials=True` is a security vulnerability. |
| 3 | **API_SECRET_KEY defined but unused** | [config.py:12](file:///G:/Documents/PDDDD/injection-alert-system/web_app/config.py#L12) | The key is loaded but never applied as middleware — all endpoints are unauthenticated. |
| 4 | **No database migrations** | [database.py:43](file:///G:/Documents/PDDDD/injection-alert-system/web_app/database.py#L43) | `Base.metadata.create_all()` is not suitable for production schema evolution. |
| 5 | **Model instantiated twice** | [app.py:19](file:///G:/Documents/PDDDD/injection-alert-system/web_app/app.py#L19), [routes.py:16](file:///G:/Documents/PDDDD/injection-alert-system/web_app/api/routes.py#L16) | [MockInjectionClassifier()](file:///G:/Documents/PDDDD/injection-alert-system/ml_model/models/mock_model.py#12-118) created in both [app.py](file:///G:/Documents/PDDDD/injection-alert-system/web_app/app.py) and [routes.py](file:///G:/Documents/PDDDD/injection-alert-system/web_app/api/routes.py) — the one in [app.py](file:///G:/Documents/PDDDD/injection-alert-system/web_app/app.py) is unused. |
| 6 | **MODEL_PATH points to .py file** | [.env.example:4](file:///G:/Documents/PDDDD/injection-alert-system/.env.example#L4) | `MODEL_PATH=ml_model/models/mock_model.py` — should point to a model artifact (`.pt`, `.onnx`), not a Python source file. |

### 🟡 Moderate

| # | Risk | Location | Detail |
|---|------|----------|--------|
| 7 | **Hardcoded SQLite fallback** | [database.py:13](file:///G:/Documents/PDDDD/injection-alert-system/web_app/database.py#L13) | Falls back to `sqlite:///./test.db` in non-production — should use `DATABASE_URL` from env consistently. |
| 8 | **No README in `injection-alert-system/`** | — | Sub-project has no [README.md](file:///G:/Documents/PDDDD/checklists/README.md) with setup instructions. |
| 9 | **Flat requirements.txt** | [requirements.txt](file:///G:/Documents/PDDDD/injection-alert-system/requirements.txt) | No separation of dev/test/production dependencies. `torch`, `tensorboard`, and `matplotlib` included in the same file as `fastapi`. |
| 10 | **No `__pycache__` in [.gitignore](file:///G:/Documents/PDDDD/injection-alert-system/.gitignore) verification** | — | [.gitignore](file:///G:/Documents/PDDDD/injection-alert-system/.gitignore) excludes `__pycache__/` but `.pytest_cache/` directory exists in repo root. |

---

## 5. Recommended Ideal Directory Tree

```
injection-alert-system/
├── README.md                          # Project overview, setup, architecture diagram
├── .env.example                       # Environment variable template
├── .gitignore
├── pytest.ini
├── requirements/                      # ← Split dependencies
│   ├── base.txt                       #   Core runtime deps
│   ├── dev.txt                        #   Testing, linting, formatting
│   ├── ml.txt                         #   PyTorch, transformers, ONNX
│   └── production.txt                 #   Gunicorn, psycopg2, etc.
│
├── .github/
│   └── workflows/
│       ├── ci.yml                     # Lint + unit tests
│       ├── cd.yml                     # Deploy to staging/prod
│       └── retrain.yml                # Scheduled retraining trigger
│
├── config/
│   ├── environments/
│   │   ├── development.env
│   │   ├── staging.env
│   │   └── production.env
│   ├── modsecurity/
│   │   ├── modsecurity.conf
│   │   └── crs-setup.conf
│   └── crs/
│       └── REQUEST-900-EXCLUSION.conf
│
├── web_app/                           # FastAPI backend
│   ├── __init__.py
│   ├── app.py                         # Application factory
│   ├── config.py                      # Pydantic settings
│   ├── database.py                    # SQLAlchemy models + session
│   ├── schemas.py                     # Pydantic request/response
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                  # Predict, alerts, feedback
│   │   └── dependencies.py            # Shared deps (model, DB)
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                    # API key / JWT middleware
│   │   └── rate_limit.py              # Rate limiting
│   ├── services/
│   │   ├── __init__.py
│   │   ├── mitigation.py              # Confidence-gated action logic
│   │   └── log_bridge.py              # ModSecurity log parser
│   └── logging_config.py              # Structured logging setup
│
├── ml_model/                          # ML component
│   ├── __init__.py
│   ├── inference/
│   │   ├── __init__.py
│   │   ├── predictor.py               # Real model inference (ONNX/PyTorch)
│   │   └── mock_model.py              # Pattern-based stub (testing)
│   ├── training/
│   │   ├── __init__.py
│   │   ├── train.py                   # Training loop
│   │   ├── config.yaml                # Hyperparameters
│   │   └── evaluate.py                # Metrics computation
│   ├── preprocessing/
│   │   ├── __init__.py
│   │   ├── tokenize.py                # Tokenization pipeline
│   │   └── dataset.py                 # Dataset loading / splits
│   ├── export/
│   │   └── export_onnx.py             # ONNX conversion script
│   └── retraining/
│       ├── retrain.py                 # Retraining entry point
│       ├── validate.py                # Champion/challenger gating
│       └── schedule.py                # Cron/timer configuration
│
├── model_registry/                    # Versioned model artifacts
│   ├── v1/
│   │   ├── model.onnx
│   │   ├── tokenizer_config.json
│   │   └── metadata.json              # Training date, metrics, dataset hash
│   └── latest -> v1/
│
├── data/
│   ├── raw/                           # Original dataset (gitignored)
│   ├── interim/                       # Intermediate processing
│   ├── processed/                     # Final training-ready data
│   ├── external/                      # Third-party reference data
│   └── staging/                       # Feedback data for retraining
│
├── ansible/
│   ├── ansible.cfg
│   ├── inventory/
│   │   ├── dev.yml
│   │   ├── staging.yml
│   │   └── production.yml
│   ├── playbooks/
│   │   ├── deploy.yml                 # Full deployment
│   │   ├── mitigate.yml               # Automated mitigation actions
│   │   ├── rollback.yml               # Rollback to previous state
│   │   └── retrain.yml                # Trigger retraining pipeline
│   ├── roles/
│   │   ├── nginx/
│   │   ├── modsecurity/
│   │   ├── fastapi_app/
│   │   ├── postgresql/
│   │   └── ssl/
│   └── group_vars/
│       ├── all.yml
│       └── production.yml
│
├── deploy/
│   ├── systemd/
│   │   ├── injection-alert-api.service
│   │   └── injection-alert-ml.service
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── sites-available/
│   │       └── injection-alert.conf
│   ├── ssl/
│   │   └── README.md                  # Certificate management instructions
│   └── docker/                        # Optional containerization
│       ├── Dockerfile.api
│       ├── Dockerfile.ml
│       └── docker-compose.yml
│
├── migrations/                        # Alembic database migrations
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│
├── frontend/                          # Dashboard UI
│   ├── package.json
│   ├── src/
│   └── public/
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_schemas.py
│   │   ├── test_mock_model.py
│   │   └── test_database.py
│   ├── integration/
│   │   ├── test_api.py
│   │   ├── test_log_bridge.py
│   │   └── test_mitigation_flow.py
│   └── e2e/
│       └── test_full_pipeline.py
│
├── logs/                              # Runtime logs (gitignored)
│   ├── app/
│   ├── audit/                         # Action audit trail
│   └── modsecurity/
│
└── docs/
    ├── ARCHITECTURE.md                # System architecture overview
    ├── API_REFERENCE.md               # OpenAPI docs pointer
    ├── DEPLOYMENT.md                  # Production deployment guide
    ├── RETRAINING.md                  # Retraining pipeline docs
    └── SECURITY.md                    # Hardening checklist
```

---

## 6. Dimension-by-Dimension Evaluation

### 6.1 Repository Structure — Grade: **C+**

| Criterion | Status |
|---|---|
| Modular separation | ✅ `web_app/`, `ml_model/`, `tests/`, [data/](file:///G:/Documents/PDDDD/injection-alert-system/tests/conftest.py#18-37) exist as separate packages |
| Clear directory hierarchy | ⚠️ Flat within each package; no sub-modules for services/middleware |
| Inference vs training separation | ❌ No training code exists; `ml_model/` contains only mock inference |
| Infrastructure-as-code placement | ❌ `ansible/` is empty |
| Environment config isolation | ⚠️ Single [.env.example](file:///G:/Documents/PDDDD/injection-alert-system/.env.example) for all environments |

### 6.2 Service Layer Architecture — Grade: **D**

| Criterion | Status |
|---|---|
| CRS layer boundary | ❌ No ModSecurity/CRS code or configuration |
| Log bridge | ❌ No log parser or ingestion service |
| ML inference boundary | ⚠️ Mock model works but is directly imported into routes — no service abstraction |
| Mitigation orchestrator | ⚠️ Inline confidence-gating in [routes.py](file:///G:/Documents/PDDDD/injection-alert-system/web_app/api/routes.py) — not separated into a service |
| Database logging | ✅ Properly implemented with SQLAlchemy ORM |
| Decoupling | ❌ Inference tied directly to [routes.py](file:///G:/Documents/PDDDD/injection-alert-system/web_app/api/routes.py) via import — no dependency injection |

### 6.3 Automation & Infrastructure — Grade: **F**

| Criterion | Status |
|---|---|
| Ansible structure | ❌ Empty directory with [.gitkeep](file:///G:/Documents/PDDDD/injection-alert-system/data/.gitkeep) |
| Role-based playbooks | ❌ None |
| Inventory separation | ❌ None |
| Idempotency | ❌ N/A |
| Rollback strategy | ❌ None |

### 6.4 Deployment Readiness — Grade: **F**

| Criterion | Status |
|---|---|
| systemd service files | ❌ None |
| Environment variable management | ⚠️ [.env.example](file:///G:/Documents/PDDDD/injection-alert-system/.env.example) exists but no per-environment configs |
| Secrets handling | ❌ Plaintext in `.env`, no vault integration |
| SSL setup | ❌ None |
| Production vs dev configs | ⚠️ [config.py](file:///G:/Documents/PDDDD/injection-alert-system/web_app/config.py) has env-aware properties but no actual prod config files |

### 6.5 Observability & Auditability — Grade: **D-**

| Criterion | Status |
|---|---|
| Log directories | ❌ None ([.gitignore](file:///G:/Documents/PDDDD/injection-alert-system/.gitignore) references `logs/` but directory doesn't exist) |
| Action audit storage | ⚠️ `action_taken` column in [TrafficLog](file:///G:/Documents/PDDDD/injection-alert-system/web_app/database.py#22-39) but no dedicated audit trail |
| Model version tracking | ⚠️ `model_version` column exists in schema but is always `NULL` |
| Retraining artifacts | ❌ None |
| Metrics collection | ❌ No Prometheus/StatsD/custom metrics |

### 6.6 CI/CD & Versioning — Grade: **D+**

| Criterion | Status |
|---|---|
| Model versioning scheme | ❌ None |
| Deployment automation | ❌ No CD pipeline |
| Testing folder structure | ⚠️ Flat `tests/` — no unit/integration/e2e separation |
| Integration vs unit tests | ❌ All tests in the same directory with no categorization |
| CI pipeline | ✅ [ci.yml](file:///G:/Documents/PDDDD/injection-alert-system/.github/workflows/ci.yml) runs pytest on push/PR |

### 6.7 Retraining Pipeline Organization — Grade: **F**

| Criterion | Status |
|---|---|
| Scheduled job structure | ❌ None |
| Data staging | ❌ [data/](file:///G:/Documents/PDDDD/injection-alert-system/tests/conftest.py#18-37) subdirs exist but are empty and gitignored |
| Model registry | ❌ None |
| Validation gating | ❌ None |

### 6.8 Security Hardening Structure — Grade: **D-**

| Criterion | Status |
|---|---|
| Permission separation | ❌ No auth middleware despite `API_SECRET_KEY` in config |
| Firewall integration isolation | ❌ No ModSecurity/CRS code |
| No permanent CRS mutation | N/A (no CRS code to evaluate) |
| Safe automation boundary | ❌ No mitigation safeguards, no dry-run mode, no rollback |
| CORS | ❌ Wildcard origins with credentials allowed |

---

## 7. Enterprise-Readiness Verdict

### **NOT YET**

**Reasoning:**

The project is in an **early scaffold phase** — roughly 10-15% of the documented architecture has been implemented. What exists (FastAPI + mock model + tests + CI) is competently built and follows reasonable conventions, but the system described in the feasibility report and CONTEXT.md is orders of magnitude more complex than what is present in the repository.

**Specifically, the project cannot be considered production-ready because:**

1. **No real ML inference exists.** The entire ML pipeline — training, evaluation, export, inference — is absent. Only a regex-based mock.
2. **No WAF integration exists.** The "CRS-first hybrid enforcement" that defines the system's identity has zero code or configuration.
3. **No automation exists.** The Ansible directory is empty. No deployment playbooks, no mitigation orchestration, no rollback.
4. **No deployment infrastructure exists.** No systemd, no Nginx, no Docker, no SSL, no database migrations.
5. **No observability exists.** No structured logging, no metrics, no audit trail beyond a DB column.
6. **No frontend exists.** The documented dashboard is entirely absent.
7. **Unauthenticated API with wildcard CORS** — the existing code has security anti-patterns that would be exploitable in production.

> [!IMPORTANT]
> The project has a solid *skeleton* and good documentation habits. The path from current state to production readiness is achievable if the sprint plan in [plans/combined.md](file:///G:/Documents/PDDDD/plans/combined.md) is executed systematically. The most critical immediate priorities should be:
> 1. Build the real inference service (replace mock with transformer/ONNX predictor)
> 2. Add authentication middleware and fix CORS
> 3. Create at minimum one Ansible deployment playbook
> 4. Stand up database migrations with Alembic
> 5. Separate test directories into unit/integration

---

*End of audit. This report evaluates structural completeness only and makes no claims about model quality, dataset adequacy, or algorithmic performance.*
