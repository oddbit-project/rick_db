import pytest

from rick_db.backend.pg import PgConnection, PgConnectionPool
from rick_db.backend.sqlite import Sqlite3Connection

PG_IMAGE = "postgres:12-alpine"
PG_USER = "pguser"
PG_PASSWORD = "pgpass"
PG_DB = "rickdb"

CH_IMAGE = "clickhouse/clickhouse-server:25.6"
CH_USER = "rickdb"
CH_PASSWORD = "rickpass"
CH_DB = "rickdb"


@pytest.fixture(scope="session")
def pg_container():
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer(
        PG_IMAGE, username=PG_USER, password=PG_PASSWORD, dbname=PG_DB
    ) as container:
        yield container


@pytest.fixture(scope="session")
def ch_container():
    from testcontainers.clickhouse import ClickHouseContainer

    container = ClickHouseContainer(
        CH_IMAGE, username=CH_USER, password=CH_PASSWORD, dbname=CH_DB
    )
    container.with_env("CLICKHOUSE_DEFAULT_ACCESS_MANAGEMENT", "1")
    with container:
        yield container


@pytest.fixture
def pg_settings(pg_container) -> dict:
    return {
        "host": pg_container.get_container_host_ip(),
        "port": int(pg_container.get_exposed_port(5432)),
        "user": PG_USER,
        "password": PG_PASSWORD,
        "database": PG_DB,
        "sslmode": "allow",
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
def ch_settings(ch_container) -> dict:
    return {
        "host": ch_container.get_container_host_ip(),
        "port": int(ch_container.get_exposed_port(8123)),
        "username": CH_USER,
        "password": CH_PASSWORD,
        "database": CH_DB,
    }


@pytest.fixture
def ch_conn(ch_settings):
    from rick_db.backend.clickhouse import ClickHouseConnection

    c = ClickHouseConnection(**ch_settings)
    yield c
    c.close()
