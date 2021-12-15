from rick_db.conn import Connection
from rick_db.util import MigrationManager
from .metadata import PgMetadata
from ...sql import PgSqlDialect


class PgMigrationManager(MigrationManager):

    def __init__(self, db: Connection):
        super().__init__(db)
        self._meta = PgMetadata(db)

    def _migration_table_sql(self, table_name: str) -> str:
        """
        SQL for migration table creation
        :param table_name:
        :return:
        """
        return """
        CREATE TABLE {name}(
            id_migration SERIAL NOT NULL PRIMARY KEY,
            applied TIMESTAMP WITH TIME ZONE,
            name VARCHAR(255) NOT NULL UNIQUE
        );
        """.format(name=PgSqlDialect().table(table_name))
