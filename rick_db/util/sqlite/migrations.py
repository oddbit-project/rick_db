from rick_db.conn import Connection
from rick_db.util import MigrationManager
from .metadata import Sqlite3Metadata
from ...sql import Sqlite3SqlDialect


class Sqlite3MigrationManager(MigrationManager):

    def __init__(self, db: Connection):
        super().__init__(db)
        self._meta = Sqlite3Metadata(db)

    def _migration_table_sql(self, table_name: str) -> str:
        """
        SQL for migration table creation
        :param table_name:
        :return:
        """
        return """
        CREATE TABLE {name}(
            id_migration INTEGER PRIMARY KEY AUTOINCREMENT,
            applied TIMESTAMP WITH TIME ZONE,
            name VARCHAR(255) NOT NULL UNIQUE
        );
        """.format(name=Sqlite3SqlDialect().table(table_name))

    def _exec(self, content):
        """
        Execute migration using a cursor
        :param content: string
        :return: none
        """
        with self._db.cursor() as c:
            # sqlite does not support multiple queries with exec()
            # so we use the sqlite3 cursor executescript() instead
            c.get_cursor().executescript(content)
