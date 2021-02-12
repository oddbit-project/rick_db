import sqlite3
from rick_db.conn import Connection


class Sqlite3Connection(Connection):
    isolation_level = ""
    timeout = 5.0

    def __init__(self, file_name:str, **kwargs):
        self._in_transaction = False
        if 'isolation_level' not in kwargs:
            kwargs['isolation_level'] = self.isolation_level
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        conn = sqlite3.connect(file_name, **kwargs)
        conn.row_factory = sqlite3.Row
        super().__init__(conn)
