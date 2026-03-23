from contextlib import contextmanager
import logging
import threading

from rick_db import Connection, PoolInterface
from rick_db.profiler import NullProfiler
from rick_db.sql import ClickHouseSqlDialect

from .connection import ClickHouseClientWrapper

logger = logging.getLogger("rick_db.backend.clickhouse")


class PoolError(Exception):
    pass


class ClickHouseConnectionPool(PoolInterface):
    """
    Thread-safe connection pool for ClickHouse.

    Note: the profiler instance is captured at connection checkout time.
    Reassigning pool.profiler after connections are already checked out
    will not affect those existing connections.
    """

    default_min_conn = 5
    default_max_conn = 25

    def __init__(self, **kwargs):
        self._lock = threading.Lock()
        self.profiler = NullProfiler()
        self._dialect = ClickHouseSqlDialect()
        self.ping = kwargs.pop("ping", True)

        minconn = kwargs.pop("minconn", self.default_min_conn)
        maxconn = kwargs.pop("maxconn", self.default_max_conn)
        self._autocommit = kwargs.pop("autocommit", False)

        self._factory = Connection
        self._kwargs = kwargs
        self._minconn = minconn
        self._maxconn = maxconn
        self._pool = []
        self._used = {}  # id(wrapper) -> wrapper, for cleanup on close()
        self._closed = False

        self._init_pool(minconn)

    def _init_pool(self, count):
        for _ in range(count):
            self._pool.append(self._create_client())

    def _create_client(self):
        import clickhouse_connect

        client = clickhouse_connect.get_client(**self._kwargs)
        return ClickHouseClientWrapper(client)

    def dialect(self):
        return self._dialect

    def connection_factory(self, factory):
        with self._lock:
            self._factory = factory

    @contextmanager
    def connection(self) -> Connection:
        conn = None
        try:
            conn = self.getconn()
            yield conn
        finally:
            if conn:
                self.putconn(conn)

    def getconn(self) -> Connection:
        if self._closed:
            raise PoolError("Connection pool is closed")

        with self._lock:
            wrapper = self._get_wrapper()

        if self.ping:
            try:
                cursor = wrapper.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
            except Exception:
                logger.warning(
                    "fetching connection from pool failed (stale connection), replacing..."
                )
                try:
                    wrapper.close()
                except Exception:
                    pass
                # create a fresh wrapper and swap it into the slot
                new_wrapper = self._create_client()
                with self._lock:
                    self._used.pop(id(wrapper), None)
                    self._used[id(new_wrapper)] = new_wrapper
                wrapper = new_wrapper

        conn = self._factory(self, wrapper, self._dialect, self.profiler)
        conn.autocommit = self._autocommit
        return conn

    def _get_wrapper(self):
        if self._pool:
            wrapper = self._pool.pop()
            self._used[id(wrapper)] = wrapper
            return wrapper

        if len(self._used) < self._maxconn:
            wrapper = self._create_client()
            self._used[id(wrapper)] = wrapper
            return wrapper

        raise PoolError("Cannot connect to database, no connections available")

    def putconn(self, conn: Connection):
        with self._lock:
            if conn.db is not None:
                self._used.pop(id(conn.db), None)
                if not self._closed:
                    self._pool.append(conn.db)
                else:
                    conn.db.close()
                conn.db = None

    def close(self):
        with self._lock:
            self._closed = True
            for wrapper in self._pool:
                try:
                    wrapper.close()
                except Exception:
                    pass
            self._pool.clear()
            for wrapper in self._used.values():
                try:
                    wrapper.close()
                except Exception:
                    pass
            self._used.clear()
