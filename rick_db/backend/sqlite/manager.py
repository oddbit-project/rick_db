from contextlib import contextmanager
from typing import Optional
from typing import List

from rick_db import Connection
from rick_db.backend.sqlite import Sqlite3Connection
from rick_db.manager import ManagerInterface, FieldRecord, UserRecord
from rick_db.sql import Select


class Sqlite3Manager(ManagerInterface):

    def __init__(self, db: Sqlite3Connection):
        self._db = db
        self.dialect = db.dialect()

    @contextmanager
    def conn(self) -> Connection:
        """
        Fetch connection object
        :return:
        """
        yield self._db

    def backend(self) -> Sqlite3Connection:
        """
        get connection backend without context manager
        :return:
        """
        return self._db

    def tables(self, schema=None) -> List:
        """
        List all available tables on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of tablenames
        """
        qry = Select(self.dialect).from_("sqlite_master").where("type", "=", "table")
        result = []
        with self.conn() as conn:
            with conn.cursor() as c:
                for r in c.fetchall(*qry.assemble()):
                    if not r["name"].startswith("sqlite_"):
                        result.append(r["name"])
        return result

    def views(self, schema=None) -> List:
        """
        List all available views on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of tablenames
        """
        qry = Select(self.dialect).from_("sqlite_master").where("type", "=", "view")
        result = []
        with self.conn() as conn:
            with conn.cursor() as c:
                for r in c.fetchall(*qry.assemble()):
                    if not r["name"].startswith("sqlite_"):
                        result.append(r["name"])
        return result

    def schemas(self) -> List:
        """
        List all available schemas
        :return: list of schema names
        """
        return []

    def databases(self) -> List:
        """
        List all available databases
        :return: list of database names
        """
        return []

    def table_indexes(self, table_name: str, schema=None) -> List[FieldRecord]:
        """
        List all indexes on a given table

        Note: Sqlite does no create indexes for primary keys automatically

        :param table_name:
        :param schema:
        :return:
        """
        sql = """
        SELECT
            ii.name as field,
            ti.type as 'type',
            pk as 'primary'
        FROM sqlite_master AS m,
            pragma_index_list(m.name) AS il,
            pragma_index_info(il.name) AS ii,
            pragma_table_info(m.name) AS ti
        WHERE
            m.type = 'table'
            and m.tbl_name = ?
            and ti.name= ii.name
        GROUP BY
            ii.name,
            il.seq
        ORDER BY 1,2;
        """
        with self.conn() as conn:
            with conn.cursor() as c:
                result = c.fetchall(sql, (table_name,), cls=FieldRecord)
                for r in result:
                    r.primary = r.primary == 1
                return result

    def table_pk(self, table_name: str, schema=None) -> Optional[FieldRecord]:
        """
        Get primary key from table
        :param table_name:
        :param schema:
        :return:
        """
        sql = "select name as field, type, pk as 'primary' from pragma_table_info(?) where pk=1;"
        with self.conn() as conn:
            with conn.cursor() as c:
                return c.fetchone(sql, (table_name,), cls=FieldRecord)

    def table_fields(self, table_name: str, schema=None) -> List[FieldRecord]:
        """
        Return list of fields for table
        :param table_name:
        :param schema:
        :return:
        """
        sql = "select name as field, type, pk as 'primary' from pragma_table_info(?);"
        with self.conn() as conn:
            with conn.cursor() as c:
                result = c.fetchall(sql, (table_name,), cls=FieldRecord)
                for r in result:
                    r.primary = r.primary == 1
                return result

    def view_fields(self, view_name: str, schema=None) -> List[FieldRecord]:
        """
        Return list of fields for view
        :param view_name:
        :param schema:
        :return:
        """
        sql = "select name as field, type from pragma_table_info(?);"
        with self.conn() as conn:
            with conn.cursor() as c:
                result = c.fetchall(sql, (view_name,), cls=FieldRecord)
                for r in result:
                    r.primary = r.primary == 1
                return result

    def users(self) -> List[UserRecord]:
        """
        List all available users
        :return:
        """
        return []

    def user_groups(self, user_name: str) -> List[str]:
        """
        List all groups associated with a given user
        :param user_name: user name to check
        :return: list of group names
        """
        return []

    def table_exists(self, table_name: str, schema=None) -> bool:
        """
        Check if a given table exists
        :param table_name: table name
        :param schema: optional schema
        :return:
        """
        qry = (
            Select(self.dialect)
            .from_("sqlite_master", ["name"])
            .where("name", "=", table_name)
            .where("type", "=", "table")
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                return len(c.fetchall(*qry.assemble())) > 0

    def view_exists(self, view_name: str, schema=None) -> bool:
        """
        Check if a given view exists
        :param view_name: table name
        :param schema: optional schema
        :return:
        """
        qry = (
            Select(self.dialect)
            .from_("sqlite_master", ["name"])
            .where("name", "=", view_name)
            .where("type", "=", "view")
        )
        with self.conn() as conn:
            with conn.cursor() as c:
                return len(c.fetchall(*qry.assemble())) > 0

    def create_database(self, database_name: str, **kwargs):
        """
        Create a database
        :param database_name: database name
        :param kwargs: optional parameters
        :return:
        """
        raise NotImplementedError("SqlLite3: feature not supported")

    def database_exists(self, database_name: str) -> bool:
        """
        Checks if a given database exists
        :param database_name: database name
        :return: bool
        """
        raise NotImplementedError("SqlLite3: feature not supported")

    def drop_database(self, database_name: str):
        """
        Removes a database
        :param database_name: database name
        :return:
        """
        raise NotImplementedError("SqlLite3: feature not supported")

    def create_schema(self, schema: str, **kwargs):
        """
        Create a new schema
        :param schema:
        :return:
        """
        raise NotImplementedError("SqlLite3: feature not supported")

    def schema_exists(self, schema: str) -> bool:
        """
        Check if a given schema exists on the current database
        :param schema:
        :return: bool
        """
        raise NotImplementedError("SqlLite3: feature not supported")

    def drop_schema(self, schema: str, cascade: bool = False):
        """
        Removes a schema
        :param schema:
        :param cascade:
        :return:
        """
        raise NotImplementedError("SqlLite3: feature not supported")

    def kill_clients(self, database_name: str):
        """
        Kills all active connections to the database
        :param database_name:
        :return:
        """
        raise NotImplementedError("SqlLite3: feature not supported")

    def drop_table(self, table_name: str, cascade: bool = False, schema: str = None):
        """
        Removes a table
        :param table_name:
        :param cascade:
        :param schema:
        :return:
        """
        sql = "DROP TABLE IF EXISTS {name}".format(
            name=self.dialect.table(table_name, schema=schema)
        )
        if cascade:
            sql = sql + " CASCADE"
        with self.conn() as conn:
            with conn.cursor() as c:
                c.exec(sql)

    def drop_view(self, view_name: str, cascade: bool = False, schema: str = None):
        """
        Removes a view
        :param view_name:
        :param cascade:
        :param schema:
        :return:
        """
        sql = "DROP VIEW IF EXISTS {name}".format(
            name=self.dialect.table(view_name, schema=schema)
        )
        if cascade:
            sql = sql + " CASCADE"

        with self.conn() as conn:
            with conn.cursor() as c:
                c.exec(sql)
