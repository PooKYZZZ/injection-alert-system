# Project Setup Checklist

**Why This Matters:** A well-organized project structure is critical for ML projects. Unlike traditional software, ML projects involve data, models, experiments, and code that must be versioned separately. Poor organization leads to lost experiments, unreproducible results, and team confusion.

---

## Project Phases Overview

### PD1 vs PD2 Boundary (Per Chapter 1)
- **PD1 (Current):** Objectives 1-2
  - Objective 1: Data Preparation
  - Objective 2: Deep Learning Model Development
- **PD2 (Future):** Objectives 3-9
  - Objective 3: Web Application Development
  - Objective 4: Automated Response Implementation
  - Objective 5: ModSecurity Integration
  - Objective 6: Retraining Pipeline
  - Objective 7: Deployment Automation
  - Objective 8: Testing
  - Objective 9: System Evaluation

---

## Directory Structure

- [ ] Create project directory structure
  - [ ] `data/raw/` - Original, immutable data (SR-BH 2020)
  - [ ] `data/interim/` - Intermediate transformed data
  - [ ] `data/processed/` - Final datasets for modeling
  - [ ] `data/external/` - Third-party data sources
  - [ ] `ml_model/` - Model code (config.py, data.py, train.py, evaluate.py)
  - [ ] `ml_model/models/` - Model architectures (cnn_bilstm.py, bilstm_attention.py, distilbert_classifier.py)
  - [ ] `web_app/` - Web application (app.py, api/, static/, templates/)
  - [ ] `ansible/` - Deployment scripts (inventory.ini, deploy.yml)
  - [ ] `notebooks/` - Jupyter notebooks for EDA
  - [ ] `tests/` - Unit and integration tests
  - [ ] `docs/` - Documentation

---

## Version Control

- [ ] Initialize git repository
- [ ] Create `.gitignore` for ML projects
  - [ ] Exclude: data/raw/, data/interim/, data/processed/
  - [ ] Exclude: *.csv, *.pkl, *.h5, *.pt, *.pth
  - [ ] Exclude: venv/, .env, __pycache__/
  - [ ] Exclude: .vscode/, .idea/, .ipynb_checkpoints/

**Note:** ML models and datasets are often large binary files (100MB+). Git is not designed for these. Consider Git LFS or DVC for large files if needed.

---

## Development Environment

- [ ] Create Python virtual environment
- [ ] Create `requirements.txt` with dependencies:
  - [ ] **Core ML:** torch, numpy, pandas, scikit-learn
  - [ ] **Transformers:** transformers, huggingface-hub
  - [ ] **Web Framework:** fastapi, uvicorn
  - [ ] **Data Processing:** nltk, requests
  - [ ] **Visualization:** matplotlib, seaborn
  - [ ] **Testing:** pytest
- [ ] Install all dependencies

---

## Tech Stack Decisions

| Component | Choice | Rationale |
|-----------|--------|-----------|
| ML Framework | PyTorch | More flexible for research, better debugging |
| Transformers | Hugging Face Transformers | DistilBERT for transfer learning |
| Web Framework | FastAPI | Fast, async support, automatic API docs |
| Deployment OS | Ubuntu Server | Industry standard, better Ansible support |
| Database | PostgreSQL | Reliable, good for logging traffic |
| WAF | ModSecurity + OWASP CRS | Open source, widely used |

---

## Engineering Standards (Per Chapter 1.7)

- [ ] **NIST SP 800-94** - Intrusion detection and prevention system guidelines
- [ ] **OWASP CRS v4.x** - Web Application Firewall rule set
- [ ] **ISO/IEC 27035-1:2023** - Information security incident management
- [ ] **IEEE 829-2008** - Software test documentation
- [ ] **PEP-8** - Python code style guide

---

## Design Constraints (Per Chapter 1.6)

| Constraint | Metric | Target |
|------------|--------|--------|
| Safety | False Positive Rate | ≤ 3% |
| Performance | Inference Latency | < 100ms |
| Efficiency | Model Size/VRAM | < 6GB |
| Functionality | Interpretability | High |
| Manufacturability | Training Time | < 60 min |
