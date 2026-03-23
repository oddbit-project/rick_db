from contextlib import contextmanager
from typing import Optional, List, Union

from rick_db import Connection, PoolInterface
from rick_db.manager import ManagerInterface, FieldRecord, UserRecord


class ClickHouseManager(ManagerInterface):
    """
    ClickHouse database manager for introspection operations.

    Uses ClickHouse system.* tables for metadata queries.
    The schema parameter maps to ClickHouse database; when None,
    uses the connection's current database.

    Accepts either a ClickHouseConnection or ClickHouseConnectionPool.
    """

    def __init__(self, db: Union[Connection, PoolInterface], database: str = None):
        if isinstance(db, Connection):
            self._db = db
            self._pool = None
            self.dialect = db.dialect()
            if database is not None:
                self._database = database
            else:
                self._database = db.client.database
        else:
            self._db = None
            self._pool = db
            self.dialect = db.dialect()
            if database is not None:
                self._database = database
            else:
                self._database = db._kwargs.get("database", "default")

    @contextmanager
    def conn(self) -> Connection:
        if self._db:
            yield self._db
        elif self._pool:
            conn = None
            try:
                conn = self._pool.getconn()
                yield conn
            finally:
                if conn is not None:
                    self._pool.putconn(conn)
        else:
            raise RuntimeError("no database connection or pool available")

    def backend(self) -> Union[Connection, PoolInterface]:
        if self._db:
            return self._db
        return self._pool

    def tables(self, schema=None) -> List[str]:
        database = schema or self._database
        sql = (
            "SELECT name FROM system.tables "
            "WHERE database = %s "
            "AND engine NOT IN ('View', 'MaterializedView') "
            "ORDER BY name"
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                rows = c.fetchall(sql, [database])
                return [r["name"] for r in rows]

    def views(self, schema=None) -> List[str]:
        database = schema or self._database
        sql = (
            "SELECT name FROM system.tables "
            "WHERE database = %s "
            "AND engine IN ('View', 'MaterializedView') "
            "ORDER BY name"
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                rows = c.fetchall(sql, [database])
                return [r["name"] for r in rows]

    def schemas(self) -> List[str]:
        return self.databases()

    def databases(self) -> List[str]:
        sql = "SELECT name FROM system.databases ORDER BY name"
        with self.conn() as conn:
            with conn.cursor() as c:
                rows = c.fetchall(sql)
                return [r["name"] for r in rows]

    def table_indexes(self, table_name: str, schema=None) -> List[FieldRecord]:
        database = schema or self._database
        sql = (
            "SELECT name AS field, type_full AS type, 0 AS \"primary\" "
            "FROM system.data_skipping_indices "
            "WHERE database = %s AND table = %s "
            "ORDER BY name"
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                return c.fetchall(sql, [database, table_name], cls=FieldRecord)

    def table_pk(self, table_name: str, schema=None) -> Optional[FieldRecord]:
        database = schema or self._database
        sql = (
            "SELECT name AS field, type, 1 AS \"primary\" "
            "FROM system.columns "
            "WHERE database = %s AND table = %s AND is_in_primary_key = 1 "
            "ORDER BY position"
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                result = c.fetchone(sql, [database, table_name], cls=FieldRecord)
                return result

    def table_fields(self, table_name: str, schema=None) -> List[FieldRecord]:
        database = schema or self._database
        sql = (
            "SELECT name AS field, type, is_in_primary_key AS \"primary\" "
            "FROM system.columns "
            "WHERE database = %s AND table = %s "
            "ORDER BY position"
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                result = c.fetchall(sql, [database, table_name], cls=FieldRecord)
                for r in result:
                    r.primary = r.primary == 1
                return result

    def view_fields(self, view_name: str, schema=None) -> List[FieldRecord]:
        return self.table_fields(view_name, schema)

    def users(self) -> List[UserRecord]:
        sql = "SELECT name FROM system.users ORDER BY name"
        with self.conn() as conn:
            with conn.cursor() as c:
                rows = c.fetchall(sql)
                return [UserRecord(name=r["name"]) for r in rows]

    def user_groups(self, user_name: str) -> List[str]:
        return []

    def table_exists(self, table_name: str, schema=None) -> bool:
        database = schema or self._database
        sql = (
            "SELECT count() AS cnt FROM system.tables "
            "WHERE database = %s AND name = %s"
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                result = c.fetchone(sql, [database, table_name])
                return result is not None and result["cnt"] > 0

    def view_exists(self, view_name: str, schema=None) -> bool:
        database = schema or self._database
        sql = (
            "SELECT count() AS cnt FROM system.tables "
            "WHERE database = %s AND name = %s "
            "AND engine IN ('View', 'MaterializedView')"
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                result = c.fetchone(sql, [database, view_name])
                return result is not None and result["cnt"] > 0

    def create_database(self, database_name: str, **kwargs):
        sql = "CREATE DATABASE IF NOT EXISTS {}".format(
            self.dialect.database(database_name)
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                c.exec(sql)

    def database_exists(self, database_name: str) -> bool:
        sql = "SELECT count() AS cnt FROM system.databases WHERE name = %s"
        with self.conn() as conn:
            with conn.cursor() as c:
                result = c.fetchone(sql, [database_name])
                return result is not None and result["cnt"] > 0

    def drop_database(self, database_name: str):
        sql = "DROP DATABASE IF EXISTS {}".format(
            self.dialect.database(database_name)
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                c.exec(sql)

    def create_schema(self, schema: str, **kwargs):
        raise NotImplementedError("ClickHouse: schemas are databases, use create_database()")

    def schema_exists(self, schema: str) -> bool:
        return self.database_exists(schema)

    def drop_schema(self, schema: str, cascade: bool = False):
        raise NotImplementedError("ClickHouse: schemas are databases, use drop_database()")

    def kill_clients(self, database_name: str):
        raise NotImplementedError("ClickHouse: feature not supported")

    def drop_table(self, table_name: str, cascade: bool = False, schema: str = None):
        sql = "DROP TABLE IF EXISTS {}".format(
            self.dialect.table(table_name, schema=schema)
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                c.exec(sql)

    def drop_view(self, view_name: str, cascade: bool = False, schema: str = None):
        sql = "DROP VIEW IF EXISTS {}".format(
            self.dialect.table(view_name, schema=schema)
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                c.exec(sql)
