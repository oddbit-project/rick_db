import psycopg2
import psycopg2.extras
from psycopg2.extensions import quote_ident
from psycopg2.pool import SimpleConnectionPool, ThreadedConnectionPool
from rick_db.conn import Connection
from rick_db.profiler import Profiler, NullProfiler
from rick_db.sql.dialect import PgSqlDialect


class PgConnection(Connection):

    def __init__(self, **kwargs):
        self._conn = None
        self._in_transaction = False
        kwargs['cursor_factory'] = psycopg2.extras.DictCursor
        conn = psycopg2.connect(**kwargs)
        conn.set_session(isolation_level=self.isolation_level, autocommit=self.autocommit)
        super().__init__(conn)
        self._dialect = PgSqlDialect()

    def quote_identifier(self, value: str) -> str:
        return quote_ident(value, self._conn)


class PgPooledConnection(Connection):

    def __init__(self, pool_manager, db_connection):
        super().__init__(db_connection)
        self._pool = pool_manager
        self._dialect = PgSqlDialect()

    def close(self):
        if self._conn is not None:
            if self._in_transaction:
                self.rollback()
            self._conn.close()
            self._pool.putconn(self._conn)
            self._conn = None


class PgConnectionPool:
    default_min_conn = 5
    default_max_conn = 25
    isolation_level = None
    autocommit = False

    def __init__(self, **kwargs):
        minconn = self.default_min_conn
        maxconn = self.default_max_conn
        kwargs['cursor_factory'] = psycopg2.extras.DictCursor
        if 'minconn' in kwargs:
            minconn = kwargs.pop('minconn')
        if 'maxconn' in kwargs:
            maxconn = kwargs.pop('maxconn')

        self._profiler = NullProfiler()
        self._pool = self._buildPool(minconn, maxconn, kwargs)

    def _buildPool(self, min_conn, max_conn, conf):
        return SimpleConnectionPool(min_conn, max_conn, **conf)

    @property
    def profiler(self):
        return self._profiler

    @profiler.setter
    def profiler(self, profiler: Profiler):
        self._profiler = profiler

    def getconn(self):
        conn = self._pool.getconn()
        conn.set_session(isolation_level=self.isolation_level, autocommit=self.autocommit)
        conn = PgPooledConnection(self, conn)
        conn.profiler = self._profiler
        return conn

    def putconn(self, conn):
        self._pool.putconn(conn)

    def close(self):
        if self._pool is not None:
            self._pool.closeall()
            self._pool = None

    def __del__(self):
        self.close()


class PgThreadedConnectionPool(PgConnectionPool):

    def _buildPool(self, min_conn, max_conn, conf):
        return ThreadedConnectionPool(minconn=min_conn, maxconn=max_conn, **conf)
