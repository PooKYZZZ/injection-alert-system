# Architecture Document: Injection Alert System

This document outlines the system architecture, design principles, and deployment model for the Injection Alert System, a hybrid Web Application Firewall (WAF) and Machine Learning (ML) triage platform designed to detect and mitigate SQL injection attacks.

## System Overview
The architecture is designed around four core principles:
1. **CRS-first enforcement hierarchy**: ModSecurity and OWASP Core Rule Set (CRS) evaluate every incoming request. The ML layer functions exclusively as a triage gate for flagged traffic; it does not replace rule-based detection or inspect benign traffic.
2. **Clean Architecture layering**: The FastAPI backend adheres to Clean Architecture, cleanly separating `domain`, `application`, `infrastructure`, and `presentation` layers. Outer layers depend on inner layers, enforcing strict separation of concerns.
3. **ML lifecycle separation**: The machine learning ecosystem is structurally decoupled. Training, inference, retraining, and model export are distinct, non-overlapping pipeline stages rather than a monolithic process.
4. **Observability as a first-class concern**: Telemetry, metrics, and alert rules are explicitly defined as named architectural components, completely segregated from runtime application logs.

## High-Level Request Flow
```text
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
│  ModSecurity +    │  ← Primary Enforcement Layer
│  OWASP CRS        │    Matches CRS rules → outputs (PASS / BLOCK)
└────────┬──────────┘
         │
    CRS: PASS or BLOCK
         │
         ▼
┌───────────────────┐
│  FastAPI Backend  │  ← Confidence-Gating Layer
│  (Triage Engine)  │    Triggers ML inference for flagged requests
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  Transformer ML   │  ← Secondary Scoring Layer
│  Model (Inference)│    Outputs label + normalized confidence score
└────────┬──────────┘
         │
    Confidence Gate
    ┌────┴─────────────────────────┐
    │                              │
HIGH / MEDIUM confidence      LOW confidence
    │                              │
    ▼                              ▼
Auto-Mitigation              Human Review Queue
(BLOCK enforced/logged)      (Logged, flagged, held for manual SOC review)
    │                              │
    └──────────────┬───────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │  Supabase (PG)  │  ← Audit Log: Immutable record of all decisions
         │  Audit Log      │
         └─────────────────┘
```

## Confidence Gate Enforcement Logic
The confidence gate utilizes a deterministic, tiered logic structure to reduce false positives without degrading threat coverage. 

| Confidence Level | Threshold | Action |
|---|---|---|
| **HIGH** | > 80% | Automated block enforced |
| **MEDIUM** | 50% – 80% | Logged, conditional block (environment-dependent) |
| **LOW** | < 50% | Routed to human review queue (logged & held) |

- **Mitigation Handling:** Only HIGH and (optionally) MEDIUM traffic is subjected to automated blocking. LOW confidence requests bypass automated mitigation entirely and are funneled into a dedicated Human Review Queue for SOC operator review.

## ML Lifecycle Architecture
The machine learning component requires physical and operational segregation across its lifecycle:
1. **Preprocessing** (`ml_model/preprocessing/`): Raw datasets are sanitized, tokenized, and engineered into features. Raw data remains immutable.
2. **Training** (`ml_model/training/`): The transformer model is trained on balanced data; hyperparameters are drawn from configuration.
3. **Inference** (`ml_model/inference/`): Loaded into the FastAPI runtime to execute low-latency probabilistic scoring.
4. **Retraining** (`ml_model/retraining/`): A daily scheduled 20-day periodic pipeline that accumulates hold-out traffic and retrains fresh model weights.
5. **Export** (`ml_model/export/`): Newly trained models are serialized into standalone artifacts for evaluation bounding.

## Model Registry and Promotion Flow
Model artifacts are deliberately isolated from runtime loading until explicitly promoted.

**Promotion Path:**
```text
ml_model/export/  →  model_registry/staging/  →  model_registry/production/
    (exported)          (evaluation window)           (live-serving slot)
```
Each iteration yields a manifest file (`model_registry/manifests/`) logging `eval_f1`, training dates, exact dataset fingerprints, and the `rollback_target`. Rollbacks are instantaneous slot-swaps governed by manifest targets, completely independent of re-training execution.

## Repository Mapping
The system maps its directory structure tightly to its architectural role:

- `web_app/domain/` → Core entities and business rules natively untouched by FastAPI logic.
- `web_app/application/` → Use-case orchestration.
- `web_app/infrastructure/` → Database adapters (Supabase/PostgreSQL), external model loader integrations, repos.
- `web_app/presentation/` → FastAPI routers, dependencies, and HTTP Pydantic schemas.

## Observability Architecture
Located in `observability/`, monitoring is handled via:
- **Metrics**: Prometheus configurations scraping model drift, absolute request rates, rule-flag ratios, and retraining queue lengths.
- **Alerts**: Rules triggered by sustained false-positive variance, confidence miscalibration alerts, or audit-log write gaps.
- **Dashboards**: Grafana JSON panels tracking live threat distributions independently from standard system logs (held in `logs/`).

## Deployment Architecture
Optimized for multi-container orchestration:
- **Ingress**: Nginx terminating TLS.
- **WAF**: ModSecurity compiled explicitly as an Nginx dynamic module.
- **Application Server**: FastAPI via Uvicorn, orchestrated by Docker Compose.
- **Database**: Supabase (PostgreSQL) maintaining immutable audit tables.
- **Automation**: Docker Compose manages provisioning, environment overlays, and container lifecycle orchestration.

## Security Boundaries
- **Immutable Audit Logging**: The Supabase (Postgres) schema enforces append-only policies via Row Level Security (RLS) and strict role grants, preventing `UPDATE` or `DELETE` operations from the backend service role.
- **Environment Isolation**: DetectionOnly mode vs Enforcement mode is dictated entirely by deployment YAML keys.
- **Write-Protected Slots**: The `model_registry/production/` slot is write-protected from the active web application, guaranteeing inference runtimes cannot accidentally modify local model weights.
- **Dependency Guardrails**: No synchronous database drivers (e.g., standard SQLAlchemy/SQLite) are permitted to avoid blocking ASGI asynchronous event loops.
