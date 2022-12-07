from typing import List, Optional

from rick_db.conn import Connection
from rick_db.sql import Select, PgSqlDialect, Literal
from rick_db.util.metadata import FieldRecord
from rick_db.util.pg.records import (
    DatabaseRecord,
    RoleRecord,
    TableSpaceRecord,
    SettingRecord,
    NamespaceRecord,
    TableRecord,
    ColumnRecord,
    ConstraintRecord,
    KeyColumnUsageRecord,
    UserRecord,
    GroupRecord,
    ForeignKeyRecord,
    IdentityRecord,
)


class PgInfo:
    SCHEMA_DEFAULT = "public"

    # table types
    TYPE_BASE = "BASE TABLE"
    TYPE_VIEW = "VIEW"
    TYPE_FOREIGN = "FOREIGN TABLE"
    TYPE_LOCAL = "LOCAL TEMPORARY"

    def __init__(self, db: Connection):
        self.db = db
        self.dialect = PgSqlDialect()

    def get_server_version(self) -> str:
        """
        Get server version string
        :return: str
        """
        with self.db.cursor() as c:
            result = c.exec(" SELECT version()")
            return result.pop()[0]

    def list_server_databases(self) -> List[DatabaseRecord]:
        """
        List existing databases, ordered by name
        :return: List[DatabaseRecord]
        """
        sql, values = (
            Select(self.dialect)
            .from_(
                {DatabaseRecord: "dr"},
                cols=[
                    "*",
                    {Literal("pg_encoding_to_char(encoding)"): DatabaseRecord.encoding},
                ],
            )
            .order(DatabaseRecord.name)
            .assemble()
        )

        with self.db.cursor() as c:
            return c.exec(sql, values, cls=DatabaseRecord)

    def list_server_roles(self) -> List[RoleRecord]:
        """
        List existing roles, ordered by name
        :return:
        """
        sql, values = (
            Select(self.dialect).from_(RoleRecord).order(RoleRecord.name).assemble()
        )

        with self.db.cursor() as c:
            return c.exec(sql, values, cls=RoleRecord)

    def list_server_users(self) -> List[UserRecord]:
        """
        List existing users, ordered by name
        :return:
        """
        sql, values = (
            Select(self.dialect).from_(UserRecord).order(UserRecord.name).assemble()
        )

        with self.db.cursor() as c:
            return c.exec(sql, values, cls=UserRecord)

    def list_server_groups(self) -> List[GroupRecord]:
        """
        List existing groups, ordered by name
        :return:
        """
        sql, values = (
            Select(self.dialect).from_(GroupRecord).order(GroupRecord.name).assemble()
        )

        with self.db.cursor() as c:
            return c.exec(sql, values, cls=GroupRecord)

    def list_user_groups(self, user_name: str) -> List[GroupRecord]:
        """
        List all groups associated with a username
        :param user_name: username to check
        :return: list of group names
        """
        sql = """
        SELECT * FROM pg_group WHERE pg_group.grosysid IN(
            SELECT pg_roles.oid FROM pg_user
                JOIN pg_auth_members ON (pg_user.usesysid=pg_auth_members.member)
                JOIN pg_roles ON (pg_roles.oid=pg_auth_members.roleid)
            WHERE pg_user.usename = %s);
        """

        with self.db.cursor() as c:
            return c.exec(sql, [user_name], cls=GroupRecord)

    def list_server_tablespaces(self) -> List[TableSpaceRecord]:
        """
        List existing tablespaces, ordered by name
        :return: List[TableSpaceRecord]
        """
        sql, values = (
            Select(self.dialect)
            .from_(TableSpaceRecord)
            .order(TableSpaceRecord.name)
            .assemble()
        )

        with self.db.cursor() as c:
            return c.exec(sql, values, cls=TableSpaceRecord)

    def list_server_settings(self) -> List[SettingRecord]:
        """
        List existing server settings and current values
        :return: List[SettingRecord]
        """
        sql, values = (
            Select(self.dialect)
            .from_(SettingRecord)
            .order(SettingRecord.name)
            .assemble()
        )

        with self.db.cursor() as c:
            return c.exec(sql, values, cls=SettingRecord)

    def list_database_namespaces(self) -> List[NamespaceRecord]:
        """
        List available namespaces on current database
        :return: List[TableRecord]
        """
        sql, values = (
            Select(self.dialect)
            .from_(NamespaceRecord)
            .order(NamespaceRecord.name)
            .assemble()
        )

        with self.db.cursor() as c:
            return c.exec(sql, values, cls=NamespaceRecord)

    def list_database_schemas(self) -> List[NamespaceRecord]:
        """
        List available namespaces on current database
        :return: List[TableRecord]
        """
        sql, values = (
            Select(self.dialect)
            .from_(NamespaceRecord)
            .order(NamespaceRecord.name)
            .assemble()
        )

        with self.db.cursor() as c:
            return c.exec(sql, values, cls=NamespaceRecord)

    def list_database_tables_type(
        self, table_type: str, schema: str = None
    ) -> List[TableRecord]:
        """
        List tables by type for the specified schema
        :param table_type: table type to filter
        :param schema: optional schema, 'public' if omitted
        :return: List[TableRecord]
        """
        if not schema:
            schema = self.SCHEMA_DEFAULT
        sql, values = (
            Select(self.dialect)
            .from_(TableRecord)
            .where(TableRecord.schema, "=", schema)
            .where(TableRecord.table_type, "=", table_type)
            .order(TableRecord.name)
            .assemble()
        )

        with self.db.cursor() as c:
            return c.exec(sql, values, cls=TableRecord)

    def list_database_views(self, schema: str = None) -> List[TableRecord]:
        """
        List all views for the specified schema
        :param schema: optional schema, 'public' if omitted
        :return: List[TableRecord]
        """
        return self.list_database_tables_type(self.TYPE_VIEW, schema)

    def list_database_tables(self, schema: str = None) -> List[TableRecord]:
        """
        List all base tables for the specified schema
        :param schema: optional schema, 'public' if omitted
        :return: List[TableRecord]
        """
        return self.list_database_tables_type(self.TYPE_BASE, schema)

    def list_database_temporary_tables(self, schema: str = None) -> List[TableRecord]:
        """
        List all temporary tables for the specified schema
        :param schema: optional schema, 'public' if omitted
        :return: List[TableRecord]
        """
        return self.list_database_tables_type(self.TYPE_LOCAL, schema)

    def list_database_foreign_tables(self, schema: str = None) -> List[TableRecord]:
        """
        List all foreign tables for the specified schema
        :param schema: optional schema, 'public' if omitted
        :return: List[TableRecord]
        """
        return self.list_database_tables_type(self.TYPE_FOREIGN, schema)

    def list_table_columns(
        self, table_name: str, schema: str = None
    ) -> List[ColumnRecord]:
        """
        List all table columns, sorted by numerical order
        :param table_name:
        :param schema:
        :return: List[ColumnRecord]
        """
        if not schema:
            schema = self.SCHEMA_DEFAULT
        sql, values = (
            Select(self.dialect)
            .from_(ColumnRecord)
            .where(ColumnRecord.schema, "=", schema)
            .where(ColumnRecord.table_name, "=", table_name)
            .order(ColumnRecord.position)
            .assemble()
        )

        with self.db.cursor() as c:
            return c.exec(sql, values, cls=ColumnRecord)

    def list_table_pk(
        self, table_name: str, schema: str = None
    ) -> Optional[ConstraintRecord]:
        """
        List primary key of table
        :param table_name:
        :param schema:
        :return: ConstraintRecord
        """
        if not schema:
            schema = self.SCHEMA_DEFAULT
        sql, values = (
            Select(self.dialect)
            .from_({ConstraintRecord: "cr"})
            .join(
                {KeyColumnUsageRecord: "kc"},
                KeyColumnUsageRecord.name,
                {ConstraintRecord: "cr"},
                ConstraintRecord.const_name,
                "=",
                cols=[KeyColumnUsageRecord.column],
            )
            .where({"cr": ConstraintRecord.schema}, "=", schema)
            .where({"cr": ConstraintRecord.table_name}, "=", table_name)
            .where({"cr": ConstraintRecord.constraint_type}, "=", "PRIMARY KEY")
            .assemble()
        )

        with self.db.cursor() as c:
            result = c.exec(sql, values, cls=ConstraintRecord)
            if len(result) > 0:
                return result.pop()
            return None

    def list_table_indexes(self, table_name: str, schema=None) -> List[FieldRecord]:
        """
        List all indexes on a given table
        :param table_name:
        :param schema:
        :return:
        """
        if schema is None:
            schema = self.SCHEMA_DEFAULT

        sql = """
            SELECT
              pg_attribute.attname AS field,
              format_type(pg_attribute.atttypid, pg_attribute.atttypmod) AS type,
              indisprimary AS primary
            FROM pg_index, pg_class, pg_attribute, pg_namespace
            WHERE
              pg_class.relname = %s AND
              indrelid = pg_class.oid AND
              nspname = %s AND
              pg_class.relnamespace = pg_namespace.oid AND
              pg_attribute.attrelid = pg_class.oid AND
              pg_attribute.attnum = any(pg_index.indkey)
        """
        params = (table_name, schema)
        with self.db.cursor() as c:
            return c.fetchall(sql, params, cls=FieldRecord)

    def list_table_foreign_keys(
        self, table_name, schema: str = None
    ) -> List[ForeignKeyRecord]:
        """
        List foreign keys for a given table

        Query from bob217 on https://stackoverflow.com/questions/1152260/how-to-list-table-foreign-keys

        :param table_name:
        :param schema:
        :return:
        """
        sql = """
            SELECT sh.nspname AS table_schema,
              tbl.relname AS table_name,
              col.attname AS column_name,
              referenced_sh.nspname AS foreign_table_schema,
              referenced_tbl.relname AS foreign_table_name,
              referenced_field.attname AS foreign_column_name
            FROM pg_constraint c
                INNER JOIN pg_namespace AS sh ON sh.oid = c.connamespace
                INNER JOIN (SELECT oid, unnest(conkey) as conkey FROM pg_constraint) con ON c.oid = con.oid
                INNER JOIN pg_class tbl ON tbl.oid = c.conrelid
                INNER JOIN pg_attribute col ON (col.attrelid = tbl.oid AND col.attnum = con.conkey)
                INNER JOIN pg_class referenced_tbl ON c.confrelid = referenced_tbl.oid
                INNER JOIN pg_namespace AS referenced_sh ON referenced_sh.oid = referenced_tbl.relnamespace
                INNER JOIN (SELECT oid, unnest(confkey) as confkey FROM pg_constraint) conf ON c.oid = conf.oid
                INNER JOIN pg_attribute referenced_field ON 
                    (referenced_field.attrelid = c.confrelid AND referenced_field.attnum = conf.confkey)
            WHERE c.contype = 'f' AND sh.nspname = %s AND tbl.relname = %s
        """
        if not schema:
            schema = self.SCHEMA_DEFAULT

        with self.db.cursor() as c:
            return c.fetchall(sql, [schema, table_name], cls=ForeignKeyRecord)

    def table_exists(
        self, table_name: str, table_type: str = None, schema: str = None
    ) -> bool:
        """
        Returns true if the specified table exists
        :param table_name: table name to find
        :param table_type: optional table type, BASE TABLE if omitted
        :param schema: optional schema, 'public' if omitted
        :return: bool
        """
        if not table_type:
            table_type = self.TYPE_BASE

        if not schema:
            schema = self.SCHEMA_DEFAULT

        sql, values = (
            Select(self.dialect)
            .from_(TableRecord)
            .where(TableRecord.schema, "=", schema)
            .where(TableRecord.table_type, "=", table_type)
            .where(TableRecord.name, "=", table_name)
            .assemble()
        )

        with self.db.cursor() as c:
            return len(c.exec(sql, values)) > 0

    def list_identity_columns(self, table, schema: str = None) -> List[IdentityRecord]:
        """
        List IDENTITY columns (if any)
        :param table: table name
        :param schema: optional schema name
        :return: List[IdentityRecord]
        """
        if not schema:
            schema = self.SCHEMA_DEFAULT

        sql, values = (
            Select(self.db.dialect())
            .from_(
                IdentityRecord,
                cols=[
                    IdentityRecord.column,
                    IdentityRecord.identity,
                    IdentityRecord.generated,
                ],
            )
            .join({"pg_class": "c"}, "oid", IdentityRecord, "attrelid")
            .join({"pg_namespace": "n"}, "oid", "c", "relnamespace")
            .where("attnum", ">", 0)
            .where({"c": "relname"}, "=", table)
            .where({"n": "nspname"}, "=", schema)
            .where_and()
            .where(IdentityRecord.identity, "!=", "")
            .orwhere(IdentityRecord.generated, "!=", "")
            .where_end()
            .assemble()
        )

        with self.db.cursor() as c:
            return c.exec(sql, values, cls=IdentityRecord)
