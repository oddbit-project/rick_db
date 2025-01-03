import psycopg2
import pytest
from rick_db import Cursor, ConnectionError
from rick_db.backend.pg import PgConnection
from rick_db.profiler import NullProfiler
from rick_db.sql import PgSqlDialect


class TestConnection:

    def test_connection(self, pg_conn: PgConnection):
        assert pg_conn is not None
        assert pg_conn.default_isolation_level == PgConnection.default_isolation_level
        assert pg_conn.default_isolation_level == 1
        assert pg_conn.profiler is not None
        assert isinstance(pg_conn.profiler, NullProfiler)
        assert isinstance(pg_conn.dialect(), PgSqlDialect)
        assert pg_conn.db is not None

    def test_connection_cursor(self, pg_conn: PgConnection):
        assert pg_conn is not None
        cursor = pg_conn.get_cursor()
        assert isinstance(cursor, Cursor)

        result = cursor.fetchone("select 1")
        assert isinstance(result, list)
        assert result[0] == 1

    def test_connection_transaction(self, pg_conn: PgConnection):
        assert pg_conn.in_transaction() is False
        pg_conn.begin()
        assert pg_conn.in_transaction() is True
        with pytest.raises(ConnectionError):
            pg_conn.begin()

        pg_conn.rollback()
        assert pg_conn.in_transaction() is False
        pg_conn.commit()

    def test_transaction_commit(self, pg_conn: PgConnection):
        assert pg_conn.in_transaction() is False
        assert pg_conn.db.autocommit is False
        with pg_conn.cursor() as c:
            c.exec("drop table if exists test")
            c.exec("create table test (id int)")

            # insert then commit
            pg_conn.begin()
            assert pg_conn.in_transaction() is True
            c.exec("insert into test select * from generate_series(1,4)")
            pg_conn.commit()
            assert pg_conn.in_transaction() is False
            result = c.fetchall("select * from test")
            assert len(result) == 4

            # cleanup
            c.exec("drop table test")

    def test_transaction_rollback(self, pg_conn: PgConnection):
        assert pg_conn.in_transaction() is False
        assert pg_conn.db.autocommit is False
        with pg_conn.cursor() as c:
            c.exec("drop table if exists test2")
            c.exec("create table test2 (id int)")

            # insert then cancel
            pg_conn.begin()
            assert pg_conn.in_transaction() is True
            c.exec("insert into test2 select * from generate_series(1,4)")
            pg_conn.rollback()
            assert pg_conn.in_transaction() is False
            result = c.fetchall("select * from test2")
            assert len(result) == 0

            # cleanup
            c.exec("drop table test2")

    def test_transaction_rollback_multi(self, pg_conn: PgConnection):
        # test rollback of multiple cursors
        pg_conn.begin()
        assert pg_conn.in_transaction() is True
        assert pg_conn.db.autocommit is False
        with pg_conn.cursor() as c:
            assert pg_conn.in_transaction() is True
            c.exec("drop table if exists test3")
            c.exec("create table test3 (id int)")
            c.exec("insert into test3(id) values(99)")

        with pg_conn.cursor() as c:
            assert pg_conn.in_transaction() is True
            c.exec("insert into test3(id) values(45)")

        # still in transaction, now lets rollback
        assert pg_conn.in_transaction() is True
        pg_conn.rollback()
        assert pg_conn.in_transaction() is False

        # transaction rollback, table should not exist
        with pytest.raises(psycopg2.errors.UndefinedTable):
            with pg_conn.cursor() as c:
                _ = c.fetchall("select * from test3")
