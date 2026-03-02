# Injection Alert System — Week 1 Tasks

This is the shared checklist for Week 1. 
- **Team members:** Check off `[x]` when you finish a task and push to GitHub.
- **Antigravity:** I will also check off items here automatically when I complete coding tasks for you.

---

## 📦 Shared Data Tasks (Eugene consolidates)
- [ ] **Eugene:** Download SR-BH 2020 raw dataset → `data/raw/`
- [ ] **Mark:** Verify dataset integrity (60k samples, 4 classes, 15k each)
- [ ] **Junaid:** Read SR-BH 2020 paper & summarize CAPEC definitions
- [ ] **Froilan:** Draft CAPEC → 4-class mapping table
- [ ] **Jabez:** Spot-check 10 raw HTTP request samples per class

## 🔬 Eugene (Data & ML Lead)
- [ ] Clone balanced 4-class version → `data/external/`
- [ ] Create `notebooks/EDA.ipynb` (Schema, distribution, length, word freq)
- [ ] Create `ml_model/preprocessing/preprocess.py` skeleton functions
- [ ] Write `tests/unit/test_preprocessing.py` (5 test cases)
- [ ] Document tokenization plan in `docs/data_pipeline.md`

## 📄 Mark (Docs & PM)
- [ ] Set up GitHub templates (`pull_request_template.md`, `ISSUE_TEMPLATE/task.md`)
- [ ] Run `pytest -v` & write test coverage audit report in `docs/test_audit.md`
- [ ] Add 5 new unit tests for `web_app/domain/` or `web_app/application/`
- [ ] Sketch low-fidelity UI wireframes → `docs/wireframes/`
- [ ] Write `docs/architecture_overview.md`

## 🖥️ Jabez (DevOps)
- [ ] Set up local virtualenv, ensure 26 tests pass, document Windows setup in `docs/dev_setup.md`
- [ ] Verify Google Colab + Kaggle GPU runtime access
- [ ] Write `docs/deployment_options.md` (DigitalOcean vs AWS comparison)
- [ ] Create Ansible stubs (`inventory`, `group_vars`, playbooks)
- [ ] Research ModSecurity + OWASP CRS install on Ubuntu → `docs/modsecurity_install_notes.md`

## 🔐 Junaid (Cyber Physical & Research)
- [ ] Collect 20+ SQL injection payloads → `docs/test_payloads/sqli_payloads.md`
- [ ] Collect 10+ code injection payloads → `docs/test_payloads/code_injection_payloads.md`
- [ ] Write `docs/attack_pattern_brief.md` (SQLi/Code injection formats & evasion)
- [ ] Write 5 new unit tests for `web_app/presentation/`
- [ ] Research Chart.js vs Plotly.js connection

## 🧑‍💻 Froilan (Backend Lead)
- [ ] Review and fix FastAPI endpoints flagged ⚠️ in `CONTEXT.md`
- [ ] Set up local PostgreSQL, run Alembic migrations (`alembic upgrade head`)
- [ ] Audit Clean Architecture layers (no reverse imports)
- [ ] Run `black .` and `ruff check .` — fix all warnings
- [ ] Set up team communication channel & schedule end-of-week sync
