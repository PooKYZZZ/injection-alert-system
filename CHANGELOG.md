# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- **High-value regression tests for HTTP parsing edge cases**:
  - `test_execute_handles_connect_authority_form_correctly`: Verifies that CONNECT method with authority-form (e.g., `CONNECT example.com:443 HTTP/1.1`) returns `None` for the path, as per RFC 7230. The raw HTTP request is still preserved for forensics.
  - `test_execute_handles_options_asterisk_form`: Verifies that OPTIONS method with asterisk-form (e.g., `OPTIONS * HTTP/1.1`) correctly returns `*` as the path, as per RFC 7230.

- **Environment-gated configuration tests**:
  - `test_staging_environment_properties`: Verifies that staging environment is correctly identified with all expected properties.
  - `test_production_environment_properties`: Verifies that production environment is correctly identified with all expected properties.

---

## [0.1.0] - 2026-03-20

### Added

- Initial release of the Injection Alert System
- FastAPI backend with ML-based SQL injection detection
- Next.js dashboard with BFF (Backend-for-Frontend) layer
- Transformer-based ML model (DistilBERT)
- Async SQLAlchemy with SQLite/PostgreSQL support

### Features

- **Backend Routes**:
  - `POST /api/predict` - Predict injection attacks from HTTP requests
  - `POST /api/triage` - Triage with reservation-first concurrency control
  - `GET /api/alerts` - List alerts with filtering
  - `GET /api/alerts/{id}` - Get alert detail
  - `PATCH /api/alerts/{id}/triage` - Update triage status
  - `GET /api/stats` - Traffic statistics with window filtering
  - `GET /api/ml-health` - ML model health metrics
  - `POST /api/feedback` - Analyst feedback on predictions
  - `GET /health` - Health check endpoint
  - `GET /api/health` - API health check endpoint

- **HTTP Request Parsing**:
  - Conservative RFC 7230-compliant parser
  - Supports origin-form, absolute-form, asterisk-form
  - Explicitly rejects authority-form (CONNECT method)
  - Returns `None` for malformed input (safe failure)

- **Security Features**:
  - Bearer token authentication for internal API routes
  - Environment-gated auth (production/staging require auth, dev allows bypass only if no API key)
  - CORS configuration per environment (restrictive in prod/staging, permissive in dev)
  - API docs disabled by default in production/staging

- **Data Model**:
  - Raw forensic `http_request` field preserved verbatim
  - Derived analytics fields: `request_method`, `request_path`
  - Confidence-gated actions: BLOCKED, THROTTLED, ALLOWED

### Testing

- 127 tests passing (unit + integration)
- Comprehensive coverage for:
  - HTTP parsing edge cases (CONNECT, OPTIONS, malformed input)
  - Triage use case flows (execute, ingest, concurrent duplicates)
  - Environment-gated configuration (dev, staging, production)
  - Repository operations (save, claim_processing, complete_processing)

---

## Known Limitations

- `/api/alerts` endpoint may return 500 due to DB schema issues (investigation needed)
- No automatic reclamation of stale PROCESSING reservations (returns 503 with Retry-After)
- Docker/ModSecurity/Redis integration not yet implemented
- Supabase RLS enforcement not yet wired

---

## Upgrade Notes

### Upgrading from earlier versions

1. Ensure `API_SECRET_KEY` is configured in production/staging environments
2. Set `APP_ENV` to `production`, `staging`, or `development` for appropriate security behavior
3. Configure `ALLOWED_ORIGINS` for CORS in production/staging
4. Set `MODEL_REGISTRY_PATH` to point to model artifacts in production

---

## Deprecation Notices

- `app.state.model` is deprecated in favor of `app.state.model_service` (compatibility alias maintained)
- Legacy `class` and `confidence_level` fields in prediction response are deprecated (use `prediction` and `confidence_tier`)

---

## Security Considerations

- Never commit `.env`, `.env.local`, or API keys to version control
- Always use bearer token authentication in production/staging
- Keep the Browser -> Next.js Route Handler -> FastAPI boundary
- Do not allow direct browser-to-FastAPI calls
