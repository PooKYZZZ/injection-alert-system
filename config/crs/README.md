# OWASP CRS Configuration

This directory contains OWASP Core Rule Set configuration and overrides.

## Purpose
- CRS setup and initialization
- Rule exclusion overrides (no permanent CRS mutation)
- Paranoia level configuration

## Expected Contents
- `crs-setup.conf` — CRS initialization and paranoia level
- `REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf` — Pre-CRS exclusions
- `RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf` — Post-CRS exclusions

## Architectural Constraint
CRS rules are NEVER permanently modified.
All customization is done via exclusion files only.
