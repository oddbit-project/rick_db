from typing import Optional, List

from rick_db.util import Metadata
from rick_db.sql import Select, PgSqlDialect, Literal
from rick_db.util.metadata import FieldRecord, UserRecord


class PgMetadata(Metadata):
    SCHEMA_DEFAULT = 'public'

    def tables(self, schema=None) -> List:
        """
        List all available tables on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of tablenames
        """
        if schema is None:
            schema = self.SCHEMA_DEFAULT

        result = []
        qry = Select(PgSqlDialect()).from_('pg_tables', ['tablename']).where('schemaname', '=', schema)
        with self._db.cursor() as c:
            for r in c.fetchall(*qry.assemble()):
                result.append(r['tablename'])
            return result

    def views(self, schema=None) -> List:
        if schema is None:
            schema = self.SCHEMA_DEFAULT

        result = []
        qry = Select(PgSqlDialect()).from_('pg_views', ['viewname']).where('schemaname', '=', schema)
        with self._db.cursor() as c:
            for r in c.fetchall(*qry.assemble()):
                result.append(r['viewname'])
            return result

    def schemas(self) -> List:
        """
        List all available schemas
        :return: list of schema names
        """
        with self._db.cursor() as c:
            result = []
            for r in c.fetchall(
                    *Select(PgSqlDialect()).from_('schemata', ['schema_name'], 'information_schema').assemble()):
                result.append(r['schema_name'])
            return result

    def databases(self) -> List:
        """
        List all available databases
        :return: list of database names
        """
        with self._db.cursor() as c:
            result = []
            for r in c.fetchall(*Select(PgSqlDialect()).from_('pg_database', ['datname']).assemble()):
                result.append(r['datname'])
            return result

    def table_indexes(self, table_name: str, schema=None) -> List[FieldRecord]:
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
        with self._db.cursor() as c:
            return c.fetchall(sql, params, cls=FieldRecord)

    def table_pk(self, table_name: str, schema=None) -> Optional[FieldRecord]:
        """
        Get primary key from table
        :param table_name:
        :param schema:
        :return:
        """
        for r in self.table_indexes(table_name, schema):
            if r.primary:
                return r
        return None

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
            'column_name': 'field',
            'data_type': 'type',
            Literal('false'): 'primary'
        }
        qry = Select(PgSqlDialect()) \
            .from_('columns', columns, schema='information_schema') \
            .where('table_schema', '=', schema) \
            .where('table_name', '=', table_name) \
            .order('ordinal_position')
        idx = self.table_pk(table_name, schema)
        with self._db.cursor() as c:
            fields = c.fetchall(*qry.assemble(), cls=FieldRecord)  # type:list[FieldRecord]
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
        fields = {
            'usename': 'name',
            'usesuper': 'superuser',
            'usecreatedb': 'createdb'
        }
        with self._db.cursor() as c:
            return c.fetchall(*Select(PgSqlDialect()).from_('pg_user', fields, 'pg_catalog').assemble(), UserRecord)

    def user_groups(self, user_name: str) -> List[str]:
        """
        List all groups associated with a given user
        :param user_name: user name to check
        :return: list of group names
        """
        qry = Select(PgSqlDialect()) \
            .from_('pg_user', {'rolname': 'name'}) \
            .join('pg_auth_members', 'member', 'pg_user', 'usesysid') \
            .join('pg_roles', 'oid', 'pg_auth_members', 'roleid') \
            .where('usename', '=', user_name)

        result = []
        with self._db.cursor() as c:
            for r in c.fetchall(*qry.assemble()):
                result.append(r['name'])
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

        qry = Select(PgSqlDialect()).from_('pg_tables', ['tablename']) \
            .where('schemaname', '=', schema) \
            .where('tablename', '=', table_name)
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

        qry = Select(PgSqlDialect()).from_('pg_views', ['viewname']) \
            .where('schemaname', '=', schema) \
            .where('viewname', '=', view_name)
        with self._db.cursor() as c:
            return len(c.fetchall(*qry.assemble())) > 0
