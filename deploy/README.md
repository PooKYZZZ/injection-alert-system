# Deployment Infrastructure

This directory contains deployment configuration for Ubuntu Server.

## Purpose
- systemd service unit files for process management
- Nginx reverse proxy configuration
- SSL/TLS certificate management

## Structure
```
deploy/
├── systemd/
│   ├── injection-alert-api.service
│   └── injection-alert-ml.service
├── nginx/
│   ├── nginx.conf
│   └── sites-available/
│       └── injection-alert.conf
└── ssl/
    └── README.md
```

## Architectural Role
Defines the production deployment topology:
  Client → Nginx (SSL) → FastAPI (uvicorn) → ML Inference
All managed as systemd services on a single Ubuntu server.
