import pytest
import os
import sys
from pathlib import Path

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
