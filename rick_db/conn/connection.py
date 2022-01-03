from rick_db.profiler import Profiler, NullProfiler
from timeit import default_timer

from rick_db.sql.dialect import SqlDialect


class ConnectionError(Exception):
    pass


class Cursor:

    def __init__(self, conn, profiler, cursor, in_transaction=False):
        super().__init__()
        self._conn = conn
        self._profiler = profiler
        self._cursor = cursor
        self._in_transaction = in_transaction

    @staticmethod
    def _timer():
        return default_timer()

    @staticmethod
    def _elapsed(start: float):
        return default_timer() - start

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if self._cursor is not None:
            if not self._in_transaction:
                self._conn.commit()
            self._cursor.close()
            self._cursor = None

    def exec(self, qry: str, params=None, cls=None):
        result = None
        cursor = self._cursor
        timer = self._timer()
        if params is not None:
            cursor.execute(qry, params)
        else:
            cursor.execute(qry)
        if not self._in_transaction:
            self._conn.commit()
        if cursor.description:
            result = cursor.fetchall()
        self._profiler.add_event(qry, params, self._elapsed(timer))
        if result is None:
            return []

        if cls is not None:
            tmp = []
            for r in result:
                tmp.append(cls().fromrecord(r))
            return tmp
        return result

    def fetchone(self, qry: str, params=None, cls=None):
        result = None
        cursor = self._cursor
        timer = self._timer()
        if params is not None:
            cursor.execute(qry, params)
        else:
            cursor.execute(qry)
        if cursor.description:
            result = cursor.fetchone()
        self._profiler.add_event(qry, params, self._elapsed(timer))
        if result is None:
            return result

        if cls is not None:
            return cls().fromrecord(result)
        return result

    def fetchall(self, qry: str, params=None, cls=None):
        result = None
        cursor = self._cursor
        timer = self._timer()
        if params is not None:
            cursor.execute(qry, params)
        else:
            cursor.execute(qry)
        if cursor.description:
            result = cursor.fetchall()
        self._profiler.add_event(qry, params, self._elapsed(timer))
        if result is None:
            return []

        if cls is not None:
            tmp = []
            for r in result:
                tmp.append(cls().fromrecord(r))
            return tmp
        return result

    def get_cursor(self):
        return self._cursor


class Connection:
    autocommit = False
    isolation_level = None

    def __init__(self, db_connection):
        self._in_transaction = False
        self._profiler = NullProfiler()
        self._conn = db_connection
        self._dialect = None

    @property
    def profiler(self):
        return self._profiler

    @profiler.setter
    def profiler(self, profiler: Profiler):
        self._profiler = profiler

    def dialect(self) -> SqlDialect:
        """
        Retrieve connection SQL Dialect
        :return: SqlDialect
        """
        return self._dialect

    def begin(self):
        if self.autocommit:
            raise ConnectionError("begin(): autocommit enabled, transactions are implicit")
        if not self._in_transaction:
            self._in_transaction = True
        else:
            raise ConnectionError("begin(): transaction already opened")

    def commit(self):
        self._conn.commit()
        if self._in_transaction:
            self._in_transaction = False

    def rollback(self):
        self._conn.rollback()
        if self._in_transaction:
            self._in_transaction = False

    def cursor(self) -> Cursor:
        return Cursor(self._conn, self._profiler, self._conn.cursor(), self._in_transaction)

    def backend(self):
        return self._conn

    def transaction_status(self) -> bool:
        return self._in_transaction

    def quote_identifier(self, value: str) -> str:
        raise RuntimeError("virtual method, overriding required")

    def close(self):
        if self._conn is not None:
            if self._in_transaction:
                self.rollback()
            self._conn.close()
            self._conn = None

    def __del__(self):
        self.close()
