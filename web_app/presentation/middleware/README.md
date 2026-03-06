# Presentation Middleware

This directory contains FastAPI middleware components.

**Relocated from:** `web_app/middleware/` to align with Clean Architecture.
Middleware is a presentation-layer concern and belongs under `presentation/`.

## Purpose
- API authentication and authorization
- Rate limiting for classification endpoints
- CORS policy enforcement
- Request/response logging middleware

## Expected Contents
- `auth.py` — API key / JWT authentication middleware
- `rate_limit.py` — Rate limiting for /api/predict
- `logging.py` — Structured request/response logging

## Architectural Role
Security hardening layer between external requests and internal services.
This is part of the presentation layer (HTTP delivery mechanism).
