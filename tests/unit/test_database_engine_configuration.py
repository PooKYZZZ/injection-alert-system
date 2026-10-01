from web_app.infrastructure.database.database import _database_engine_options


def test_postgres_engine_uses_a_bounded_pool_and_connection_deadline():
    pool, connect_args = _database_engine_options(
        "postgresql+asyncpg://db.example.test/app"
    )

    assert pool["pool_size"] == 5
    assert pool["max_overflow"] == 5
    assert pool["pool_timeout"] == 10
    assert pool["pool_pre_ping"] is True
    assert connect_args["timeout"] == 10


def test_supabase_transaction_pooler_disables_asyncpg_statement_cache():
    _, connect_args = _database_engine_options(
        "postgresql+asyncpg://aws-1.pooler.supabase.com:6543/app"
    )

    assert connect_args["statement_cache_size"] == 0


def test_sqlite_engine_keeps_its_existing_pool_configuration():
    pool, connect_args = _database_engine_options("sqlite+aiosqlite:///:memory:")

    assert pool == {"pool_pre_ping": True}
    assert connect_args == {}
