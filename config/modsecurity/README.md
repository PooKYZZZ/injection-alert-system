# ModSecurity Configuration

This directory contains ModSecurity engine configuration files.

## Purpose
- Primary WAF detection engine configuration
- ModSecurity audit log format and output settings
- Engine-level directives (SecRuleEngine, SecAuditLog, etc.)

## Expected Contents
- `modsecurity.conf` — Core engine configuration
- `unicode.mapping` — Unicode mapping file

## Architectural Role
First layer in the CRS-first hybrid enforcement hierarchy.
ModSecurity processes all incoming requests BEFORE ML triage.
