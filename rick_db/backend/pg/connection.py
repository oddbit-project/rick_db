import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED

from rick_db import Connection
from rick_db.sql import PgSqlDialect


class PgConnection(Connection):
    default_isolation_level = ISOLATION_LEVEL_READ_COMMITTED

    def __init__(self, **kwargs):
        self._conn = None
        self._in_transaction = False
        kwargs["cursor_factory"] = psycopg2.extras.DictCursor

        isolation_level = kwargs.pop("isolation_level", self.default_isolation_level)
        autocommit = kwargs.pop("autocommit", False)

        conn = psycopg2.connect(**kwargs)
        conn.set_session(isolation_level=isolation_level, autocommit=autocommit)
        super().__init__(None, conn, PgSqlDialect())
