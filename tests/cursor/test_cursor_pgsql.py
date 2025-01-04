import pytest
from psycopg2.errors import UniqueViolation

from rick_db.backend.pg import PgConnection, PgConnectionPool
from tests.cursor.base_cursor import BaseTestCursor, NumberRecord


class TestCursorPGConnection(BaseTestCursor):

    @pytest.fixture
    def conn(self, pg_settings: dict):
        conn = PgConnection(**pg_settings)

        yield conn

        conn.close()

    def test_propagate_exception(self, pg_conn: PgConnection):
        with pg_conn.cursor() as cur:
            # simple select
            result = cur.exec("select 1")
            assert len(result) == 1

            # object mapper hydration
            cur.exec("drop table if exists counter")
            cur.exec("create table counter (id int not null primary key)")
            cur.exec("insert into counter(id) values(1)")
            cur.exec("insert into counter(id) values(2)")
            cur.exec("insert into counter(id) values(3)")
            cur.exec("insert into counter(id) values(4)")
            result = cur.exec("select * from counter", cls=NumberRecord)
            assert len(result) == 4
            for r in result:
                assert isinstance(r, NumberRecord)

        # ensures exception propagates outside of context
        with pytest.raises(UniqueViolation):
            with pg_conn.cursor() as cur:
                cur.exec("insert into counter(id) values (1)")

            with pg_conn.cursor() as cur:
                # cleanup
                cur.exec("drop table if exists counter")


class TestCursorPGConnectionPool(BaseTestCursor):

    @pytest.fixture
    def conn(self, pg_settings: dict):
        pool = PgConnectionPool(**pg_settings)

        with pool.connection() as conn:
            yield conn

        # teardown
        pool.close()

    def test_propagate_exception(self, pg_pool: PgConnectionPool):
        with pg_pool.connection() as conn:
            with conn.cursor() as cur:
                # simple select
                result = cur.exec("select 1")
                assert len(result) == 1

                # object mapper hydration
                cur.exec("drop table if exists counter")
                cur.exec("create table counter (id int not null primary key)")
                cur.exec("insert into counter(id) values(1)")
                cur.exec("insert into counter(id) values(2)")
                cur.exec("insert into counter(id) values(3)")
                cur.exec("insert into counter(id) values(4)")
                result = cur.exec("select * from counter", cls=NumberRecord)
                assert len(result) == 4
                for r in result:
                    assert isinstance(r, NumberRecord)

        # ensures exception propagates outside of context
        with pytest.raises(UniqueViolation):
            with pg_pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.exec("insert into counter(id) values (1)")

        with pg_pool.connection() as conn:
            with conn.cursor() as cur:
                # cleanup
                cur.exec("drop table if exists counter")
