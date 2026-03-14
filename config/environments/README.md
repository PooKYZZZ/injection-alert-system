# Environment Configuration

This directory contains per-environment YAML configuration files.

## Purpose
- Isolate environment-specific variables
- Separate development, staging, and production settings
- Prevent cross-environment configuration leakage

## Current Contents
- `dev.yaml` — Local development defaults
- `staging.yaml` — Pre-production or validation defaults
- `production.yaml` — Production-oriented defaults

## Security Note
Production secrets must NOT be committed.
Use `.env.example` templates with placeholder values only.
