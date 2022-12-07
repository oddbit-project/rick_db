import os

import pytest

from rick_db import Repository, DbGrid
from rick_db.conn.sqlite import Sqlite3Connection
from tests.dbgrid import DbGridTest, GridRecord


class TestSqlite3Repository(DbGridTest):
    createTable = """
        create table if not exists grid(
        id_grid integer primary key autoincrement,
        label text,
        content text default '',        
        odd boolean
        );
        """
    insertTable = "insert into grid(label, content, odd) values(?,?,?)"

    def setup_method(self, test_method):
        self.conn = Sqlite3Connection(":memory:")
        with self.conn.cursor() as qry:
            qry.exec(self.createTable)
            for i in range(1, 100):
                qry.exec(
                    self.insertTable, [self.label % i, "mickey mouse", (i % 2) == 0]
                )

    def teardown_method(self, test_method):
        self.conn.close()

    @pytest.fixture()
    def conn(self):
        return self.conn

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
