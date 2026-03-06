# web_app/infrastructure/database/
#
# Re-exports from the database module for clean import paths.
# Usage: from web_app.infrastructure.database import get_db, TrafficLog
#
from web_app.infrastructure.database.database import (
    engine,
    AsyncSessionLocal,
    Base,
    TrafficLog,
    init_db,
    get_db,
)

__all__ = [
    "engine",
    "AsyncSessionLocal",
    "Base",
    "TrafficLog",
    "init_db",
    "get_db",
]
