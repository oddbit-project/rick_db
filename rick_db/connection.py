from contextlib import contextmanager
from typing import Optional, List, Any

from rick_db.profiler import ProfilerInterface, NullProfiler
from timeit import default_timer

from rick_db.sql.dialect import SqlDialect


class ConnectionError(Exception):
    pass


class CursorInterface:

    def close(self):
        pass

    def lastrowid(self) -> Optional[Any]:
        pass

    def exec(self, qry: str, params=None, cls=None) -> Optional[List]:
        pass

    def fetchone(self, qry: str, params=None, cls=None) -> Optional[object]:
        pass

    def fetchall(self, qry: str, params=None, cls=None) -> Optional[List]:
        pass


class ConnectionInterface:
    def dialect(self) -> SqlDialect:
        pass

    def get_cursor(self):
        pass

    def begin(self):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def in_transaction(self) -> bool:
        pass

    def close(self):
        pass


class PoolInterface:
    def dialect(self) -> SqlDialect:
        pass

    def getconn(self) -> ConnectionInterface:
        pass

    def putconn(self, conn: ConnectionInterface):
        pass

    def connection(self) -> ConnectionInterface:
        pass


class Connection(ConnectionInterface):

    def __init__(
        self,
        pool: Optional[PoolInterface],
        db_connection,
        dialect: SqlDialect,
        profiler: ProfilerInterface = NullProfiler(),
    ):
        """
        Initializes a connection
        :param pool: optional pool instance
        :param db_connection: the db connection instance
        :param dialect: SQL dialect
        :param profiler: optional profiler
        """
        self.db = db_connection
        self.pool = pool
        self._dialect = dialect
        self._in_transaction = False
        self._cursor_factory = Cursor
        self.profiler = profiler
        # autocommit can either be defined at inherited instances or
        # imported from the database adapter
        if getattr(self, "autocommit", None) is None:
            v = getattr(self.db, "autocommit", None)
            if v != None:
                self.autocommit = v
            else:
                raise RuntimeError("cannot automatically set autocommit status")

    def get_cursor(self):
        """
        Creates a new cursor
        :return:
        """
        return self._cursor_factory(self)

    @contextmanager
    def cursor(self) -> CursorInterface:
        try:
            c = self.get_cursor()
            yield c
        finally:
            c.close()

    def begin(self):
        """
        Initializes a transaction on the connection
        :return:
        """
        if self.autocommit not in [False, -1]:
            raise ConnectionError(
                "begin(): autocommit enabled, transactions are implicit"
            )
        if not self._in_transaction:
            self._in_transaction = True
        else:
            raise ConnectionError("begin(): transaction already opened")

    def commit(self):
        """
        Commits any pending changes to the database
        If inside a transaction, transaction is finalized
        :return:
        """
        if self.db:
            self.db.commit()
        if self._in_transaction:
            self._in_transaction = False

    def rollback(self):
        """
        Rollbacks any pending changes to the database
        :return:
        """
        if self.db:
            self.db.rollback()
        if self._in_transaction:
            self._in_transaction = False

    def in_transaction(self) -> bool:
        """
        Returns true if connection is running a transaction
        :return:
        """
        return self._in_transaction

    def dialect(self) -> SqlDialect:
        return self._dialect

    def close(self):
        """
        Close current connection
        Any pending operations are rolled back
        :return:
        """
        if self.db is not None:
            if self._in_transaction:
                self.rollback()

            # if pooled connection, return to pool
            if self.pool:
                self.pool.putconn(self)
                return

            self.db.close()
            self.db = None


class Cursor(CursorInterface):
    def __init__(self, conn: Connection):
        """
        Creates a new cursor from a connection
        :param conn:
        """
        super().__init__()
        self.conn = conn
        self.profiler = conn.profiler
        self.cursor = conn.db.cursor()

    @staticmethod
    def _timer():
        return default_timer()

    @staticmethod
    def _elapsed(start: float):
        return default_timer() - start

    def lastrowid(self):
        """
        Fetch last rowid
        :return:
        """
        if self.cursor:
            return getattr(self.cursor, "lastrowid", None)

    def close(self):
        """
        Closes current cursor
        operations are auto-comitted if not in transaction
        :return:
        """
        if self.cursor is not None:
            if not self.conn.in_transaction():
                self.conn.commit()
            self.cursor.close()
            self.cursor = None

    def exec(self, qry: str, params=None, cls=None) -> Optional[List]:
        """
        Executes a query against the database
        if cls is not None, the result record will be converted to cls()
        :param qry:
        :param params:
        :param cls:
        :return:
        """
        result = None
        cursor = self.cursor
        timer = self._timer()
        if params is not None:
            cursor.execute(qry, params)
        else:
            cursor.execute(qry)

        if cursor.description:
            result = cursor.fetchall()

        # if not in transaction, write queries require explicit commit
        if not self.conn.in_transaction():
            self.conn.commit()

        self.profiler.add_event(qry, params, self._elapsed(timer))
        if result is None:
            return []

        if cls is not None:
            tmp = []
            for r in result:
                tmp.append(cls().fromrecord(r))
            return tmp

        return result

    def fetchone(self, qry: str, params=None, cls=None) -> Optional[object]:
        """
        Fetch a single row from the database
        if cls is not None, each result record will be converted to cls()
        :param qry:
        :param params:
        :param cls:
        :return:
        """
        result = None
        cursor = self.cursor
        timer = self._timer()
        if params is not None:
            cursor.execute(qry, params)
        else:
            cursor.execute(qry)

        if cursor.description:
            result = cursor.fetchone()
        self.profiler.add_event(qry, params, self._elapsed(timer))

        if result is None:
            return result

        if cls is not None:
            return cls().fromrecord(result)
        return result

    def fetchall(self, qry: str, params=None, cls=None) -> Optional[List]:
        """
        Fetch a list of rows from the database
        if cls is not None, each row will be converted to cls()
        :param qry:
        :param params:
        :param cls:
        :return:
        """
        result = None
        cursor = self.cursor
        timer = self._timer()
        if params is not None:
            cursor.execute(qry, params)
        else:
            cursor.execute(qry)

        if cursor.description:
            result = cursor.fetchall()

        self.profiler.add_event(qry, params, self._elapsed(timer))

        if result is None:
            return []

        if cls is not None:
            tmp = []
            for r in result:
                tmp.append(cls().fromrecord(r))
            return tmp
        return result
