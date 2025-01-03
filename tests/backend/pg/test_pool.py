import pytest
from psycopg2.pool import PoolError
from rick_db import Cursor, Connection
from rick_db.backend.pg import PgConnection, PgConnectionPool
from rick_db.profiler import NullProfiler
from rick_db.sql import PgSqlDialect


class SampleConnection(Connection):
    pass


class TestPool:

    def test_pool(self, pg_pool: PgConnectionPool):
        assert pg_pool is not None
        assert pg_pool.default_isolation_level == PgConnection.default_isolation_level
        assert pg_pool.default_isolation_level == 1
        assert pg_pool.profiler is not None
        assert isinstance(pg_pool.profiler, NullProfiler)
        assert isinstance(pg_pool.dialect(), PgSqlDialect)
        assert type(pg_pool._factory) == type(Cursor)
        assert pg_pool._pool is not None

    def test_pool_cursor(self, pg_pool: PgConnectionPool):
        conn = pg_pool.getconn()
        assert conn is not None
        assert isinstance(conn, Connection)
        cursor = conn.get_cursor()
        assert isinstance(cursor, Cursor)

        result = cursor.fetchone("select 1")
        assert isinstance(result, list)
        assert result[0] == 1
        pg_pool.putconn(conn)
        assert conn.db is None
        # call twice, should have no effect
        pg_pool.putconn(conn)

    def test_getconn_closed(self, pg_pool: PgConnectionPool):
        pg_pool.close()
        with pytest.raises(PoolError):
            with pg_pool.getconn():
                pass

    def test_pool_ctx(self, pg_pool: PgConnectionPool):
        with pg_pool.connection() as conn:
            assert conn is not None
            assert isinstance(conn, Connection)

    def test_pool_exhaust(self, pg_pool: PgConnectionPool):
        conns = []
        with pytest.raises(PoolError):
            # exhaust pool
            for i in range(100):
                conns.append(pg_pool.getconn())
        assert len(conns) > 0
        for conn in conns:
            pg_pool.putconn(conn)

    def test_pool_factory(self, pg_pool: PgConnectionPool):
        assert type(pg_pool._factory) == type(Connection)
        pg_pool.connection_factory(SampleConnection)
        assert type(pg_pool._factory) == type(SampleConnection)
        with pg_pool.connection() as conn:
            assert isinstance(conn, SampleConnection)
