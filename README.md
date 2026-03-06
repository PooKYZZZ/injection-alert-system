# Injection Alert System

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)

A hybrid, CRS-first Web Application Firewall (WAF) and machine learning confidence-gated platform for SQL injection detection. 
It reduces the false-positive enforcement rates inherent in rule-based WAFs by conditioning automated blocking decisions on ML confidence scores.

## Table of Contents
- [Project Overview](#project-overview)
- [Quick Start](#quick-start)
- [Minimal Usage Example](#minimal-usage-example)
- [Architecture Overview](#architecture-overview)
- [Repository Structure](#repository-structure)
- [Documentation & Research](#documentation--research)
- [Contributing](#contributing)
- [License](#license)
- [Notes](#notes)

## Project Overview

The Injection Alert System is a cybersecurity research prototype combining ModSecurity and the OWASP Core Rule Set (CRS) with a transformer-based machine learning triage model. Instead of relying solely on strict rules or pure ML classification, this system leverages a CRS-first enforcement hierarchy.

By placing the ML model behind the CRS as a secondary confidence gate, we dramatically reduce false-positive blocking without sacrificing detection coverage. The ML model evaluates only the traffic that is already flagged by the rule set.

This repository contains the full backend, ML lifecycle pipelines, and deployment automation required to run the triage gate.

## Quick Start

Run these commands to get the backend running locally in detection-only mode:

```bash
git clone https://github.com/your-org/injection-alert-system.git
cd injection-alert-system
cp .env.example .env
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn web_app.presentation.app:app --reload
```

## Minimal Usage Example

Test the triage inference engine using a mocked payload:

```bash
curl -X POST "http://localhost:8000/api/predict" \
     -H "Content-Type: application/json" \
     -d '{"http_request": "SELECT * FROM users WHERE id = 1"}'
```

## Architecture Overview

Every request is evaluated by ModSecurity and OWASP CRS before being scored by the ML layer. Only flagged requests invoke ML inference.

```text
HTTP ──▶ Nginx Proxy ──▶ ModSecurity/CRS ──▶ FastAPI Triage ──▶ ML Inference ──▶ Gate ──▶ Supabase Audit Log
```

### Confidence Gate Tiers

| Confidence Level | Threshold | Action |
|---|---|---|
| **HIGH** | > 80% | Automated block enforced |
| **MEDIUM** | 50% – 80% | Logged, conditional block |
| **LOW** | < 50% | Routed to human review queue |

## Repository Structure

- `config/` - Static configurations, CRS overrides, and environment toggles.
- `web_app/` - FastAPI backend implementing Clean Architecture principles.
- `ml_model/` - Separated ML lifecycle (preprocessing, training, inference, retraining).
- `model_registry/` - Versioned model artifacts and promotion manifests.
- `data/` - Datasets storing raw, interim, and processed files for retraining.
- `observability/` - Prometheus metrics, alert rules, and Grafana dashboard parameters.
- `docs/` - Deep-dive architecture and research methodology documents.

For a deeper dive into these boundaries, see the [Architecture Document](docs/architecture.md).

## Documentation & Research

- **System Architecture:** [docs/architecture.md](docs/architecture.md)
- **Feasibility Report Methodology:** [docs/feasibility_report.md](docs/feasibility_report.md)

## Contributing

Please review [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, testing standards, and pull request procedures.

## License

MIT License. See `LICENSE` for full terms.

This repository is available for academic review and research reference.
