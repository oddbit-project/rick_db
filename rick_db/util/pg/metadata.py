from typing import Optional, List

from rick_db.conn import Connection
from rick_db.util import Metadata
from rick_db.sql import Select, Literal
from rick_db.util.metadata import FieldRecord, UserRecord
from .pginfo import PgInfo


class PgMetadata(Metadata):
    SCHEMA_DEFAULT = "public"

    def __init__(self, db: Connection):
        super().__init__(db)
        self.pginfo = PgInfo(db)

    def tables(self, schema=None) -> List[str]:
        """
        List all available tables on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of tablenames
        """
        if schema is None:
            schema = self.SCHEMA_DEFAULT

        result = [t.name for t in self.pginfo.list_database_tables(schema)]
        return result

    def views(self, schema=None) -> List[str]:
        """
        List all available views on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of tablenames
        """
        if schema is None:
            schema = self.SCHEMA_DEFAULT

        result = [t.name for t in self.pginfo.list_database_views(schema)]
        return result

    def schemas(self) -> List[str]:
        """
        List all available schemas
        :return: list of schema names
        """
        result = [t.name for t in self.pginfo.list_database_schemas()]
        return result

    def databases(self) -> List[str]:
        """
        List all available databases
        :return: list of database names
        """
        result = [t.name for t in self.pginfo.list_server_databases()]
        return result

    def table_indexes(self, table_name: str, schema=None) -> List[FieldRecord]:
        """
        List all indexes on a given table
        :param table_name:
        :param schema:
        :return:
        """
        return self.pginfo.list_table_indexes(table_name, schema)

    def table_pk(self, table_name: str, schema=None) -> Optional[FieldRecord]:
        """
        Get primary key from table
        :param table_name:
        :param schema:
        :return:
        """
        pk = self.pginfo.list_table_pk(table_name, schema)
        if pk is None:
            return None
        return FieldRecord(field=pk.column, primary=True)

    def table_fields(self, table_name: str, schema=None) -> List[FieldRecord]:
        """
        Get fields of table
        :param table_name:
        :param schema:
        :return:
        """
        if schema is None:
            schema = self.SCHEMA_DEFAULT

        columns = {
            "column_name": "field",
            "data_type": "type",
            Literal("false"): "primary",
        }
        qry = (
            Select(self._db.dialect())
            .from_("columns", columns, schema="information_schema")
            .where("table_schema", "=", schema)
            .where("table_name", "=", table_name)
            .order("ordinal_position")
        )
        idx = self.table_pk(table_name, schema)
        with self._db.cursor() as c:
            fields = c.fetchall(
                *qry.assemble(), cls=FieldRecord
            )  # type:list[FieldRecord]
            if idx is not None:
                for f in fields:
                    f.primary = f.field == idx.field
            return fields

    def view_fields(self, view_name: str, schema=None) -> List[FieldRecord]:
        """
        Get fields of view
        :param view_name:
        :param schema:
        :return:
        """
        # table_fields() implementation actually doesn't distinguish between table and view
        return self.table_fields(view_name, schema)

    def users(self) -> List[UserRecord]:
        """
        List all available users
        :return:
        """
        fields = {"usename": "name", "usesuper": "superuser", "usecreatedb": "createdb"}
        with self._db.cursor() as c:
            return c.fetchall(
                *Select(self._db.dialect())
                .from_("pg_user", fields, "pg_catalog")
                .assemble(),
                UserRecord
            )

    def user_groups(self, user_name: str) -> List[str]:
        """
        List all groups associated with a given user
        :param user_name: username to check
        :return: list of group names
        """
        qry = (
            Select(self._db.dialect())
            .from_("pg_user", {"rolname": "name"})
            .join("pg_auth_members", "member", "pg_user", "usesysid")
            .join("pg_roles", "oid", "pg_auth_members", "roleid")
            .where("usename", "=", user_name)
        )

        result = []
        with self._db.cursor() as c:
            for r in c.fetchall(*qry.assemble()):
                result.append(r["name"])
        return result

    def table_exists(self, table_name: str, schema=None) -> bool:
        """
        Check if a given table exists
        :param table_name: table name
        :param schema: optional schema
        :return:
        """
        if schema is None:
            schema = self.SCHEMA_DEFAULT

        qry = (
            Select(self._db.dialect())
            .from_("pg_tables", ["tablename"])
            .where("schemaname", "=", schema)
            .where("tablename", "=", table_name)
        )
        with self._db.cursor() as c:
            return len(c.fetchall(*qry.assemble())) > 0

    def view_exists(self, view_name: str, schema=None) -> bool:
        """
        Check if a given view exists
        :param view_name: table name
        :param schema: optional schema
        :return:
        """
        if schema is None:
            schema = self.SCHEMA_DEFAULT

        qry = (
            Select(self._db.dialect())
            .from_("pg_views", ["viewname"])
            .where("schemaname", "=", schema)
            .where("viewname", "=", view_name)
        )
        with self._db.cursor() as c:
            return len(c.fetchall(*qry.assemble())) > 0

    def create_database(self, database_name: str, **kwargs):
        """
        Create a database
        :param database_name: database name
        :param kwargs: optional parameters
        :return:
        """
        dialect = self._db.dialect()
        args = []
        for k, v in kwargs.items():
            args = "=".join([k.upper(), dialect.database(v)])
        args = " ".join(args)

        backend = self._db.backend()
        backend.set_isolation_level(0)  # ISOLATION_LEVEL_AUTOCOMMIT

        sql = "CREATE DATABASE {db} {args}".format(
            db=dialect.database(database_name), args=args
        )
        with self._db.cursor() as c:
            c.exec(sql)
        backend.set_isolation_level(self._db.isolation_level)

    def database_exists(self, database_name: str) -> bool:
        """
        Checks if a given database exists
        :param database_name: database name
        :return: bool
        """
        return database_name in self.databases()

    def drop_database(self, database_name: str):
        """
        Removes a database
        :param database_name: database name
        :return:
        """
        self.kill_clients(database_name)
        dialect = self._db.dialect()

        backend = self._db.backend()
        backend.set_isolation_level(0)  # ISOLATION_LEVEL_AUTOCOMMIT
        with self._db.cursor() as c:
            c.exec(
                "DROP DATABASE IF EXISTS {db}".format(
                    db=dialect.database(database_name)
                )
            )
        backend.set_isolation_level(self._db.isolation_level)

    def create_schema(self, schema: str, **kwargs):
        """
        Create a new schema
        :param schema:
        :return:
        """
        dialect = self._db.dialect()
        authorization = (
            kwargs["authorization"] if "authorization" in kwargs.keys() else None
        )
        sql = "CREATE SCHEMA IF NOT EXISTS {schema}".format(
            schema=dialect.database(schema)
        )
        if authorization:
            sql = sql + " AUTHORIZATION {role}".format(
                role=dialect.database(authorization)
            )
        with self._db.cursor() as c:
            c.exec(sql)

    def schema_exists(self, schema: str) -> bool:
        """
        Check if a given schema exists on the current database
        :param schema:
        :return: bool
        """
        return schema in self.schemas()

    def drop_schema(self, schema: str, cascade: bool = False):
        """
        Removes a schema
        :param schema:
        :param cascade:
        :return:
        """
        dialect = self._db.dialect()
        sql = "DROP SCHEMA IF EXISTS {schema}".format(schema=dialect.database(schema))
        if cascade:
            sql = sql + " CASCADE"
        with self._db.cursor() as c:
            c.exec(sql)

    def kill_clients(self, database_name: str):
        """
        Kills all active connections to the database
        :param database_name:
        :return:
        """
        with self._db.cursor() as c:
            sql = """
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = %s
            AND pid <> pg_backend_pid();
            """
            c.exec(sql, [database_name])
