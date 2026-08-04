import pytest

from rick_db.backend.pg import PgConnection, PgConnectionPool

from tests.keyset.common import BaseKeysetIntegrationTest

CREATE_TABLE = """
CREATE TABLE keyset_grid (
    id_keyset_grid SERIAL PRIMARY KEY,
    label TEXT NOT NULL,
    content TEXT NOT NULL,
    odd BOOLEAN NOT NULL
)
"""


def _setup(conn):
    with conn.cursor() as cursor:
        cursor.exec("DROP TABLE IF EXISTS keyset_grid")
        cursor.exec(CREATE_TABLE)
        for index in range(1, 100):
            cursor.exec(
                "INSERT INTO keyset_grid(label, content, odd) VALUES(%s, %s, %s)",
                ["row %d" % index, "tied", index % 2 == 0],
            )


def _teardown(conn):
    with conn.cursor() as cursor:
        cursor.exec("DROP TABLE IF EXISTS keyset_grid")


class TestPgConnectionKeyset(BaseKeysetIntegrationTest):
    @pytest.fixture
    def conn(self, pg_settings):
        conn = PgConnection(**pg_settings)
        _setup(conn)
        yield conn
        _teardown(conn)
        conn.close()


class TestPgPoolKeyset(BaseKeysetIntegrationTest):
    @pytest.fixture
    def conn(self, pg_settings):
        pool = PgConnectionPool(**pg_settings)
        with pool.connection() as connection:
            _setup(connection)
        yield pool
        with pool.connection() as connection:
            _teardown(connection)
        pool.close()
