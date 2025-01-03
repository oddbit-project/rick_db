from rick_db import Cursor, Connection, QueryCache
from rick_db.backend.pg import PgConnectionPool, PgConnection
from rick_db.repository import GenericRepository


class TestGenericRepository:

    def test_init_pool(self, pg_pool: PgConnectionPool):
        r = GenericRepository(pg_pool, "some_table", "schema", "pk")
        assert r._db is None
        assert r._pool == pg_pool
        assert r.pk == "pk"
        assert r.table_name == "some_table"
        assert r.schema == "schema"
        assert isinstance(r.query_cache, QueryCache)

        with r.conn() as conn:
            assert isinstance(conn, Connection)

        with r.cursor() as cursor:
            assert isinstance(cursor, Cursor)

    def test_init_conn(self, pg_conn: PgConnection):
        r = GenericRepository(pg_conn, "some_table", "schema", "pk")
        assert r._pool is None
        assert r._db == pg_conn
        assert r.pk == "pk"
        assert r.table_name == "some_table"
        assert r.schema == "schema"
        assert isinstance(r.query_cache, QueryCache)

        with r.conn() as conn:
            assert isinstance(conn, Connection)
            assert conn == pg_conn

        with r.cursor() as cursor:
            assert isinstance(cursor, Cursor)
