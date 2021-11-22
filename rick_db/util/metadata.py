from rick_db import fieldmapper
from rick_db.conn import Connection


@fieldmapper
class FieldRecord:
    field = 'field'
    type = 'type'
    primary = 'primary'


@fieldmapper()
class UserRecord:
    name = 'name'
    superuser = 'superuser'
    createdb = 'createdb'


class Metadata:

    def __init__(self, db: Connection):
        self._db = db

    def tables(self, schema=None) -> list:
        """
        List all available tables on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of tablenames
        """
        pass

    def views(self, schema=None) -> list:
        """
        List all available views on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of tablenames
        """
        pass

    def schemas(self) -> list:
        """
        List all available schemas
        :return: list of schema names
        """
        pass

    def databases(self) -> list:
        """
        List all available databases
        :return: list of database names
        """
        pass

    def table_keys(self, table_name: str, schema=None) -> list[FieldRecord]:
        """
        List all keys on a given table
        :param table_name:
        :param schema:
        :return:
        """
        pass

    def table_pk(self, table_name: str, schema=None) -> [FieldRecord, None]:
        """
        Get primary key from table
        :param table_name:
        :param schema:
        :return:
        """
        pass

    def users(self) -> list[UserRecord]:
        """
        List all available users
        :return:
        """
        pass

    def user_groups(self, user_name: str) -> list[str]:
        """
        List all groups associated with a given user
        :param user_name: user name to check
        :return: list of group names
        """
        pass

    def table_exists(self, table_name: str, schema=None) -> bool:
        """
        Check if a given table exists
        :param table_name: table name
        :param schema: optional schema
        :return:
        """
        pass

    def view_exists(self, view_name: str, schema=None) -> bool:
        """
        Check if a given view exists
        :param view_name: table name
        :param schema: optional schema
        :return:
        """
        pass
