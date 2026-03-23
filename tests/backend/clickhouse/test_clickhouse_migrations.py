import pytest

from rick_db.backend.clickhouse import ClickHouseConnection, ClickHouseManager
from rick_db.backend.clickhouse.migrations import ClickHouseMigrationManager
from rick_db.migrations import MigrationRecord


class TestClickHouseMigrationManager:

    @pytest.fixture
    def mm(self, ch_backend):
        mgr = ClickHouseManager(ch_backend)
        mm = ClickHouseMigrationManager(mgr)
        yield mm
        mgr.drop_table(mm.MIGRATION_TABLE)

    def test_install_manager(self, mm):
        meta = mm.manager

        # ensure no manager
        assert mm.is_installed() is False

        # install manager
        result = mm.install()
        assert result.success is True
        assert result.error == ""
        assert mm.is_installed() is True
        tables = meta.tables()
        assert mm.MIGRATION_TABLE in tables

        # check table has no entries
        m_list = mm.list()
        assert len(m_list) == 0

    def test_install_already_installed(self, mm):
        mm.install()
        result = mm.install()
        assert result.success is False
        assert "already exists" in result.error

    def test_register(self, mm):
        mm.install()

        mig = MigrationRecord(name="migration1")
        result = mm.register(mig)
        assert result.success is True
        assert result.error == ""

        m_list = mm.list()
        assert len(m_list) == 1
        assert m_list[0].name == "migration1"

    def test_register_duplicate(self, mm):
        mm.install()

        mig = MigrationRecord(name="migration1")
        mm.register(mig)

        # duplicate should fail
        result = mm.register(MigrationRecord(name="migration1"))
        assert result.success is False
        assert "already exists" in result.error

    def test_register_empty_name(self, mm):
        mm.install()
        result = mm.register(MigrationRecord(name=""))
        assert result.success is False

    def test_fetch_by_name(self, mm):
        mm.install()
        mm.register(MigrationRecord(name="mig_one"))

        r = mm.fetch_by_name("mig_one")
        assert r is not None
        assert r.name == "mig_one"

        r = mm.fetch_by_name("nonexistent")
        assert r is None

    def test_flatten(self, mm):
        mm.install()

        # insert multiple records
        for name in ["mig1", "mig2", "mig3"]:
            result = mm.register(MigrationRecord(name=name))
            assert result.success is True

        m_list = mm.list()
        assert len(m_list) == 3

        # flatten
        flatten_record = MigrationRecord(name="flattened")
        result = mm.flatten(flatten_record)
        assert result.success is True

        m_list = mm.list()
        assert len(m_list) == 1
        assert m_list[0].name == "flattened"

    def test_execute(self, mm):
        mm.install()

        create_sql = """
        CREATE TABLE IF NOT EXISTS animal (
            id_animal UInt32,
            name String
        ) ENGINE = MergeTree()
        ORDER BY id_animal
        """

        mig = MigrationRecord(name="create_animal")
        result = mm.execute(mig, create_sql)
        assert result.success is True

        # table should exist
        assert mm.manager.table_exists("animal") is True

        # migration should be registered
        r = mm.fetch_by_name("create_animal")
        assert r is not None

        # cleanup
        mm.manager.drop_table("animal")

    def test_execute_duplicate(self, mm):
        mm.install()

        create_sql = """
        CREATE TABLE IF NOT EXISTS animal (
            id_animal UInt32,
            name String
        ) ENGINE = MergeTree()
        ORDER BY id_animal
        """
        mm.execute(MigrationRecord(name="create_animal"), create_sql)

        # executing same migration again should fail
        result = mm.execute(MigrationRecord(name="create_animal"), create_sql)
        assert result.success is False

        mm.manager.drop_table("animal")

    def test_execute_empty(self, mm):
        mm.install()
        result = mm.execute(MigrationRecord(name=""), "SELECT 1")
        assert result.success is False

        result = mm.execute(MigrationRecord(name="test"), "")
        assert result.success is False

    def test_execute_single_statement(self, mm):
        """Each migration file should contain a single SQL statement."""
        mm.install()

        create_sql = """
        CREATE TABLE IF NOT EXISTS animal (
            id_animal UInt32,
            name String
        ) ENGINE = MergeTree()
        ORDER BY id_animal
        """

        mig = MigrationRecord(name="single_stmt")
        result = mm.execute(mig, create_sql)
        assert result.success is True
        assert mm.manager.table_exists("animal") is True

        mm.manager.drop_table("animal")
