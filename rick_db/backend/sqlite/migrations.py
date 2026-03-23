from rick_db.migrations import BaseMigrationManager
from rick_db.sql import Sqlite3SqlDialect


def _split_statements(content):
    """Split SQL on semicolons, respecting single-quoted strings."""
    statements = []
    current = []
    in_string = False
    i = 0
    while i < len(content):
        ch = content[i]
        if in_string:
            current.append(ch)
            if ch == "'" and i + 1 < len(content) and content[i + 1] == "'":
                current.append("'")
                i += 2
                continue
            elif ch == "'":
                in_string = False
        elif ch == "'":
            in_string = True
            current.append(ch)
        elif ch == ";":
            stmt = "".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []
        else:
            current.append(ch)
        i += 1
    stmt = "".join(current).strip()
    if stmt:
        statements.append(stmt)
    return statements


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
        """.format(name=Sqlite3SqlDialect().table(table_name))

    def _exec(self, content):
        """
        Execute migration using a cursor.

        Statements are split by ';' (respecting quoted strings) and executed
        individually to avoid sqlite3's executescript() which implicitly
        commits any pending transaction.

        :param content: string
        :return: none
        """
        with self.manager.conn() as conn:
            with conn.cursor() as c:
                for statement in _split_statements(content):
                    c.exec(statement)
