from datetime import datetime
from typing import Optional

from rick_db.conn import Connection
from rick_db.util import MigrationManager, MigrationRecord, MigrationResult
from .metadata import PgMetadata
from ... import Repository


class PgMigrationManager(MigrationManager):
    TABLE_NAME = '_migration'

    def __init__(self, db: Connection):
        super().__init__(db)
        self._meta = PgMetadata(db)
        self._repo = None

    def has_manager(self) -> bool:
        """
        Returns true if migration manager is installed
        :return:
        """
        return self._meta.table_exists(self.TABLE_NAME)

    def install_manager(self) -> MigrationResult:
        """
        Installs the migration manager in the current db
        :return:
        """
        if self._meta.table_exists(self.TABLE_NAME):
            return MigrationResult(success=False, error="migration table '{}' already exists".format(self.TABLE_NAME))
        try:
            with self._db.cursor() as c:
                c.exec(self._migration_table_sql(self.TABLE_NAME))
                return MigrationResult(success=True, error="")
        except Exception as e:
            return MigrationResult(success=False, error=str(e))

    def fetch_by_name(self, name: str) -> Optional[MigrationRecord]:
        """
        Search a migration by name
        :param name: name to search
        :return: MigrationRecord or None
        """
        result = self.get_repository().fetch_by_field(MigrationRecord.name, name)
        if len(result) > 0:
            return result.pop(0)
        return None

    def fetch_by_hash(self, hash: str) -> Optional[MigrationRecord]:
        """
        Search a migration by hash
        :param hash:
        :return:
        """
        result = self.get_repository().fetch_by_field(MigrationRecord.hash, hash)
        if len(result) > 0:
            return result.pop(0)
        return None

    def list(self, ctx: str = None) -> list[MigrationRecord]:
        """
        Retrieve all registered migrations
        :param ctx: context
        :return:
        """
        qry = self.get_repository().select().order(MigrationRecord.applied)
        if ctx is not None:
            qry.where(MigrationRecord.ctx, '=', ctx)
        return self.get_repository().fetch(qry)

    def register(self, migration: MigrationRecord) -> MigrationResult:
        """
        Registers a migration
        This method can be used to provide code-only migration mechanisms
        :param migration:
        :return:
        """
        if len(migration.name) == 0 or len(migration.hash) == 0:
            return MigrationResult(success=False, error="empty migration data")

        try:
            migration.applied = datetime.now().isoformat()
            self.get_repository().insert(migration)
            return MigrationResult(success=True, error="")
        except Exception as e:
            return MigrationResult(success=False, error=str(e))

    def execute(self, migration: MigrationRecord, content: str) -> MigrationResult:
        """
        Execute a migration and register it
        :param migration:
        :param content:
        :return:
        """
        if len(migration.name) == 0 or len(migration.hash) == 0 or len(content) == 0:
            return MigrationResult(success=False, error="empty migration data")

        if self.fetch_by_name(migration.name) or self.fetch_by_hash(migration.hash):
            return MigrationResult(success=False, error="migration already executed")

        try:
            # execute migration
            with self._db.cursor() as c:
                c.exec(content)
                # update record
            return self.register(migration)
        except Exception as e:
            return MigrationResult(success=False, error=str(e))

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
            context VARCHAR(255) NOT NULL DEFAULT '',
            name VARCHAR(255) NOT NULL UNIQUE,
            hash VARCHAR(255) NOT NULL UNIQUE
        );
        """.format(name=self._db.quote_identifier(table_name))

    def get_repository(self) -> Repository:
        if self._repo is None:
            self._repo = Repository(self._db, MigrationRecord, table_name=self.TABLE_NAME,
                                    primary_key=MigrationRecord.id)
        return self._repo
