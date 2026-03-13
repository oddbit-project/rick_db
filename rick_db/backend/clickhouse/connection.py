from rick_db import Connection
from rick_db.sql import ClickHouseSqlDialect


class ClickHouseCursorWrapper:
    """
    DB-API 2.0 cursor wrapper for clickhouse-connect Client.

    The clickhouse-connect Client doesn't follow the DB-API 2.0 spec,
    so this wrapper provides the interface that rick_db's Cursor class expects.
    """

    # Query prefixes that return result sets
    _SELECT_PREFIXES = ("SELECT", "SHOW", "DESCRI", "WITH", "EXPLAI")

    def __init__(self, client):
        self._client = client
        self._rows = []
        self._description = None
        self.lastrowid = None

    def execute(self, query, params=None):
        if params is not None:
            params = tuple(params) if isinstance(params, list) else params

        query_type = query.lstrip()[:6].upper()
        if query_type.startswith(self._SELECT_PREFIXES):
            result = self._client.query(query, parameters=params or None)
            self._description = [(name,) for name in result.column_names]
            self._rows = [
                dict(zip(result.column_names, row))
                for row in result.result_rows
            ]
        else:
            self._client.command(query, parameters=params or None)
            self._description = None
            self._rows = []

    @property
    def description(self):
        return self._description

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def close(self):
        self._rows = []
        self._description = None


class ClickHouseClientWrapper:
    """
    DB-API 2.0 connection wrapper for clickhouse-connect Client.

    Provides cursor(), commit(), rollback(), close() methods that
    rick_db's Connection base class expects.
    """

    def __init__(self, client):
        self._client = client
        self.autocommit = False

    def cursor(self):
        return ClickHouseCursorWrapper(self._client)

    def commit(self):
        pass  # no-op: ClickHouse has no transactions

    def rollback(self):
        pass  # no-op

    def close(self):
        self._client.close()


class ClickHouseConnection(Connection):
    """
    ClickHouse connection using clickhouse-connect HTTP client.

    ClickHouse has no real transactions - each statement is its own unit of work.
    commit() and rollback() are no-ops. The transaction() context manager on
    Repository will work without errors but provides no atomicity guarantees.
    """

    def __init__(self, **kwargs):
        import clickhouse_connect

        client = clickhouse_connect.get_client(**kwargs)
        wrapper = ClickHouseClientWrapper(client)
        self.autocommit = False
        super().__init__(None, wrapper, ClickHouseSqlDialect())

    @property
    def client(self):
        """Access the underlying clickhouse-connect Client"""
        return self.db._client
