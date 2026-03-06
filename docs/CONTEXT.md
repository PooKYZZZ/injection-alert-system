# Project Context - Injection Alert Classification System

**Updated:** 2026-03-07 | **Defense:** May 2026 | **Team:** 13

---

## Project

**Title:** Deep Learning-Based Confidence Classification for Context-Aware Injection Alert

**Goal:** ML system detecting injection attacks with confidence levels (LOW <50% | MEDIUM 50-80% | HIGH >80%), automated actions, ModSecurity WAF integration, 20-day retraining pipeline.

---

## Academic Paper Status

| Chapter | Status | Notes |
|---------|--------|-------|
| Chapter 1: Project Background | ✅ Complete | All fixes applied |
| Chapter 2: Project Design | ✅ Complete | Ready for review |
| Chapter 3: Design Tradeoffs | ✅ Complete | MCDM analysis done |
| Chapter 4: Final Design | ❌ Pending | PD1 work to be reported |
| Chapter 5: Business Plan | ❌ Pending | - |

**Paper Output Location:** REFERENCES/output/

---

## Feasibility Report Status

| Section | Status |
|---------|--------|
| Problem Statement | ✅ Complete |
| Objectives (1-9) | ✅ Complete |
| Model Comparison | ✅ Complete |
| MCDM Decision Matrix | ✅ Complete |
| Standards Compliance | ✅ Complete |
| Confidence Threshold Rationale | ✅ Complete |
| Problem Statement Evidence | ✅ Complete |
| Gap Analysis | ✅ Complete |
| References | ✅ Complete |

**Standards Covered:** NIST SP 800-94, OWASP CRS v4.x, ISO/IEC 27035-1:2023, IEEE 829-2008, Python PEP-8

---

## Key Citations

**Dataset:**
- Sureda Riera et al. (2022) — SR-BH 2020 dataset (907,814 HTTP requests, 13 CAPEC categories)
- Sanhour et al. (2025) — WAMM framework (~10% mislabeling in benign class)

**Model Benchmarks:**
- Devlin et al. (2019) — BERT-base fine-tuning foundations
- Sanh et al. (2019) — DistilBERT compression strategy
- Wang et al. (2020) — MiniLM deep self-attention distillation
- Sanhour et al. (2025) — WAMM framework (Transformer superiority for web attacks)

**Confidence Thresholds:**
- Talpini et al. (2024) — Uncertainty quantification in ML-based IDS
- Yu et al. (2025) — Empirical confidence thresholds in safety-critical AI
- Gelman et al. (2023) — ML alert prioritization

---

## Tech Stack

| Component | Choice |
|-----------|--------|
| Frontend | Next.js 15 (App Router), TypeScript 5.x, Zustand, TanStack Query, Zod, shadcn/ui |
| ML Framework | PyTorch |
| Transformers | Hugging Face Transformers |
| Backend API | FastAPI (Python) |
| Database | Supabase (Managed Cloud PostgreSQL) |
| WAF | ModSecurity + OWASP CRS v4.x |
| Deployment | Docker Compose (3 containers), Ansible, Ubuntu Server, Nginx |

---

## Architecture & Security Setup

**Deployment Architecture (3 Containers):**
- **Container 1:** `owasp/modsecurity-crs:nginx` (Exposed to internet on port 80/443; route reverse proxy)
- **Container 2:** FastAPI + PyTorch models (Internal network only)
- **Container 3:** Next.js 15 (Internal network only)

**Frontend Specifications (11 Pages):**
- Full multi-page application encompassing SOC Dashboard, Alert History, Incident Detail, Mitigation Log, ML Health, Traffic, Reports, Audit Trail, Settings, Admin, and Login.

**Security Isolation Constraints:**
- Browser **NEVER** calls FastAPI or Groq API directly. Proxy flow: Browser → Next.js Route Handler → FastAPI/Groq.
- Core Secrets (`GROQ_API_KEY`, `DATABASE_URL`) stored solely in Next.js server-side / FastAPI `.env` files.
- NextAuth v5 JWT handles role-based access (analyst vs admin) in httpOnly cookies.
- All intercepted attack payloads are rendered inside strict `<pre><code>` blocks to block DOM XSS.

**Deployment Timetable Pipeline:**
- **Stage 1:** Local Docker Compose environment
- **Stage 2:** PD1 Demo (Cloud VM, MiniLM-L6, ModSecurity in DetectionOnly)
- **Stage 3:** PD2 Demo (Bigger VM, Production model, ModSecurity in Enforcement)
- **Stage 4:** Final DICT Infrastructure Handoff

---

## Team Roles

