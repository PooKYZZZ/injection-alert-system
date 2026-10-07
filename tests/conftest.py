import os
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up test environment variables BEFORE any imports
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["APP_ENV"] = "testing"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["MODEL_PATH"] = "ml_model/models/mock_model.py"
# Set MODEL_REGISTRY_PATH to non-existent path to trigger mock fallback in tests
os.environ["MODEL_REGISTRY_PATH"] = "ml_model/model_registry/does_not_exist"
os.environ["API_SECRET_KEY"] = "test-secret-key"
os.environ["WAF_INGEST_API_KEY"] = "test-waf-ingest-key-at-least-32-characters"
# Local enforcement must never leak into the test suite through a developer's
# ignored environment file. Individual policy tests opt into other modes.
os.environ["ENFORCEMENT_MODE"] = "off"
os.environ["RETRAINING_ENABLED"] = "false"
# The test suite uses in-memory SQLite; the PostgreSQL notification worker must
# stay disabled regardless of settings in a developer's ignored
# .local/env/.env file.
os.environ["NOTIFICATION_WORKER_ENABLED"] = "false"
os.environ["NOTIFICATION_WORKER_REQUIRED"] = "false"


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Ensure test environment is configured before any module imports."""
    yield
    # Cleanup — remove test.db file if it exists
    test_db_path = os.path.join(os.getcwd(), "test.db")
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except OSError:
            pass
