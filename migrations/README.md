# Database Migrations

This directory contains Alembic database migration scripts.

## Purpose
- Schema evolution for PostgreSQL
- Version-controlled database changes
- Rollback capability for schema changes

## Current Contents
- `env.py` — Alembic environment setup; reads `DATABASE_URL` from the environment and rewrites PostgreSQL URLs to sync `psycopg` for migrations
- `versions/20260315_000002_add_triage_processing_status.py` — adds `created_at` and `status`, and relaxes placeholder-result columns for reservation-first triage ingest

## Related Files
- Repo root `alembic.ini` — Alembic configuration
