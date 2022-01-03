from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from rick_db import Repository, fieldmapper
from rick_db.conn import Connection
from rick_db.util import Metadata

MIGRATION_TABLE = '_migration'


@fieldmapper(tablename=MIGRATION_TABLE, pk='id_migration')
class MigrationRecord:
    id = 'id_migration'
    name = 'name'
    applied = 'applied'


@dataclass
class MigrationResult:
    success: bool
    error: str


class Migration:

    def run(self, conn) -> bool:
        """
        Base class for code-based migrations
        :param conn:
        :return: bool
        """
        pass


class MigrationManager:

    def __init__(self, db: Connection):
        self._db = db
        self._meta = None  # type: Metadata
        self._repo = None

    def get_meta(self) -> Metadata:
        """
        Retrieve metadata manager
        :return:
        """
        return self._meta

    def has_manager(self) -> bool:
        """
        Returns true if migration manager is installed
        :return:
        """
        return self._meta.table_exists(MIGRATION_TABLE)

    def install_manager(self) -> MigrationResult:
        """
        Installs the migration manager in the current db
        :return:
        """
        if self._meta.table_exists(MIGRATION_TABLE):
            return MigrationResult(success=False, error="migration table '{}' already exists".format(MIGRATION_TABLE))
        try:
            with self._db.cursor() as c:
                c.exec(self._migration_table_sql(MIGRATION_TABLE))
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

    def list(self) -> List[MigrationRecord]:
        """
        Retrieve all registered migrations
        :return:
        """
        qry = self.get_repository().select().order(MigrationRecord.applied)
        return self.get_repository().fetch(qry)

    def flatten(self, record: MigrationRecord) -> MigrationResult:
        """
        Remove all records from the migration table, and replace them with a new record
        :param record: new migration record
        :return:
        """
        try:
            self.get_repository().delete_where([(MigrationRecord.id, '>', 0)])
            record.applied = datetime.now().isoformat()
            self.get_repository().insert(record)
            return MigrationResult(success=True, error="")
        except Exception as e:
            return MigrationResult(success=False, error=str(e))

    def register(self, migration: MigrationRecord) -> MigrationResult:
        """
        Registers a migration
        This method can be used to provide code-only migration mechanisms
        :param migration:
        :return:
        """
        if len(migration.name) == 0:
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
        if len(migration.name) == 0 or len(content) == 0:
            return MigrationResult(success=False, error="empty migration data")

        if self.fetch_by_name(migration.name):
            return MigrationResult(success=False, error="migration already executed")

        try:
            # execute migration
            self._exec(content)
            # update record
            return self.register(migration)
        except Exception as e:
            return MigrationResult(success=False, error=str(e))

    def get_repository(self) -> Repository:
        if self._repo is None:
            self._repo = Repository(self._db, MigrationRecord)
        return self._repo

    def _migration_table_sql(self, table_name: str) -> str:
        raise NotImplementedError("abstract method")

    def _exec(self, content):
        """
        Execute migration using a cursor
        :param content: string
        :return: none
        """
        with self._db.cursor() as c:
            c.exec(content)
