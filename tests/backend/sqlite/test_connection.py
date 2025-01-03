import sqlite3
import sys

import pytest

from rick_db import Cursor, ConnectionError
from rick_db.backend.sqlite import Sqlite3Connection, Sqlite3Manager
from rick_db.profiler import NullProfiler
from rick_db.sql import Sqlite3SqlDialect


class TestConnection:

    def test_connection(self, sqlite_conn: Sqlite3Connection):
        assert sqlite_conn is not None
        assert sqlite_conn.profiler is not None
        assert isinstance(sqlite_conn.profiler, NullProfiler)
        assert isinstance(sqlite_conn.dialect(), Sqlite3SqlDialect)
        assert sqlite_conn.db is not None

    def test_connection_cursor(self, sqlite_conn: Sqlite3Connection):
        cursor = sqlite_conn.get_cursor()
        assert isinstance(cursor, Cursor)

        result = cursor.fetchone("select 1")
        assert isinstance(result, dict)  # sqlite returns dictionaries

    def test_connection_transaction(self, sqlite_conn: Sqlite3Connection):
        assert sqlite_conn.in_transaction() is False
        sqlite_conn.begin()
        assert sqlite_conn.in_transaction() is True
        with pytest.raises(ConnectionError):
            sqlite_conn.begin()

        sqlite_conn.rollback()
        assert sqlite_conn.in_transaction() is False
        sqlite_conn.commit()

    def test_transaction_commit(self, sqlite_conn: Sqlite3Connection):
        assert sqlite_conn.in_transaction() is False
        assert sqlite_conn.autocommit is False
        with sqlite_conn.cursor() as c:
            c.exec("drop table if exists test")
            c.exec("create table test (id int)")

            # insert then commit
            sqlite_conn.begin()
            assert sqlite_conn.in_transaction() is True
            c.exec("insert into test(id) values(1)")
            c.exec("insert into test(id) values(2)")
            c.exec("insert into test(id) values(3)")
            c.exec("insert into test(id) values(4)")
            sqlite_conn.commit()
            assert sqlite_conn.in_transaction() is False
            result = c.fetchall("select * from test")
            assert len(result) == 4

            # cleanup
            c.exec("drop table test")

    def test_transaction_rollback(self, sqlite_conn: Sqlite3Connection):
        assert sqlite_conn.in_transaction() is False
        assert sqlite_conn.autocommit is False
        with sqlite_conn.cursor() as c:
            c.exec("drop table if exists test2")
            c.exec("create table test2 (id int)")

            # insert then cancel
            sqlite_conn.begin()
            assert sqlite_conn.in_transaction() is True
            c.exec("insert into test2(id) values(1)")
            c.exec("insert into test2(id) values(2)")
            c.exec("insert into test2(id) values(3)")
            c.exec("insert into test2(id) values(4)")
            sqlite_conn.rollback()
            assert sqlite_conn.in_transaction() is False

            result = c.fetchall("select * from test2")
            assert len(result) == 0

            # cleanup
            c.exec("drop table test2")

    def test_transaction_rollback_multi(self, sqlite_conn: Sqlite3Connection):
        # test rollback of multiple cursors
        sqlite_conn.begin()
        assert sqlite_conn.in_transaction() is True
        assert sqlite_conn.autocommit is False

        with sqlite_conn.cursor() as c:
            assert sqlite_conn.in_transaction() is True
            c.exec("drop table if exists test3")
            c.exec("create table test3 (id int)")
            c.exec("insert into test3(id) values(99)")

        with sqlite_conn.cursor() as c:
            assert sqlite_conn.in_transaction() is True
            c.exec("insert into test3(id) values(45)")

        # still in transaction, now lets rollback
        assert sqlite_conn.in_transaction() is True
        sqlite_conn.rollback()
        assert sqlite_conn.in_transaction() is False

        version = sys.version_info
        # python >=3.12 sqlite supports PEP249 autocommit property
        if version >= (3, 12):
            # in previous python versions, rollback() does not rollback DDL statements
            # transaction rollback, table should not exist
            with pytest.raises(sqlite3.OperationalError):
                with sqlite_conn.cursor() as c:
                    _ = c.fetchall("select * from test3")
        else:
            # no DDL rollback supported, table should be empty
            with sqlite_conn.cursor() as c:
                assert len(c.fetchall("select * from test3")) == 0
