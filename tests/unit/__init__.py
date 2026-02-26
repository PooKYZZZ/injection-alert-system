# tests/unit/
#
# Tier: Unit Tests
# Scope: Pure function and class-level tests with no I/O, no DB, no network.
# Target modules: web_app/domain/, web_app/application/, ml_model/preprocessing/, ml_model/inference/
# Mocking rule: all infrastructure dependencies (DB, model file) MUST be mocked.
# CI gate: runs on every commit, must complete in < 60s.
