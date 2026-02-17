import pytest
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up test environment variables BEFORE any imports
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["APP_ENV"] = "testing"
os.environ["LOG_LEVEL"] = "DEBUG"
os.environ["MODEL_PATH"] = "ml_model/models/mock_model.py"
os.environ["API_SECRET_KEY"] = "test-secret-key"


@pytest.fixture(scope="session", autouse=True)
def test_env():
    """Set up test environment and cleanup."""
    yield

    # Cleanup
    if os.path.exists(project_root / "test.db"):
        os.remove(project_root / "test.db")
