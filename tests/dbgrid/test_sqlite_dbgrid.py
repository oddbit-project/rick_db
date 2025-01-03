import pytest

from rick_db import Repository, DbGrid
from rick_db.backend.sqlite import Sqlite3Connection
from tests.dbgrid.base_dbgrid import BaseDbGridTest, GridRecord

create_table = """
    create table if not exists grid(
    id_grid integer primary key autoincrement,
    label text,
    content text default '',
    odd boolean
    );
    """
insert_table = "insert into grid(label, content, odd) values(?,?,?)"


class TestSqlite3DbGrid(BaseDbGridTest):

    @pytest.fixture
    def conn(self):
        conn = Sqlite3Connection("file::memory:?cache=shared")

        # setup
        with conn.cursor() as c:
            c.exec(create_table)
            for i in range(1, 100):
                c.exec(insert_table, [self.label % i, "mickey mouse", (i % 2) == 0])

        yield conn

        # teardown
        conn.close()

    def test_grid_search_fields(self, conn):
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo, [GridRecord.label])
        # should search default field
        qry = grid._assemble(search_text="99", search_fields=[])
        sql, _ = qry.assemble()
        assert (
            sql
            == 'SELECT "grid".* FROM "grid" WHERE ( (UPPER("label") LIKE ?) ) ORDER BY "id_grid" ASC'
        )

        # skipping non-valid search field
        qry = grid._assemble(search_text="99", search_fields=[GridRecord.content])
        sql, _ = qry.assemble()
        assert (
            sql
            == 'SELECT "grid".* FROM "grid" WHERE ( (UPPER("label") LIKE ?) ) ORDER BY "id_grid" ASC'
        )

        # using specific search field
        grid = DbGrid(repo, [GridRecord.label, GridRecord.content])
        qry = grid._assemble(search_text="99", search_fields=[GridRecord.content])
        sql, _ = qry.assemble()
        assert (
            sql
            == 'SELECT "grid".* FROM "grid" WHERE ( (UPPER("content") LIKE ?) ) ORDER BY "id_grid" ASC'
        )

        # using specific search field and invalid field
        grid = DbGrid(repo, [GridRecord.label, GridRecord.content])
        qry = grid._assemble(
            search_text="99", search_fields=[GridRecord.content, GridRecord.odd]
        )
        sql, _ = qry.assemble()
        assert (
            sql
            == 'SELECT "grid".* FROM "grid" WHERE ( (UPPER("content") LIKE ?) ) ORDER BY "id_grid" ASC'
        )
