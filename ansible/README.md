# Ansible — Response Automation

This directory contains Ansible playbooks, roles, and inventory
for automated deployment and mitigation response.

## Purpose
- Deployment automation for Ubuntu Server target
- Temporary IP blocking via confidence-gated mitigation
- Service orchestration (FastAPI, Nginx, PostgreSQL, ModSecurity)
- Rollback capability for both infrastructure and model versions

## Structure
```
ansible/
├── ansible.cfg
├── playbooks/
│   ├── deploy.yml          — Full system deployment
│   ├── mitigate.yml        — Temporary IP block (time-bounded)
│   └── rollback.yml        — Rollback deployment or model version
├── roles/
│   ├── nginx/              — Reverse proxy setup
│   ├── modsecurity/        — WAF engine installation and config
│   ├── fastapi_app/        — Backend application deployment
│   ├── postgresql/         — Database setup
│   └── ssl/                — Certificate management
├── inventory/
│   ├── dev.yml
│   ├── staging.yml
│   └── production.yml
└── group_vars/
    ├── all.yml
    └── production.yml
```

## Architectural Constraints
- Mitigation actions are ALWAYS time-bounded (no permanent blocks)
- CRS rules are NEVER permanently modified by automation
- All actions are logged to the audit trail
- Playbooks must be idempotent
