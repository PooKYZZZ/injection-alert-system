from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError


POSTGRES_URL = os.getenv("CYBERTRACE_POSTGRES_TEST_URL")


@pytest.mark.skipif(not POSTGRES_URL, reason="disposable PostgreSQL URL not configured")
def test_postgres_rejects_verified_direct_source() -> None:
    database_url = POSTGRES_URL.replace(
        "postgresql://", "postgresql+psycopg://", 1
    )
    engine = create_engine(database_url)
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        """
                        INSERT INTO traffic_logs
                            (source_ip, source_provenance,
                             source_verification_status, http_request)
                        VALUES
                            ('192.0.2.250', 'DIRECT_REMOTE_ADDR',
                             'VERIFIED', 'GET /invalid')
                        """
                    )
                )
        finally:
            transaction.rollback()
    engine.dispose()
