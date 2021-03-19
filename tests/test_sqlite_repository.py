import os

import pytest
from rick_db.conn.sqlite import Sqlite3Connection
from tests.repository import RepositoryTest, rows_users

dbfile = '/tmp/rick_db_sqlite_test.db'


class TestSqlite3Repository(RepositoryTest):
    createTable = """
        create table if not exists users(
        id_user integer primary key autoincrement,
        name text default '',
        email text default '',
        login text default null,
        active boolean default true
        );
        """
    insertTable = "insert into users(name, email, login, active) values(?,?,?,?)"

    def setup_method(self, test_method):
        self.conn = Sqlite3Connection(dbfile)
        with self.conn.cursor() as c:
            c.exec(self.createTable)
            for r in rows_users:
                c.exec(self.insertTable, list(r.values()))

    def teardown_method(self, test_method):
        self.conn.close()
        os.unlink(dbfile)

    @pytest.fixture()
    def conn(self):
        return self.conn
