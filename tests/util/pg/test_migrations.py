import pytest

from rick_db.util.pg import PgMigrationManager
from tests.config import connectSimple
from tests.util.migrations import BaseMigrationManager


class TestPgMigrationManager(BaseMigrationManager):

    @pytest.fixture()
    def mm(self) -> PgMigrationManager:
        return PgMigrationManager(connectSimple())
