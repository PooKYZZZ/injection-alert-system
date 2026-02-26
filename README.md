# Injection Alert System

A hybrid, CRS-first WAF + ML confidence-gated triage platform designed for SQL injection detection and automated mitigation on a single-server Ubuntu deployment.

---

## Project Overview

The Injection Alert System is a cybersecurity research prototype that integrates ModSecurity with the OWASP Core Rule Set (CRS) as the primary enforcement layer, augmented by a transformer-based machine learning triage model as a secondary confidence layer. The system's primary contribution is reducing false-positive enforcement rates inherent in rule-based WAF systems by conditioning automated blocking decisions on ML confidence scores above a defined threshold.

This system is designed for academic capstone defense and production-oriented evaluation. It is not currently deployed in a live production environment.

**Primary Contribution:** ML-assisted confidence gating over OWASP CRS enforcement to reduce false-positive blocking without compromising detection coverage.

---

## Architectural Principles

The repository architecture follows four governing principles:

1. **CRS-first enforcement hierarchy** — ModSecurity and OWASP CRS evaluate every request before ML inference is invoked. The ML layer is a triage gate, not a replacement for rule-based detection.
2. **Clean Architecture layering** — The FastAPI backend is organized into `domain`, `application`, `infrastructure`, and `presentation` sub-packages with enforced dependency direction: outer layers depend on inner layers, never the reverse.
3. **ML lifecycle separation** — Training, inference, retraining, and model export are structurally distinct pipeline stages, not co-located processes.
4. **Observability as a first-class concern** — Metrics, alert rules, and dashboards are represented as named architectural components, not runtime afterthoughts.

---

## System Architecture

### High-Level Request Flow

```
Incoming HTTP Request
        │
        ▼
┌───────────────────┐
│  Nginx (Reverse   │
│  Proxy + TLS)     │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  ModSecurity +    │  ← Primary enforcement layer
│  OWASP CRS        │    Rule match → CRS decision (PASS / BLOCK)
└────────┬──────────┘
         │
    CRS: PASS or BLOCK
         │
         ▼
┌───────────────────┐
│  FastAPI Backend  │  ← Confidence-gating layer
│  (Triage Engine)  │    Invokes ML inference on flagged requests
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Transformer ML   │  ← Secondary scoring layer
│  Model (Inference)│    Outputs: label + confidence score
└────────┬──────────┘
         │
    Confidence Gate
    ┌────┴─────────────────────────┐
    │                              │
HIGH / MEDIUM confidence      LOW confidence
    │                              │
    ▼                              ▼
Auto-mitigation              Human Review Queue
(BLOCK enforced)             (logged, flagged, held)
    │                              │
    └──────────────┬───────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  PostgreSQL      │  ← Audit log: every decision recorded
         │  Audit Log       │
         └─────────────────┘
```

### Confidence Gate Tiers

| Confidence Level | Threshold | Action |
|---|---|---|
| HIGH | ≥ 0.92 (production) | Automated block enforced |
| MEDIUM | 0.85 – 0.91 | Logged, conditional block |
| LOW | < 0.85 | Routed to human review queue |

Thresholds are environment-specific and declared in `config/environments/`.

---

## Repository Structure

