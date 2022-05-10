import pytest

from rick_db.conn.pg import PgConnection
from tests.config import postgres_db
from tests.dbgrid import DbGridTest


class TestPgRepository(DbGridTest):
    createTable = """
        create table if not exists grid(
        id_grid serial primary key,
        label text default '',
        odd boolean
        );
        """
    insertTable = "insert into grid(label, odd) values(%s,%s)"
    dropTable = "drop table grid"

    def setup_method(self, test_method):
        self.conn = PgConnection(**postgres_db)
        with self.conn.cursor() as qry:
            qry.exec(self.createTable)
            for i in range(1, 100):
                qry.exec(self.insertTable, [self.label % i, (i % 2) == 0])

    def teardown_method(self, test_method):
        with self.conn.cursor() as c:
            c.exec(self.dropTable)

    @pytest.fixture()
    def conn(self):
        return self.conn
