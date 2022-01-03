from typing import Optional
from typing import List
from rick_db.sql import Sqlite3SqlDialect, Select
from rick_db.util import Metadata
from rick_db.util.metadata import FieldRecord, UserRecord


class Sqlite3Metadata(Metadata):

    def tables(self, schema=None) -> List:
        """
        List all available tables on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of tablenames
        """
        qry = Select(Sqlite3SqlDialect()) \
            .from_('sqlite_master') \
            .where('type', '=', 'table')
        result = []
        with self._db.cursor() as c:
            for r in c.fetchall(*qry.assemble()):
                if not r['name'].startswith('sqlite_'):
                    result.append(r['name'])
        return result

    def views(self, schema=None) -> List:
        """
        List all available views on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of tablenames
        """
        qry = Select(Sqlite3SqlDialect()).from_('sqlite_master').where('type', '=', 'view')
        result = []
        with self._db.cursor() as c:
            for r in c.fetchall(*qry.assemble()):
                if not r['name'].startswith('sqlite_'):
                    result.append(r['name'])
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
        with self._db.cursor() as c:
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
        with self._db.cursor() as c:
            return c.fetchone(sql, (table_name,), cls=FieldRecord)

    def table_fields(self, table_name: str, schema=None) -> List[FieldRecord]:
        """
        Return list of fields for table
        :param table_name:
        :param schema:
        :return:
        """
        sql = "select name as field, type, pk as 'primary' from pragma_table_info(?);"
        with self._db.cursor() as c:
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
        with self._db.cursor() as c:
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
