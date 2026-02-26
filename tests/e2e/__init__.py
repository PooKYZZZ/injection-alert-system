# tests/e2e/
#
# Tier: End-to-End Tests
# Scope: Full system path — HTTP request → WAF decision → ML inference → audit log write.
# Requires: running FastAPI server, seeded PostgreSQL, loaded model artifact.
# Validates: confidence-gated mitigation behaviour, rollback trigger conditions.
# CI gate: runs on release branch only; requires full environment provisioned via Ansible.
