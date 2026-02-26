# tests/integration/
#
# Tier: Integration Tests
# Scope: Tests that span two or more components with real dependencies.
# Includes: FastAPI TestClient + real DB session (test schema), ML model loading from disk.
# Target: endpoint behaviour, DB read/write correctness, WAF config parsing round-trips.
# CI gate: runs on PR merge, requires test DB to be provisioned.
