import os

import pytest

from rick_db.backend.pg import PgConnection, PgConnectionPool
from rick_db.backend.sqlite import Sqlite3Connection


@pytest.fixture
def pg_settings() -> dict:
    return {
        "host": os.environ.get("PGHOST", "localhost"),
        "port": int(os.environ.get("PGPORT", 5432)),
        "user": os.environ.get("POSTGRES_USER", "pguser"),
        "password": os.environ.get("POSTGRES_PASSWORD", "pgpass"),
        "database": os.environ.get("POSTGRES_DB", "rickdb"),
        "sslmode": os.environ.get("PGSSLMODE", "allow"),
    }


@pytest.fixture
def pg_conn(pg_settings) -> PgConnection:
    c = PgConnection(**pg_settings)
    yield c
    c.close()


@pytest.fixture
def pg_pool(pg_settings) -> PgConnectionPool:
    c = PgConnectionPool(**pg_settings)
    yield c
    c.close()


@pytest.fixture
def sqlite_conn() -> Sqlite3Connection:
    c = Sqlite3Connection(":memory:")
    yield c
    c.close()


@pytest.fixture
def ch_settings() -> dict:
    return {
        "host": os.environ.get("CLICKHOUSE_HOST", "localhost"),
        "port": int(os.environ.get("CLICKHOUSE_PORT", 8123)),
        "username": os.environ.get("CLICKHOUSE_USER", "default"),
        "password": os.environ.get("CLICKHOUSE_PASSWORD", ""),
        "database": os.environ.get("CLICKHOUSE_DB", "default"),
    }


@pytest.fixture
def ch_conn(ch_settings):
    from rick_db.backend.clickhouse import ClickHouseConnection

    try:
        c = ClickHouseConnection(**ch_settings)
    except Exception:
        pytest.skip("ClickHouse server not available")
        return

    yield c
    c.close()
