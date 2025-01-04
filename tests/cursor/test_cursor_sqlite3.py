from sqlite3 import IntegrityError

import pytest

from rick_db.backend.sqlite import Sqlite3Connection

from tests.cursor.base_cursor import BaseTestCursor, NumberRecord


class TestCursorSqlLite3(BaseTestCursor):

    @pytest.fixture
    def conn(self, sqlite_conn: Sqlite3Connection):
        yield sqlite_conn
        sqlite_conn.close()

    def test_duplicate_record(self, conn):
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

            # attempt to insert forbidden value
            # exception raised, transaction is aborted
            with pytest.raises(IntegrityError):
                cur.exec("insert into counter(id) values (1)")

        with conn.cursor() as cur:
            # cleanup
            cur.exec("drop table if exists counter")
