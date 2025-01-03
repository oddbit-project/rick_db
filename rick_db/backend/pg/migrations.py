from ...migrations import BaseMigrationManager
from ...sql import PgSqlDialect


class PgMigrationManager(BaseMigrationManager):

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
            name TEXT NOT NULL
        );
        """.format(
            name=PgSqlDialect().table(table_name)
        )
