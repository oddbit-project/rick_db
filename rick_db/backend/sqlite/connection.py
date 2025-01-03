import sqlite3
import sys

from rick_db import Connection
from rick_db.sql.dialect import Sqlite3SqlDialect


class Sqlite3Connection(Connection):
    default_isolation_level = "DEFERRED"
    default_auto_commit = False
    timeout = 5.0

    def __init__(self, db_file: str, **kwargs):
        self._in_transaction = False
        if "isolation_level" not in kwargs:
            kwargs["isolation_level"] = self.default_isolation_level

        version = sys.version_info
        # python >=3.12 sqlite supports PEP249 autocommit property
        if version >= (3, 12):
            if "autocommit" not in kwargs:
                kwargs["autocommit"] = self.default_auto_commit
        else:
            self.autocommit = kwargs["isolation_level"] is None

        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        conn = sqlite3.connect(db_file, **kwargs)

        conn.row_factory = self._row_factory
        super().__init__(None, conn, Sqlite3SqlDialect())

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
