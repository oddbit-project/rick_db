import pytest

from rick_db import Repository, DbGrid
from rick_db.backend.pg import PgConnection, PgConnectionPool
from tests.dbgrid.base_dbgrid import BaseDbGridTest, GridRecord

create_table = """
    create table if not exists grid(
    id_grid serial primary key,
    label text default '',
    content text default '',
    odd boolean
    );
    """
insert_table = "insert into grid(label, content, odd) values(%s,%s,%s)"
drop_table = "drop table if exists grid"


class TestPgConnDbGrid(BaseDbGridTest):

    @pytest.fixture
    def conn(self, pg_settings: dict):
        conn = PgConnection(**pg_settings)
        # setup
        with conn.cursor() as c:
            c.exec(drop_table)
            c.exec(create_table)
            for i in range(1, 100):
                c.exec(insert_table, [self.label % i, "mickey mouse", (i % 2) == 0])

        yield conn

        # teardown
        with conn.cursor() as c:
            c.exec(drop_table)
        conn.close()

    def test_grid_search_fields(self, conn):
        repo = Repository(conn, GridRecord)
        grid = DbGrid(repo, [GridRecord.label])

        # should search default field
        qry = grid._assemble(search_text="99", search_fields=[])
        sql, _ = qry.assemble()
        assert (
            sql
            == 'SELECT "grid".* FROM "grid" WHERE ( ("label" ILIKE %s) ) ORDER BY "id_grid" ASC'
        )

        # skipping non-valid search field
        qry = grid._assemble(search_text="99", search_fields=[GridRecord.content])
        sql, _ = qry.assemble()
        assert (
            sql
            == 'SELECT "grid".* FROM "grid" WHERE ( ("label" ILIKE %s) ) ORDER BY "id_grid" ASC'
        )

        # using specific search field
        grid = DbGrid(repo, [GridRecord.label, GridRecord.content])
        qry = grid._assemble(search_text="99", search_fields=[GridRecord.content])
        sql, _ = qry.assemble()
        assert (
            sql
            == 'SELECT "grid".* FROM "grid" WHERE ( ("content" ILIKE %s) ) ORDER BY "id_grid" ASC'
        )

        # using specific search field and invalid field
        grid = DbGrid(repo, [GridRecord.label, GridRecord.content])
        qry = grid._assemble(
            search_text="99", search_fields=[GridRecord.content, GridRecord.odd]
        )
        sql, _ = qry.assemble()
        assert (
            sql
            == 'SELECT "grid".* FROM "grid" WHERE ( ("content" ILIKE %s) ) ORDER BY "id_grid" ASC'
        )


class TestPgPoolDbGrid(TestPgConnDbGrid):

    @pytest.fixture
    def conn(self, pg_settings: dict):
        pool = PgConnectionPool(**pg_settings)
        # setup
        with pool.connection() as db:
            with db.cursor() as c:
                c.exec(drop_table)
                c.exec(create_table)
                for i in range(1, 100):
                    c.exec(insert_table, [self.label % i, "mickey mouse", (i % 2) == 0])

        yield pool

        # teardown
        with pool.connection() as conn:
            with conn.cursor() as c:
                c.exec(drop_table)
        pool.close()
