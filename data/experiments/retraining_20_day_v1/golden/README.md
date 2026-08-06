# Locked golden-v1 controls

This directory contains the immutable evaluation controls for the controlled
offline retraining simulation. The exact request
`GET /api/users?page=1&limit=10` is a mandatory benign control and is not a
training sample.

Cases cover routine pagination, filtering, sorting, search, API requests,
encoded input, malformed/boundary input, SQL injection, code injection,
command injection, other attacks, obfuscation, and a structured-body
false-negative control.

The manifest pins the JSONL SHA-256 and a canonical manifest hash. Before a
future golden-set revision is created, compare exact and near-duplicate text
against the historical train/validation/test data, remove contamination, and
increment the experiment version. Do not edit `golden-v1` in place.
