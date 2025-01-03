import abc
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List

from rick_db import Repository, fieldmapper
from .manager import ManagerInterface
from .mapper import ATTR_TABLE


@fieldmapper(pk="id_migration")
class MigrationRecord:
    id = "id_migration"
    name = "name"
    applied = "applied"


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


class BaseMigrationManager:
    MIGRATION_TABLE = "_migration"

    def __init__(self, mgr: ManagerInterface):
        self.manager = mgr

    def is_installed(self) -> bool:
        """
        Returns true if migration manager is installed
        :return:
        """
        return self.manager.table_exists(self.MIGRATION_TABLE)

    def install(self) -> MigrationResult:
        """
        Installs the migration manager in the current db
        :return:
        """
        if self.is_installed():
            return MigrationResult(
                success=False,
                error="migration table '{}' already exists".format(
                    self.MIGRATION_TABLE
                ),
            )

        try:
            with self.manager.conn() as conn:
                with conn.cursor() as c:
                    c.exec(self._migration_table_sql(self.MIGRATION_TABLE))
            return MigrationResult(success=True, error="")

        except Exception as e:
            return MigrationResult(success=False, error=str(e))

    def fetch_by_name(self, name: str) -> Optional[MigrationRecord]:
        """
        Search a migration by name
        :param name:
        :return: MigrationRecord or None
        """
        result = self.repository.fetch_by_field(MigrationRecord.name, name)
        if len(result) > 0:
            return result.pop(0)
        return None

    def list(self) -> List[MigrationRecord]:
        """
        Retrieve all registered migrations
        :return:
        """
        return self.repository.fetch_all_ordered(MigrationRecord.applied)

    def flatten(self, record: MigrationRecord) -> MigrationResult:
        """
        Remove all records from the migration table, and replace them with a new record
        :param record: new migration record
        :return:
        """
        try:
            # patch migration table
            setattr(record, ATTR_TABLE, self.MIGRATION_TABLE)
            record.applied = datetime.now().isoformat()

            self.repository.delete_where([(MigrationRecord.id, ">", 0)])
            self.repository.insert(record)

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

        if (
            len(
                self.repository.fetch_where(
                    [
                        (MigrationRecord.name, "=", migration.name),
                    ]
                )
            )
            > 0
        ):
            return MigrationResult(
                success=False,
                error="migration name {name} already exists".format(
                    name=migration.name
                ),
            )

        try:
            # patch migration table
            setattr(migration, ATTR_TABLE, self.MIGRATION_TABLE)
            migration.applied = datetime.now().isoformat()
            self.repository.insert(migration)
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

    @property
    def repository(self) -> Repository:
        # build a patched class based on MigrationRecord, since
        # existing one has no table name
        class R(MigrationRecord):
            pass

        # define table name
        setattr(R, ATTR_TABLE, self.MIGRATION_TABLE)

        return Repository(self.manager.backend(), R)

    @abc.abstractmethod
    def _migration_table_sql(self, table_name: str) -> str:
        pass

    def _exec(self, content):
        """
        Execute migration using a cursor
        :param content: string
        :return: none
        """
        with self.manager.conn() as conn:
            with conn.cursor() as c:
                c.exec(content)
