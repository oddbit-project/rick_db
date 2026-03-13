from datetime import datetime

from rick_db.migrations import BaseMigrationManager, MigrationRecord, MigrationResult
from rick_db.mapper import ATTR_TABLE
from rick_db.sql import ClickHouseSqlDialect


class ClickHouseMigrationManager(BaseMigrationManager):

    def _migration_table_sql(self, table_name: str) -> str:
        """
        SQL for migration table creation using ClickHouse MergeTree engine.
        Uses UUID for id_migration and DateTime for applied timestamp.
        """
        return """
        CREATE TABLE IF NOT EXISTS {name} (
            id_migration UUID DEFAULT generateUUIDv4(),
            applied DateTime DEFAULT now(),
            name String
        ) ENGINE = MergeTree()
        ORDER BY (name)
        """.format(name=ClickHouseSqlDialect().table(table_name))

    def flatten(self, record: MigrationRecord) -> MigrationResult:
        """
        Remove all records from the migration table, and replace with a new record.
        Uses TRUNCATE TABLE instead of DELETE WHERE (cleaner for ClickHouse,
        avoids UUID comparison issues).
        """
        try:
            setattr(record, ATTR_TABLE, self.MIGRATION_TABLE)
            record.applied = datetime.now().isoformat()

            sql = "TRUNCATE TABLE {}".format(
                ClickHouseSqlDialect().table(self.MIGRATION_TABLE)
            )
            with self.manager.conn() as conn:
                with conn.cursor() as c:
                    c.exec(sql)

            self.repository.insert(record)
            return MigrationResult(success=True, error="")
        except Exception as e:
            return MigrationResult(success=False, error=str(e))

    def _exec(self, content):
        """
        Execute migration using a cursor.
        Splits multi-statement SQL on ';' since clickhouse-connect's
        command() only accepts one statement at a time.
        """
        with self.manager.conn() as conn:
            with conn.cursor() as c:
                for statement in content.split(";"):
                    statement = statement.strip()
                    if statement:
                        c.exec(statement)
