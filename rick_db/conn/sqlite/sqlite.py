import sqlite3
from rick_db.conn import Connection
from rick_db.sql.dialect import Sqlite3SqlDialect


class Sqlite3Connection(Connection):
    isolation_level = ""
    timeout = 5.0

    def __init__(self, db_file: str, **kwargs):
        self._in_transaction = False
        if 'isolation_level' not in kwargs:
            kwargs['isolation_level'] = self.isolation_level
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        conn = sqlite3.connect(db_file, **kwargs)
        conn.row_factory = self._row_factory
        super().__init__(conn)
        self._dialect = Sqlite3SqlDialect()

    def quote_identifier(self, value: str) -> str:
        raise RuntimeError("sqlite3 does not provide driver-level quoting function")

    @staticmethod
    def _row_factory(cursor, row):
        """
        Dict row factory
        used instead of sqlite3.Row because we need to assign to the dict
        :param cursor:
        :param row:
        :return: dict
        """
        result = {}
        for idx, col in enumerate(cursor.description):
            result[col[0]] = row[idx]
        return result