```
injection-alert-system/
│
├── pyproject.toml              # PEP 517/518 packaging, tool, and test config
├── requirements.txt            # Pinned runtime dependency manifest
├── .env.example                # Environment variable schema reference
│
├── config/                     # Static configuration boundary
│   ├── modsecurity/            # ModSecurity engine directives
│   ├── crs/                    # OWASP CRS rule overrides and exclusions
│   └── environments/           # Environment-specific parameter files
│       ├── dev.yaml            # DetectionOnly mode, gate disabled
│       ├── staging.yaml        # Enforcement mode, staging model slot
│       └── production.yaml     # Full enforcement, production slot only
│
├── web_app/                    # FastAPI backend (Clean Architecture)
│   ├── domain/                 # Core entities and value objects
│   ├── application/            # Use case orchestration
│   ├── infrastructure/         # DB adapters, model loader, repositories
│   └── presentation/           # FastAPI routers, middleware, HTTP schemas
│
├── ml_model/                   # Full ML lifecycle boundary
│   ├── preprocessing/          # Data cleaning, tokenization, feature engineering
│   ├── training/               # Training loop and hyperparameter configuration
│   ├── models/                 # In-development model checkpoints
│   ├── inference/              # Inference pipeline and confidence scoring
│   ├── retraining/             # 20-day periodic retraining pipeline
│   └── export/                 # Serialized model artifacts (pre-registry)
│
├── model_registry/             # Versioned model promotion boundary
│   ├── manifests/              # Per-version metadata (F1, threshold, rollback target)
│   ├── staging/                # Candidate model under evaluation window
│   └── production/             # Active production artifact (validated only)
│
├── data/                       # Data pipeline boundary
│   ├── raw/                    # Immutable original dataset
│   ├── interim/                # Cleaned intermediate data
│   ├── processed/              # Model-ready final dataset
│   ├── external/               # Third-party data sources
│   └── staging/                # 20-day retraining accumulation window
│
├── observability/              # First-class observability layer
│   ├── metrics/                # Prometheus scrape config, metric definitions
│   ├── alerts/                 # Alert rules: confidence breach, drift, rollback
│   └── dashboards/             # Grafana panels: threat view, review queue, retraining tracker
│
├── ansible/                    # IaC automation (Ansible Galaxy layout)
│   ├── inventory/
│   ├── group_vars/
│   ├── playbooks/
│   └── roles/
│
├── deploy/                     # Runtime delivery artifacts
│   ├── nginx/                  # Nginx virtual host and proxy config
│   ├── ssl/                    # TLS certificate paths and configuration
│   └── systemd/                # Systemd unit files for service management
│
├── tests/                      # Strictly tiered test pyramid
│   ├── unit/                   # Pure function tests, all I/O mocked
│   ├── integration/            # Cross-component tests with real DB session
│   └── e2e/                    # Full system path, full environment required
│
├── migrations/                 # Alembic schema version control
├── docs/                       # Extended architecture and design documentation
├── frontend/                   # Human-in-the-loop review dashboard
└── logs/                       # Runtime log output (not an observability layer)
```

---

## ML Lifecycle Design

The machine learning component follows a structured, stage-separated lifecycle:

1. **Preprocessing** (`ml_model/preprocessing/`) — Raw log data is cleaned, tokenized, and feature-engineered into the canonical input format expected by the transformer model. Raw data is never modified in place.
2. **Training** (`ml_model/training/`) — The transformer model is trained on a balanced dataset (equal injection / benign class distribution). Hyperparameters are configuration-driven, not hardcoded.
3. **Inference** (`ml_model/inference/`) — At request time, the inference pipeline loads the production-slot model artifact and returns a `{label, confidence_score}` result within the request cycle.
4. **Retraining** (`ml_model/retraining/`) — A 20-day periodic retraining pipeline re-trains the model on accumulated traffic data from `data/staging/`. Retraining does not modify the production-slot artifact directly.
5. **Export** (`ml_model/export/`) — Successfully retrained models are serialized and exported to `model_registry/staging/` for evaluation gate processing.

---

## Model Versioning & Rollback Strategy

The `model_registry/` directory is the versioned model promotion boundary. A model artifact moves through a defined promotion path and is never deployed directly from `ml_model/export/`.

### Promotion Path

```
ml_model/export/  →  model_registry/staging/  →  model_registry/production/
    (exported)          (evaluation window)           (live-serving artifact)
```

### Manifest Schema

Each model version is recorded in `model_registry/manifests/` as a structured metadata file containing:

- `version` — unique version identifier
- `training_date` — timestamp of the completed training run
- `dataset_fingerprint` — hash of the dataset used for training
- `eval_f1`, `eval_precision`, `eval_recall` — evaluation metrics on the held-out test set
- `confidence_threshold_used` — gate threshold validated during evaluation
- `promoted_by` — identity of the reviewer approving promotion
- `rollback_target` — version identifier of the previous production artifact

