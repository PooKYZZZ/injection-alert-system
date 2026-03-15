# Presentation Middleware

This directory contains FastAPI middleware components.

**Relocated from:** `web_app/middleware/` to align with Clean Architecture.
Middleware is a presentation-layer concern and belongs under `presentation/`.

## Purpose
- Presentation-layer middleware and request guards
- CORS policy enforcement
- Request/response logging middleware

## Current Repo State
- This directory currently contains only the package marker and this README.
- Internal API bearer auth is implemented in `web_app/presentation/dependencies/auth.py`, not as FastAPI middleware.
- Rate limiting and structured request logging middleware are still deferred.

## Architectural Role
Security hardening layer between external requests and internal services.
This is part of the presentation layer (HTTP delivery mechanism).
