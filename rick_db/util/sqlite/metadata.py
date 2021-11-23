from rick_db.sql import Sqlite3SqlDialect, Select
from rick_db.util import Metadata
from rick_db.util.metadata import FieldRecord, UserRecord


class Sqlite3Metadata(Metadata):

    def tables(self, schema=None) -> list:
        """
        List all available tables on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of tablenames
        """
        qry = Select(Sqlite3SqlDialect()).from_('sqlite_master').where('type', '=', 'table')
        result = []
        with self._db.cursor() as c:
            for r in c.fetchall(*qry.assemble()):
                result.append(r['name'])
        return result

    def views(self, schema=None) -> list:
        """
        List all available views on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of tablenames
        """
        qry = Select(Sqlite3SqlDialect()).from_('sqlite_master').where('type', '=', 'view')
        result = []
        with self._db.cursor() as c:
            for r in c.fetchall(*qry.assemble()):
                result.append(r['name'])
        return result

    def schemas(self) -> list:
        """
        List all available schemas
        :return: list of schema names
        """
        return []

    def databases(self) -> list:
        """
        List all available databases
        :return: list of database names
        """
        return []

    def table_keys(self, table_name: str, schema=None) -> list[FieldRecord]:
        """
        List all keys on a given table
        :param table_name:
        :param schema:
        :return:
        """
        sql = """
        SELECT 
            m.tbl_name as table_name,
            ii.name as field,
            CASE il.origin when 'pk' then 1 else 0 END as primary
        FROM sqlite_master AS m,
            pragma_index_list(m.name) AS il,
            pragma_index_info(il.name) AS ii
        WHERE 
            m.type = 'table'
            and m.tbl_name = %s
        GROUP BY
            m.tbl_name,
            ii.name,
            il.seq
        ORDER BY 1,3
        """
        with self._db.cursor() as c:
            return c.fetchall(sql, (table_name,), FieldRecord)

    def table_pk(self, table_name: str, schema=None) -> [FieldRecord, None]:
        """
        Get primary key from table
        :param table_name:
        :param schema:
        :return:
        """
        for r in self.table_keys(table_name, schema):
            if r.primary:
                return r
        return None

    def users(self) -> list[UserRecord]:
        """
        List all available users
        :return:
        """
        return []

    def user_groups(self, user_name: str) -> list[str]:
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
        qry = Select(Sqlite3SqlDialect()) \
            .from_('sqlite_master', ['name']) \
            .where('name', '=', table_name) \
            .where('type', '=', 'table')
        with self._db.cursor() as c:
            return len(c.fetchall(*qry.assemble())) > 0

    def view_exists(self, view_name: str, schema=None) -> bool:
        """
        Check if a given view exists
        :param view_name: table name
        :param schema: optional schema
        :return:
        """
        qry = Select(Sqlite3SqlDialect()) \
            .from_('sqlite_master', ['name']) \
            .where('name', '=', view_name) \
            .where('type', '=', 'view')
        with self._db.cursor() as c:
            return len(c.fetchall(*qry.assemble())) > 0
