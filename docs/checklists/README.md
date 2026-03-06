# Development Checklist Overview

**Project:** Deep Learning-Based Confidence Classification for Context-Aware Injection Alert  
**Team:** Team 13  
**Final Defense:** May 2026

---

## Quick Navigation

| # | Checklist | Focus Area | File |
|---|-----------|------------|------|
| 1 | Project Setup | Directory structure, version control, environment | [01_PROJECT_SETUP.md](01_PROJECT_SETUP.md) |
| 2 | Data Preparation | Dataset acquisition, preprocessing, EDA | [02_DATA_PREPARATION.md](02_DATA_PREPARATION.md) |
| 3 | ML Model | Architecture, training, comparison, evaluation | [03_ML_MODEL.md](03_ML_MODEL.md) |
| 4 | Web Application | Backend, frontend, response actions | [04_WEB_APP.md](04_WEB_APP.md) |
| 5 | Retraining Pipeline | Data collection, scheduling, versioning | [05_RETRAINING.md](05_RETRAINING.md) |
| 6 | ModSecurity Integration | WAF setup, hybrid detection | [06_MODSECURITY.md](06_MODSECURITY.md) |
| 7 | Ansible Deployment | Playbooks, templates, automation | [07_ANSIBLE.md](07_ANSIBLE.md) |
| 8 | Testing & Evaluation | Unit tests, integration tests, security tests | [08_TESTING.md](08_TESTING.md) |
| 9 | Documentation | API docs, user manual, final report | [09_DOCUMENTATION.md](09_DOCUMENTATION.md) |

---

## Tech Stack

| Component | Choice |
|-----------|--------|
| ML Framework | PyTorch |
| Web Framework | FastAPI |
| Deployment OS | Ubuntu Server |
| Database | PostgreSQL |
| WAF | ModSecurity + OWASP CRS |
| Automation | Ansible |

---

## Target Metrics

| Metric | Target |
|--------|--------|
| Overall Accuracy | ≥ 95% |
| Per-class F1-Score | ≥ 0.85 |
| False Positive Rate | ≤ 3% |
| Inference Latency | < 100ms |

---

## Timeline Summary

| Week | Focus | Key Deliverable |
|------|-------|-----------------|
| 1-2 | Data Preparation | Clean dataset, EDA complete |
| 3-4 | Model Development | 3 architectures trained |
| 5-6 | Model Selection | Best model selected |
| 7-8 | Web App Backend | API endpoints functional |
| 9-10 | Web App Frontend | Dashboard usable |
| 11-12 | ModSecurity Integration | Hybrid detection working |
| 13-14 | Ansible Scripts | Deployment automated |
| 15-16 | Testing | All tests passing |
| 17-18 | Documentation | All docs complete |
| 19-20 | Defense Prep | Presentation ready |

---

## Quick Commands Reference

```bash
# Activate environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Training
python ml_model/train.py --model cnn_bilstm --epochs 50

# Evaluation
python ml_model/evaluate.py --model models/best_model.pt

# Web Application
uvicorn web_app.app:app --host 0.0.0.0 --port 5000

# Testing
pytest tests/ -v

# Deployment
ansible-playbook ansible/deploy.yml -i ansible/inventory.ini --ask-become-pass

# Retraining
python scripts/retrain.py
```