### Rollback Procedure

Rollback is performed by replacing the `production/` slot contents with the artifact identified by the current manifest's `rollback_target` field. No retraining is required; rollback is a slot-swap operation traceable to the manifest ledger.

---

## Confidence-Gated Mitigation Logic

The confidence gate is the system's primary mechanism for reducing false-positive enforcement.

### Decision Logic

```
CRS Decision: BLOCK
       │
       ▼
  ML Inference
       │
  confidence_score
       │
  ┌────┴─────────────────────────────┐
  │                                  │
score ≥ HIGH threshold        score < MEDIUM threshold
  │                                  │
  ▼                                  ▼
Auto-block enforced           Human review queue
(full mitigation)             (no automated action)
```

- **High confidence:** CRS-flagged request is auto-blocked. The decision and evidence are written to the PostgreSQL audit log.
- **Medium confidence:** Logged and conditionally blocked depending on environment configuration.
- **Low confidence:** Request is held in a human review queue. No automated blocking is applied. A reviewer evaluates the flagged request through the dashboard.

Confidence thresholds are not hardcoded. They are declared per-environment in `config/environments/` and are adjustable without code changes.

### CRS-Only Requests

Requests not flagged by CRS do not invoke ML inference. This preserves performance and ensures the ML layer operates only within its intended scope — triage of ambiguous rule-matches, not blanket classification.

---

## Observability & Audit Design

The `observability/` directory is a named architectural layer, structurally distinct from the runtime `logs/` directory.

### Components

| Directory | Purpose |
|---|---|
| `observability/metrics/` | Prometheus scrape configuration: request rate, WAF block rate, ML confidence distribution, model drift indicators, retraining pipeline status |
| `observability/alerts/` | Alert rule definitions: confidence threshold breach, sustained false-positive rate elevation, retraining pipeline failure, audit log gap detection |
| `observability/dashboards/` | Dashboard definitions: live threat overview, confidence score histogram, 20-day retraining cycle tracker, human review queue depth and age |

### Audit Log

Every confidence-gate decision — automated block, conditional hold, or human review routing — is written as an immutable record to the PostgreSQL audit log. The schema captures:

- Request fingerprint
- CRS rule(s) matched
- ML label and confidence score
- Gate decision applied
- Timestamp and environment identifier

The audit log supports post-incident analysis, retraining data curation, and thesis evaluation evidence collection.

---

## Deployment Model

The system is designed for single-server deployment on Ubuntu with Nginx as the reverse proxy and TLS termination layer.

### Stack

| Component | Role |
|---|---|
| Ubuntu (LTS) | Host operating system |
| Nginx | Reverse proxy, TLS termination |
| ModSecurity (Nginx module) | WAF enforcement engine |
| OWASP CRS | Rule set loaded into ModSecurity |
| FastAPI (Uvicorn) | Application server |
| PostgreSQL | Persistent audit and alert log store |
| Systemd | Service lifecycle management |
| Ansible | Automated provisioning and configuration |

### Automation

`ansible/` follows the Ansible Galaxy project layout (`inventory/`, `group_vars/`, `playbooks/`, `roles/`). Provisioning, ModSecurity configuration deployment, model registry initialization, and service restart procedures are managed through Ansible playbooks rather than manual shell operations.

### Environment Promotion

Three YAML configuration files in `config/environments/` define the parameter set for each deployment context. The `MODEL_REGISTRY_SLOT` key in each file determines which registry slot (`staging` or `production`) the inference pipeline loads its artifact from, enabling slot-based environment promotion without code changes.

---

## Testing Strategy

The test suite follows a strictly tiered pyramid, enforcing that no test files reside at the `tests/` root level.

### Tiers

| Tier | Directory | Scope | CI Gate |
|---|---|---|---|
| Unit | `tests/unit/` | Pure function and class-level; all I/O mocked | Every commit |
| Integration | `tests/integration/` | Cross-component with real DB session and TestClient | PR merge |
| End-to-End | `tests/e2e/` | Full system path; full environment required | Release branch |

