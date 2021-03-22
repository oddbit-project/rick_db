import pytest

from rick_db.conn.pg import PgConnection
from tests.config import postgres_db
from tests.repository import RepositoryTest, rows_users


class TestPgRepository(RepositoryTest):
    createTable = """
        create table if not exists users(
        id_user serial primary key,
        name text default '',
        email text default '',
        login text default null,
        active boolean default true
        );
        """
    insertTable = "insert into users(name, email, login, active) values(%s,%s,%s,%s)"
    dropTable = "drop table users"

    def setup_method(self, test_method):
        self.conn = PgConnection(**postgres_db)
        with self.conn.cursor() as qry:
            qry.exec(self.createTable)
            for r in rows_users:
                qry.exec(self.insertTable, list(r.values()))

    def teardown_method(self, test_method):
        with self.conn.cursor() as c:
            c.exec(self.dropTable)

    @pytest.fixture()
    def conn(self):
        return self.conn
