from contextlib import contextmanager
from typing import Optional, Union
from typing import List

from . import Connection, PoolInterface
from .mapper import fieldmapper


@fieldmapper
class FieldRecord:
    field = "field"
    type = "type"
    primary = "primary"


@fieldmapper
class UserRecord:
    name = "name"
    superuser = "superuser"
    createdb = "createdb"


class ManagerInterface:

    @contextmanager
    def conn(self) -> Connection:
        """
        yield a connection context
        :return:
        """
        pass

    def backend(self) -> Union[Connection, PoolInterface]:
        """
        get connection backend without context manager
        :return:
        """
        pass

    def tables(self, schema=None) -> List:
        """
        List all available tables on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of tablenames
        """
        pass

    def views(self, schema=None) -> List:
        """
        List all available views on the indicated schema. If no schema is specified, assume public schema
        :param schema: optional schema name
        :return: list of views
        """
        pass

    def schemas(self) -> List[str]:
        """
        List all available schemas
        :return: list of schema names
        """
        pass

    def databases(self) -> List[str]:
        """
        List all available databases
        :return: list of database names
        """
        pass

    def table_indexes(self, table_name: str, schema=None) -> List[FieldRecord]:
        """
        List all indexes on a given table
        :param table_name:
        :param schema:
        :return:
        """
        pass

    def table_pk(self, table_name: str, schema=None) -> Optional[FieldRecord]:
        """
        Get primary key from table
        :param table_name:
        :param schema:
        :return:
        """
        pass

    def table_fields(self, table_name: str, schema=None) -> List[FieldRecord]:
        """
        Get fields of table
        :param table_name:
        :param schema:
        :return:
        """
        pass

    def view_fields(self, view_name: str, schema=None) -> List[FieldRecord]:
        """
        Get fields of view
        :param view_name:
        :param schema:
        :return:
        """
        pass

    def users(self) -> List[UserRecord]:
        """
        List all available users
        :return:
        """
        pass

    def user_groups(self, user_name: str) -> List[str]:
        """
        List all groups associated with a given user
        :param user_name: username to check
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

    def create_database(self, database_name: str, **kwargs):
        """
        Create a database
        :param database_name: database name
        :param kwargs: optional parameters
        :return:
        """
        pass

    def database_exists(self, database_name: str) -> bool:
        """
        Checks if a given database exists
        :param database_name: database name
        :return: bool
        """
        pass

    def drop_database(self, database_name: str):
        """
        Removes a database
        :param database_name: database name
        :return:
        """
        pass

    def create_schema(self, schema: str, **kwargs):
        """
        Create a new schema in the current database
        :param schema:
        :return:
        """
        pass

    def schema_exists(self, schema: str) -> bool:
        """
        Check if a given schema exists on the current database
        :param schema:
        :return: bool
        """
        pass

    def drop_schema(self, schema: str, cascade: bool = False):
        """
        Removes a schema
        :param schema:
        :param cascade:
        :return:
        """
        pass

    def kill_clients(self, database_name: str):
        """
        Kills all active connections to the database
        :param database_name:
        :return:
        """
        pass

    def drop_table(self, table_name: str, cascade: bool = False, schema: str = None):
        """
        Removes a table
        :param table_name:
        :param cascade:
        :param schema:
        :return:
        """
        pass

    def drop_view(self, view_name: str, cascade: bool = False, schema: str = None):
        """
        Removes a view
        :param view_name:
        :param cascade:
        :param schema:
        :return:
        """
        pass
