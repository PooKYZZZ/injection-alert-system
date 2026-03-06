"""
web_app/app.py

LEGACY COMPATIBILITY SHIM — scheduled for removal.

This file exists only to preserve backward compatibility for:
  - tests/integration/test_api.py (imports `from web_app.app import app`)
  - uvicorn invocations that use `web_app.app:app`

The canonical app factory is at web_app/presentation/app.py.
All new code should import from there instead.

TODO: Update all imports to `web_app.presentation.app` and delete this file.
"""

from web_app.presentation.app import app  # noqa: F401

__all__ = ["app"]
