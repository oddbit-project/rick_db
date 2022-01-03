import pytest

from rick_db.conn.sqlite import Sqlite3Connection
from rick_db.util import MigrationManager
from rick_db.util.sqlite import Sqlite3MigrationManager
from tests.util.migrations import BaseMigrationManager


class TestSqliteMigrationManager(BaseMigrationManager):

    @pytest.fixture()
    def mm(self) -> MigrationManager:
        return Sqlite3MigrationManager(self.conn)

    def setup_method(self, test_method):
        self.conn = Sqlite3Connection(":memory:")

    def teardown_method(self, test_method):
        self.conn.close()
        self.conn = None
