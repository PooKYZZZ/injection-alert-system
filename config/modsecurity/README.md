# ModSecurity Configuration

This directory contains ModSecurity engine configuration files.

## Purpose
- Primary WAF detection engine configuration
- ModSecurity audit log format and output settings
- Engine-level directives (SecRuleEngine, SecAuditLog, etc.)

## Current Repo State
- This directory is currently a documented placeholder for future ModSecurity configuration.
- Runnable ModSecurity config files are not checked into the repo yet.

## Architectural Role
First layer in the CRS-first hybrid enforcement hierarchy.
ModSecurity processes all incoming requests BEFORE ML triage.
