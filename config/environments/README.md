# Environment Configuration

This directory contains per-environment configuration files.

## Purpose
- Isolate environment-specific variables
- Separate development, staging, and production settings
- Prevent cross-environment configuration leakage

## Expected Contents
- `development.env` — Local development settings
- `staging.env` — Pre-production testing environment
- `production.env` — Production deployment settings (secrets excluded)

## Security Note
Production secrets must NOT be committed.
Use `.env.example` templates with placeholder values only.
