from contextlib import contextmanager
import logging
import threading
import psycopg2
import psycopg2.extras
from psycopg2.extensions import quote_ident, ISOLATION_LEVEL_READ_COMMITTED
from psycopg2.pool import SimpleConnectionPool, ThreadedConnectionPool, PoolError
from rick_db import Connection, PoolInterface

from rick_db.profiler import NullProfiler
from rick_db.sql import SqlDialect
from rick_db.sql.dialect import PgSqlDialect

logger = logging.getLogger("rick_db.backend.pg")


class PgConnectionPool(PoolInterface):
    default_isolation_level = ISOLATION_LEVEL_READ_COMMITTED
    default_min_conn = 5
    default_max_conn = 25

    def __init__(self, **kwargs):
        """
        Build a PG Connection pool
        :param kwargs:
        """
        self._lock = threading.Lock()
        self.profiler = NullProfiler()
        self._dialect = PgSqlDialect()
        self.ping = True  # if true, connections are "pinged" for validity

        kwargs["cursor_factory"] = psycopg2.extras.DictCursor
        minconn = kwargs.pop("minconn", self.default_min_conn)
        maxconn = kwargs.pop("maxconn", self.default_max_conn)

        self._isolation_level = kwargs.pop(
            "isolation_level", self.default_isolation_level
        )
        self._autocommit = kwargs.pop("autocommit", False)

        self._factory = Connection  # connection factory class
        self._pool = self._buildPool(minconn, maxconn, kwargs)

    def dialect(self) -> SqlDialect:
        return self._dialect

    def connection_factory(self, factory):
        """
        Assign a connection class to be used as factory for connections
        :param factory:
        :return:
        """
        with self._lock:
            self._factory = factory

    def _buildPool(self, min_conn, max_conn, conf):
        return ThreadedConnectionPool(min_conn, max_conn, **conf)

    @contextmanager
    def connection(self) -> Connection:
        """
        contextmanager to fetch a connection from the pool
        :return:
        """
        conn = None
        try:
            conn = self.getconn()
            yield conn
        finally:
            if conn:
                self.putconn(conn)

    def getconn(self) -> Connection:
        """
        Fech a connection from the pool
        The connection is tested for conectivity
        :return:
        """
        if not self._pool:
            raise PoolError("Connection pool not initialized")

        tries = 0
        dbconn = None
        while (dbconn is None) and (tries < self._pool.maxconn):
            try:
                with self._lock:
                    dbconn = self._pool.getconn()
                    ping = self.ping

                if ping:
                    # test if connection is alive
                    dbconn.autocommit = True
                    cur = dbconn.cursor()
                    cur.execute("SELECT 1")
                    cur.close()

            except psycopg2.OperationalError:
                logger.warning(
                    "feching connection from pool failed (stale connection), retrying..."
                )
                with self._lock:
                    self._pool.putconn(dbconn, close=True)
                dbconn = None
                tries += 1

        if dbconn is None:
            raise PoolError("Cannot connect to database, no connections available")

        dbconn.set_session(
            isolation_level=self._isolation_level, autocommit=self._autocommit
        )

        # create connection object
        return self._factory(self, dbconn, self._dialect, self.profiler)

    def putconn(self, conn: Connection):
        with self._lock:
            if conn.db:
                self._pool.putconn(conn.db)
                conn.db = None

    def close(self):
        """
        Closes all connections and invalidates the pool
        :return:
        """
        with self._lock:
            if self._pool:
                self._pool.closeall()
                self._pool = None