| Member | Role | Primary Tasks |
|--------|------|---------------|
| **Gayao, Froilan** | DevOps & Project Manager | Ansible, Nginx, SSL, ModSecurity, orchestration |
| **Dela Cruz, Eugene** | Data & ML Lead | Dataset, preprocessing, model training |
| **Nonan, Faron Jabez** | Backend Lead | FastAPI, DB schema, retraining pipeline |
| **Aquino, Mark Angelo A.** | Frontend/Test/Docs | Dashboard, tests, documentation |
| **Bantuas, Junaid** | Frontend/Test/Docs | UI, tests, presentation |

---

## Target Metrics

| Metric | Target |
|--------|--------|
| Accuracy | ≥95% |
| F1-Score | ≥0.85 (macro average) |
| FPR | ≤3% |
| Latency | <100ms |

---

## Dataset

- **Source:** SR-BH 2020 (Harvard Dataverse)
- **Original:** 907,814 HTTP requests, 13 multi-label CAPEC categories
- **Adapted:** ~335,821 samples (Imbalanced: SQLi 55%, Normal 37%, Other 4%, Code 3%)
- **Split:** ~268K train (80%) / ~33K validation (10%) / ~33K test (10%), stratified
- **Characteristics:** 39.23% near-duplicate rate, severe 16.65:1 class imbalance

---

## Models (Compare 3)

1. **Fine-tuned BERT-base** (High-capacity reference configuration)
2. **Fine-tuned DistilBERT** (Balanced capacity-latency configuration)
3. **Fine-tuned MiniLM-L6** (Ultra-fast triage configuration)

---

## PD1/PD2 Boundary

| Phase | Scope | Status |
|-------|-------|--------|
| PD1 | Obj 1-2 (Data Prep, Model Dev), Working Frontend Dashboard Demo (Next.js), FastAPI endpoints partially working | Current |
| PD2 | Obj 3-9, Full Docker Compose deployment, ModSecurity enforcement, Ansible playbooks, Supabase DB, Real ML model | Future |

---

## Files

```
G:\Documents\PDDDD\
├── CONTEXT.md              # This file
├── REFERENCES/
│   └── output/            # Completed chapters
│       ├── Chapter1_Project_Background.md
│       ├── Chapter2_Project_Design.md
│       ├── Chapter3_Design_Tradeoffs.md
│       └── PLANNING_DOCUMENT.md
├── checklists/            # 9 checklist files
└── injection-alert-system/ # Project code
```

---

## Current State

| Component | Status | Owner |
|-----------|--------|-------|
| Project structure | ✅ Created | Froilan |
| Mock FastAPI model| ✅ Created | Froilan |
| FastAPI endpoints | ⚠️ Needs fixes | Jabez |
| Tests (26 passing)| ✅ Working | Mark/Junaid |
| Real ML model | ❌ Pending | Eugene |
| Data prep | ✅ Audited | Eugene |
| Frontend (Next.js) | ❌ In progress | Mark/Junaid |
| Ansible playbooks | ❌ Pending | Froilan |
| ModSecurity config| ❌ Pending | Froilan |
| Docker Compose | ❌ Pending | Froilan |
| Supabase connect | ❌ Pending (SQLite now)| Jabez |
| Documentation | 🔄 In progress | Mark/Junaid |

**FastAPI Backend Known Issues:**
- **Endpoints:** Missing `/api/stats`, `/api/batch-predict`, `/api/explain`
- **Schema:** Wrong field names (`traffic_id` → `alert_id`, `correct_label` → `analyst_label`)
- **Database:** Still using local SQLite (`test.db`) rather than Supabase connection
- **CORS:** Extremely permissive (`allow_origins=["*"]`) instead of Next.js explicitly
- **Secrets:** `GROQ_API_KEY` missing in `.env.example` and `config.py`

---

## Timeline (36 Weeks)

```
W1-4:    Data Preparation (Eugene)
W5-10:   Model Development & Training (Eugene)
W11-16:  Backend Development (Jabez)
W17-22:  Frontend Development (Mark, Junaid)
W23-26:  LLM Integration (Jabez, Eugene)
W27-30:  ModSecurity Integration (Froilan)
W31-34:  Ansible & Deployment (Froilan)
W35-36:  Testing & Documentation (All)
```

### Critical Path
Data Preparation → Model Training → Backend Integration → Deployment

---

## Contacts

- **Adviser:** Engr. Robin Valenzuela
- **Panel Lead:** Engr. Verlyn Nojor
- **Panel:** Engr. Menchie M. Rosales, Engr. Lloyd Aldrin Pornobi
- **Client:** DICT (Department of Information and Communications Technology)