### Coverage Targets

- Unit tests target `web_app/domain/`, `web_app/application/`, and `ml_model/inference/`.
- Integration tests validate FastAPI endpoint behavior, database read/write correctness, and WAF configuration round-trips.
- E2E tests validate the complete request path: HTTP ingress → CRS decision → ML inference → confidence gate → audit log write.

Tool configuration for `pytest`, `coverage`, `black`, and `ruff` is consolidated in `pyproject.toml`.

---

## Security Considerations

- **No secrets in version control.** All credentials, database passwords, and API keys are referenced through environment variables. The `.env.example` file documents the required variable schema.
- **WAF in DetectionOnly mode for development.** `config/environments/dev.yaml` sets `WAF_MODE: DetectionOnly` to prevent accidental blocking during local development and testing.
- **Production model slot is write-protected by convention.** Only the Ansible provisioning playbook and the explicit promotion workflow write to `model_registry/production/`. Direct file writes to the production slot outside this workflow are considered a policy violation.
- **Audit log is append-only.** The PostgreSQL audit table schema enforces no-update, no-delete constraints, preserving the integrity of decision records for forensic analysis.
- **TLS enforced at Nginx.** Plaintext HTTP traffic is not accepted at the application layer; Nginx terminates TLS and proxies over a local socket.
- **Confidence threshold is not hardcoded.** Gate thresholds are declared in externalized YAML configuration, preventing threshold manipulation through code changes alone.

---

## Limitations & Scope

- This system is designed and evaluated as a **research prototype**. It has not undergone production security hardening, load testing, or third-party penetration testing.
- The ML model is trained and evaluated on a **controlled, balanced dataset**. Generalization to real-world traffic distributions has not been empirically validated.
- The transformer model targets **SQL injection detection only**. XSS, CSRF, path traversal, and other attack vectors are handled exclusively by CRS rules and are outside the ML scope.
- The confidence gate does not replace human judgment for low-confidence decisions. A human review queue is a required operational component, not an optional feature.
- Retraining runs **daily over a 20-day window** — each day a new training run is executed on accumulated traffic data from `data/staging/`. This is a scheduled daily pipeline, not a single trigger fired at day 20. Continuous drift-based triggering (outside the fixed window) is an identified future work item.
- The system assumes a **single-server deployment**. Horizontal scaling, distributed model serving, and multi-region replication are explicitly out of scope.

---

## Future Work

The following capabilities are identified as post-thesis (PD2) development targets:

- **Drift-triggered retraining** — Supplement the daily 20-day retraining window with Prometheus-alert-triggered invocations based on detected confidence distribution shift, enabling out-of-window retraining when drift is measurably elevated.
- **Expanded attack surface coverage** — Extend the ML triage model to score XSS and command injection patterns in addition to SQL injection.
- **Policy-as-code for CI** — Integrate IaC static analysis (e.g., Checkov) and SAST scanning into the GitHub Actions pipeline as named, staged workflow files.
- **Formal model evaluation gate** — Replace manual promotion approval with a structured gate: F1 ≥ threshold, precision ≥ threshold, no regression on held-out injection categories.
- **Full web_app/ layer migration** — Complete migration of legacy flat files (`api/`, `services/`, `schemas.py`, `database.py`) into the corresponding Clean Architecture sub-packages.

---

## Academic Context

This system was developed as the primary deliverable for a Bachelor of Science in Computer Engineering capstone research project (PD1/PD2 cycle). The research objective is to evaluate whether transformer-based ML confidence scoring can measurably reduce the false-positive enforcement rate of an OWASP CRS-governed ModSecurity WAF without reducing true-positive detection coverage.

All architectural decisions, experimental design parameters, and evaluation baselines are documented in `docs/` and the accompanying feasibility study.

---

## License

MIT License. See `LICENSE` for full terms.

This repository is made available for academic review and research reference. It is not licensed for production deployment without independent security evaluation.
