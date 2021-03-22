import os

import pytest
from rick_db.conn.sqlite import Sqlite3Connection
from tests.dbgrid import DbGridTest

dbfile = '/tmp/rick_db_sqlite_test.db'


class TestSqlite3Repository(DbGridTest):
    createTable = """
        create table if not exists grid(
        id_grid integer primary key autoincrement,
        label text,
        odd boolean
        );
        """
    insertTable = "insert into grid(label, odd) values(?,?)"

    def setup_method(self, test_method):
        self.conn = Sqlite3Connection(dbfile)
        with self.conn.cursor() as qry:
            qry.exec(self.createTable)
            for i in range(1, 100):
                qry.exec(self.insertTable, [self.label % i, (i % 2) == 0])

    def teardown_method(self, test_method):
        self.conn.close()
        os.unlink(dbfile)

    @pytest.fixture()
    def conn(self):
        return self.conn
