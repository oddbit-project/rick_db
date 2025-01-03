from rick_db.migrations import BaseMigrationManager
from rick_db.sql import Sqlite3SqlDialect


class Sqlite3MigrationManager(BaseMigrationManager):
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
            name TEXT NOT NULL
        );
        """.format(
            name=Sqlite3SqlDialect().table(table_name)
        )

    def _exec(self, content):
        """
        Execute migration using a cursor
        :param content: string
        :return: none
        """
        with self.manager.conn() as conn:
            with conn.cursor() as c:
                # sqlite does not support multiple queries with exec()
                # so we use the sqlite3 cursor executescript() instead
                c.get_cursor().executescript(content)
